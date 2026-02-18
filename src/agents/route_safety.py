"""
Agent 2: Route Safety Agent
Analyzes routes using crime data and consults Safety Copilot for guidance
**DEPENDS ON Agent 1 (Safety Copilot)**
"""
"""
Agent 2: Route Safety Agent
Features 2 + 3: Step-level narration, pattern-aware reasoning
"""
from typing import Dict, List
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.risk_scorer import RiskScorer
from src.route_planner import RoutePlanner
from src.archia_client import ArchiaClient
from src.agents.safety_copilot import SafetyCopilot


ROUTE_SAFETY_SYSTEM_PROMPT = """You are TigerTown Route Safety Agent, a specialized AI for analyzing safe routes on the University of Missouri campus.

Your role:
1. Analyze route safety based on crime data
2. Explain risk factors clearly
3. Provide actionable recommendations
4. Integrate general safety guidance

Reasoning guidelines:
- If most incidents are minor theft on weekday afternoons and this is a Friday night → risk is higher than the score suggests
- If a segment has high incident count but they're all traffic/parking → deprioritize vs. assault/harassment
- If night_ratio ≥ 0.6 and the user is traveling after 8pm → explicitly flag this
- Mention call boxes when they are ≤ 300ft from a high-risk step
- Never just repeat numbers — interpret them into actionable advice

Response format:
1. **Route Assessment** - Overall safety evaluation with pattern reasoning (not just a score)
2. **Risk Factors** - Specific concerns: crime types, timing patterns, hotspot steps
3. **Recommendations** - Transport alternatives, timing, escorts, call box locations
4. **Safety Tips** - Contextual advice for tonight's specific conditions

Keep response under 300 words.
"""


class RouteSafetyAgent:
    def __init__(self):
        self.client      = ArchiaClient()
        self.risk_scorer = RiskScorer()
        self.route_planner = RoutePlanner()
        self.safety_copilot = SafetyCopilot()
        print("✅ Route Safety Agent initialized (with Safety Copilot dependency)")

    def analyze_route(self, start_lat: float, start_lon: float,
                      end_lat: float, end_lon: float,
                      hour: int, user_context: Dict = None) -> Dict:
        user_context = user_context or {}

        # ── Step 1: Get real walking steps + per-step risk ─────────────────
        print("🗺️  Fetching walking route from OSRM...")
        route = self.route_planner.get_route(start_lat, start_lon, end_lat, end_lon, hour)

        # ── Step 2: Get start/end rich detail (backwards compat) ───────────
        start_detail = self.risk_scorer.get_risk_detail(start_lat, start_lon, hour)
        end_detail   = self.risk_scorer.get_risk_detail(end_lat, end_lon, hour)

        overall_risk = route['overall_risk']

        # ── Step 3: Consult Safety Copilot ─────────────────────────────────
        safety_query = self._build_safety_query(overall_risk, hour, user_context)
        print(f"🔗 Consulting Safety Copilot: '{safety_query}'")
        copilot_response = self.safety_copilot.process_query(safety_query, user_context)

        # ── Step 4: Build pattern-aware prompt (Feature 3) ─────────────────
        route_prompt = self._build_pattern_prompt(
            route, start_detail, end_detail, hour, user_context, copilot_response
        )

        route_analysis = self.client.chat(
            system_prompt=ROUTE_SAFETY_SYSTEM_PROMPT,
            user_message=route_prompt,
            temperature=0.3
        )

        # ── Step 5: Recommendations ────────────────────────────────────────
        recommendations = self._generate_recommendations(
            overall_risk, hour, copilot_response, route
        )

        return {
            'agent': 'route_safety',
            'route': route,                          # Full step-by-step route
            'route_risk': {
                'overall_risk':   overall_risk,
                'avg_risk_score': route['avg_step_risk_score'],
                'max_risk_score': route['max_step_risk_score'],
                'start': {
                    'risk_level':  start_detail['risk_level'],
                    'risk_score':  start_detail['risk_score'],
                    'incidents':   start_detail['incident_count'],
                    'pattern':     start_detail['pattern_summary'],
                },
                'end': {
                    'risk_level':  end_detail['risk_level'],
                    'risk_score':  end_detail['risk_score'],
                    'incidents':   end_detail['incident_count'],
                    'pattern':     end_detail['pattern_summary'],
                },
            },
            'route_analysis':        route_analysis,
            'recommendations':       recommendations,
            'hotspot_step':          route.get('hotspot_step'),
            'safety_copilot_guidance': {
                'urgency':         copilot_response['urgency'],
                'primary_action':  copilot_response['primary_action'],
                'safety_checklist': copilot_response['safety_checklist'],
            }
        }

    def _build_pattern_prompt(self, route: Dict, start_detail: Dict,
                               end_detail: Dict, hour: int,
                               user_context: Dict, copilot_response: Dict) -> str:
        """Feature 3: Pattern-aware prompt with full incident context."""
        is_night  = hour >= 20 or hour < 6
        is_alone  = user_context.get('is_alone', False)
        day_name  = user_context.get('day_of_week', 'Unknown')

        # Summarize the 3 highest-risk steps
        steps = route.get('steps', [])
        risky_steps = sorted(steps, key=lambda s: s['risk_detail']['risk_score'], reverse=True)[:3]
        step_summaries = []
        for s in risky_steps:
            rd = s['risk_detail']
            if rd['risk_score'] > 0:
                step_summaries.append(
                    f"  Step {s['step']} ({s['road'] or 'unnamed road'}): "
                    f"{rd['risk_level']} risk (score {rd['risk_score']}) — "
                    f"{rd['pattern_summary']}"
                )

        step_text = "\n".join(step_summaries) if step_summaries else "  All steps show low risk."

        hotspot = route.get('hotspot_step')
        hotspot_text = ""
        if hotspot and hotspot['risk_detail']['risk_score'] > 0:
            rd = hotspot['risk_detail']
            cb = hotspot.get('call_box')
            cb_text = (f"Emergency call box {cb['distance_ft']}ft away."
                       if cb and cb['distance_ft'] <= 500 else "No nearby call box.")
            hotspot_text = (
                f"\nHOTSPOT STEP — Step {hotspot['step']} ({hotspot['road']}):\n"
                f"  Risk: {rd['risk_level']} | Score: {rd['risk_score']}\n"
                f"  Categories: {rd['category_breakdown']}\n"
                f"  Night ratio: {rd['night_ratio']} | Weekend ratio: {rd['weekend_ratio']}\n"
                f"  Peak hour: {rd['peak_hour']} | Current hour: {hour}\n"
                f"  {cb_text}"
            )

        prompt = f"""Analyze this walking route for a Mizzou student:

CONTEXT:
- Time: {hour:02d}:00 ({'night' if is_night else 'day'}) | Day: {day_name}
- Traveling alone: {is_alone}
- Route: {route['total_distance_miles']} miles, ~{route['walk_minutes']} min walk
- Steps: {route['step_count']} | Source: {route['source']}
- Overall risk: {route['overall_risk']} (max step score: {route['max_step_risk_score']}/10)

STARTING POINT:
{start_detail['pattern_summary']}

DESTINATION:
{end_detail['pattern_summary']}

TOP RISK STEPS:
{step_text}
{hotspot_text}

SAFETY COPILOT GUIDANCE (from MU safety documents):
{copilot_response.get('llm_guidance', 'N/A')}

TASK:
Give a route-specific safety briefing. Reason about patterns (what types of crimes, when they happen, whether tonight's conditions match peak risk times). Don't just repeat numbers — interpret them. Flag the hotspot step specifically. End with one clear recommendation.
"""
        return prompt

    def _build_safety_query(self, risk_level: str, hour: int, user_context: Dict) -> str:
        time_desc = "night" if (hour >= 20 or hour <= 5) else "daytime"
        alone = user_context.get('is_alone', False)
        if risk_level == "High":
            return (f"I need to walk alone at {time_desc} through a high-risk area on campus. "
                    f"What should I do?" if alone else
                    f"I'm traveling through a high-risk campus area at {time_desc}. Precautions?")
        elif risk_level == "Medium":
            return f"I'm walking through a moderate-risk campus area at {time_desc}. Safety tips?"
        return f"General tips for walking on campus at {time_desc}."

    def _generate_recommendations(self, risk_level: str, hour: int,
                                   copilot_response: Dict, route: Dict) -> List[Dict]:
        recs = []

        if risk_level == "High":
            recs.append({
                'type': 'transport', 'priority': 1,
                'title': '🚗 Use Safe Ride',
                'description': 'Free campus shuttle — Call 573-882-1010'
            })
            recs.append({
                'type': 'escort', 'priority': 1,
                'title': '👥 Request Friend Walk',
                'description': 'Walking escort service — Call 573-884-9255 (7PM–3AM)'
            })

        if risk_level in ['High', 'Medium'] and (hour >= 20 or hour <= 6):
            recs.append({
                'type': 'timing', 'priority': 2,
                'title': '⏰ Consider Alternate Time',
                'description': 'Travel during daylight if possible'
            })

        hotspot = route.get('hotspot_step')
        if hotspot and hotspot['risk_detail']['risk_score'] >= 4:
            recs.append({
                'type': 'avoid', 'priority': 1,
                'title': f"⚠️ High-Risk Segment at Step {hotspot['step']}",
                'description': hotspot['risk_detail']['pattern_summary']
            })

        recs.append({
            'type': 'emergency_contact', 'priority': 1,
            'title': copilot_response['primary_action']['name'],
            'description': (
                f"{copilot_response['primary_action']['contact']}: "
                f"{copilot_response['primary_action']['description']}"
            )
        })

        return sorted(recs, key=lambda x: x['priority'])