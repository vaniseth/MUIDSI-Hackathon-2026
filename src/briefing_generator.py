"""
Briefing Generator - Feature 5: Pre-trip safety briefing
Generates a short, plain-English brief before a user starts walking.
Combines route risk, pattern data, time context, and alternatives.
"""
from datetime import datetime
from typing import Dict, Optional
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from src.archia_client import ArchiaClient

BRIEFING_SYSTEM_PROMPT = """You are MizzouSafe, generating a concise pre-trip safety briefing for a Mizzou student about to start walking.

Format (strictly):
**Tonight's Route Brief**
[1-2 sentence route summary with risk level and walk time]

**Key Risks**
[2-3 bullet points about specific risks on THIS route — crime types, timing patterns, hotspots]

**Your Options**
[2-3 bullet points: proceed safely / safer route / Safe Ride / Friend Walk — only include relevant ones]

**Before You Go**
[1-2 actionable tips specific to tonight's conditions]

Keep it under 150 words total. Be direct and helpful, not alarming.
"""


class BriefingGenerator:
    """
    Feature 5: Generates a pre-trip briefing from a completed route analysis.
    Call after RouteSafetyAgent.analyze_route() to get the briefing.
    """

    def __init__(self):
        self.client = ArchiaClient()

    def generate(self, route_response: Dict, hour: Optional[int] = None,
                 user_context: Dict = None) -> str:
        """
        Generate a pre-trip briefing from the route analysis response.

        Args:
            route_response: Output from RouteSafetyAgent.analyze_route()
            hour: Current hour (defaults to now)
            user_context: {'is_alone', 'day_of_week', etc.}

        Returns:
            Plain-text briefing string
        """
        user_context = user_context or {}
        hour = hour if hour is not None else datetime.now().hour

        route      = route_response.get('route', {})
        route_risk = route_response.get('route_risk', {})
        hotspot    = route_response.get('hotspot_step')
        recs       = route_response.get('recommendations', [])
        copilot    = route_response.get('safety_copilot_guidance', {})

        is_night  = hour >= 20 or hour < 6
        is_alone  = user_context.get('is_alone', False)
        day_name  = user_context.get('day_of_week', datetime.now().strftime('%A'))
        overall   = route_risk.get('overall_risk', 'Unknown')
        walk_min  = route.get('walk_minutes', '?')
        dist      = route.get('total_distance_miles', '?')
        step_count = route.get('step_count', '?')

        start_pattern = route_risk.get('start', {}).get('pattern', 'No data for start.')
        end_pattern   = route_risk.get('end', {}).get('pattern', 'No data for destination.')

        hotspot_text = ""
        if hotspot and hotspot.get('risk_detail', {}).get('risk_score', 0) >= 4:
            rd = hotspot['risk_detail']
            cb = hotspot.get('call_box')
            cb_note = (f"Call box {cb['distance_ft']}ft away at Step {hotspot['step']}."
                       if cb and cb['distance_ft'] <= 400 else "")
            hotspot_text = (
                f"Hotspot: Step {hotspot['step']} ({hotspot.get('road', 'unnamed road')}) — "
                f"{rd['risk_level']} risk. {rd['pattern_summary']} {cb_note}"
            )

        rec_text = "\n".join(
            f"- {r['title']}: {r['description']}"
            for r in recs[:3]
        )

        safe_ride_available = hour >= 19 or hour < 3
        friend_walk_available = 19 <= hour <= 27  # 7pm–3am

        prompt = f"""Generate a pre-trip safety briefing for this student:

TRIP DETAILS:
- Day/Time: {day_name}, {hour:02d}:00 ({'night' if is_night else 'day'})
- Traveling alone: {is_alone}
- Distance: {dist} miles | Walk time: ~{walk_min} min | Steps: {step_count}
- Overall risk: {overall}
- Max step risk score: {route.get('max_step_risk_score', 0)}/10

STARTING AREA PATTERN:
{start_pattern}

DESTINATION AREA PATTERN:
{end_pattern}

{f'HOTSPOT:{chr(10)}{hotspot_text}' if hotspot_text else 'No major hotspots on this route.'}

AVAILABLE SERVICES TONIGHT:
- Safe Ride: {'Available (573-882-1010)' if safe_ride_available else 'Not currently running'}
- Friend Walk: {'Available (573-884-9255)' if friend_walk_available else 'Not currently running'}
- MUPD: Always available (573-882-7201)

RECOMMENDATIONS FROM AGENTS:
{rec_text}

Now write the pre-trip briefing.
"""

        briefing = self.client.chat(
            system_prompt=BRIEFING_SYSTEM_PROMPT,
            user_message=prompt,
            temperature=0.4,
            max_tokens=400
        )

        return briefing

    def format_step_narration(self, route_response: Dict) -> str:
        """
        Feature 2 companion: Format all enriched steps as a readable narration.
        Useful for displaying turn-by-turn directions with safety context.
        """
        route = route_response.get('route', {})
        steps = route.get('steps', [])

        if not steps:
            return "No step-by-step directions available."

        lines = [
            f"🗺️ **Turn-by-Turn Directions** (~{route.get('walk_minutes', '?')} min walk)\n"
        ]

        for step in steps:
            rd         = step['risk_detail']
            risk_emoji = {'High': '🔴', 'Medium': '🟡', 'Low': '🟢'}.get(rd['risk_level'], '⚪')
            dist_ft    = round(step['distance_m'] * 3.281)
            dist_text  = f"{dist_ft}ft" if dist_ft < 1000 else f"{round(dist_ft/5280, 2)}mi"

            lines.append(f"{step['step']}. {risk_emoji} **{step['direction']}** ({dist_text})")

            if step.get('safety_note'):
                lines.append(f"   ℹ️  {step['safety_note']}")

        lines.append(f"\n📊 Route Risk: **{route.get('overall_risk', 'Unknown')}** "
                     f"(max score: {route.get('max_step_risk_score', 0)}/10)")

        return "\n".join(lines)