"""
Agent 2: Route Safety Agent
Analyzes routes using crime data and consults Safety Copilot for guidance
**DEPENDS ON Agent 1 (Safety Copilot)**
"""
from typing import Dict, List, Tuple
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from src.risk_scorer import RiskScorer
from src.archia_client import ArchiaClient
from src.agents.safety_copilot import SafetyCopilot


ROUTE_SAFETY_SYSTEM_PROMPT = """You are MizzouSafe Route Safety Agent, a specialized AI for analyzing safe routes on the University of Missouri campus.

Your role:
1. Analyze route safety based on crime data
2. Explain risk factors clearly
3. Provide actionable recommendations
4. Integrate general safety guidance

Guidelines:
- Be data-driven but explain in simple terms
- Highlight specific risk factors (time, location, crime types)
- Always provide alternative options
- Reference the Safety Copilot's general guidance when relevant

Response format:
1. **Route Assessment** - Overall safety evaluation
2. **Risk Factors** - Specific concerns with this route
3. **Recommendations** - What to do (transport alternatives, timing, escorts)
4. **Safety Tips** - Contextual advice for this journey

Keep responses under 250 words.
"""


class RouteSafetyAgent:
    """
    Agent 2: Route Safety Agent
    Analyzes routes and DEPENDS ON Safety Copilot for general guidance
    """
    
    def __init__(self):
        self.client = ArchiaClient()
        self.risk_scorer = RiskScorer()
        # DEPENDENCY: Initialize Safety Copilot
        self.safety_copilot = SafetyCopilot()
        print("✅ Route Safety Agent initialized (with Safety Copilot dependency)")
    
    def analyze_route(self, start_lat: float, start_lon: float, 
                     end_lat: float, end_lon: float, 
                     hour: int, user_context: Dict = None) -> Dict:
        """
        Analyze route safety
        
        Args:
            start_lat, start_lon: Starting location
            end_lat, end_lon: Destination
            hour: Time of travel (0-23)
            user_context: User context (is_alone, etc.)
            
        Returns:
            Complete route analysis with safety guidance
        """
        # 1. Get risk scores for start and end points
        start_risk_level, start_risk_score, start_incidents = self.risk_scorer.get_risk_score(
            start_lat, start_lon, hour
        )
        
        end_risk_level, end_risk_score, end_incidents = self.risk_scorer.get_risk_score(
            end_lat, end_lon, hour
        )
        
        # Calculate overall route risk
        avg_risk_score = (start_risk_score + end_risk_score) / 2
        if avg_risk_score >= 8:
            overall_risk = "High"
        elif avg_risk_score >= 4:
            overall_risk = "Medium"
        else:
            overall_risk = "Low"
        
        # 2. **AGENT DEPENDENCY**: Consult Safety Copilot for general guidance
        # Build a query for the Safety Copilot based on the route risk
        safety_query = self._build_safety_query(overall_risk, hour, user_context)
        
        print(f"🔗 Consulting Safety Copilot about: '{safety_query}'")
        copilot_response = self.safety_copilot.process_query(safety_query, user_context)
        
        # 3. Generate route-specific analysis using LLM
        route_prompt = self._create_route_prompt(
            start_risk_level, start_risk_score, start_incidents,
            end_risk_level, end_risk_score, end_incidents,
            hour, overall_risk, copilot_response
        )
        
        route_analysis = self.client.chat(
            system_prompt=ROUTE_SAFETY_SYSTEM_PROMPT,
            user_message=route_prompt,
            temperature=0.3
        )
        
        # 4. Generate recommendations
        recommendations = self._generate_recommendations(
            overall_risk, hour, copilot_response
        )
        
        # 5. Compile complete response
        return {
            'agent': 'route_safety',
            'route_risk': {
                'overall_risk': overall_risk,
                'avg_risk_score': round(avg_risk_score, 2),
                'start': {
                    'risk_level': start_risk_level,
                    'risk_score': start_risk_score,
                    'incidents': start_incidents
                },
                'end': {
                    'risk_level': end_risk_level,
                    'risk_score': end_risk_score,
                    'incidents': end_incidents
                }
            },
            'route_analysis': route_analysis,
            'recommendations': recommendations,
            # Include Safety Copilot's guidance
            'safety_copilot_guidance': {
                'urgency': copilot_response['urgency'],
                'primary_action': copilot_response['primary_action'],
                'safety_checklist': copilot_response['safety_checklist']
            }
        }
    
    def _build_safety_query(self, risk_level: str, hour: int, user_context: Dict = None) -> str:
        """Build a query for Safety Copilot based on route risk"""
        time_desc = "night" if (hour >= 20 or hour <= 5) else "daytime"
        
        if risk_level == "High":
            if user_context and user_context.get('is_alone'):
                return f"I need to walk alone at {time_desc} in a high-risk area. What should I do?"
            else:
                return f"I need to travel through a high-risk area at {time_desc}. What precautions should I take?"
        elif risk_level == "Medium":
            return f"I'm traveling through an area with moderate crime risk at {time_desc}. What safety measures should I take?"
        else:
            return f"I'm planning to travel on campus at {time_desc}. Any general safety tips?"
    
    def _create_route_prompt(self, start_risk_level: str, start_risk_score: float, start_incidents: int,
                             end_risk_level: str, end_risk_score: float, end_incidents: int,
                             hour: int, overall_risk: str, copilot_response: Dict) -> str:
        """Create prompt for route analysis"""
        prompt = f"""Analyze this campus route:

**Route Overview:**
- Time: {hour:02d}:00
- Overall Risk: {overall_risk}

**Starting Point:**
- Risk Level: {start_risk_level}
- Risk Score: {start_risk_score}/10
- Historical Incidents: {start_incidents}

**Destination:**
- Risk Level: {end_risk_level}
- Risk Score: {end_risk_score}/10
- Historical Incidents: {end_incidents}

**General Safety Guidance from Safety Copilot:**
{copilot_response['llm_guidance']}

**Your task:**
Provide a route-specific safety analysis that:
1. Explains the specific risks of this route
2. Recommends the safest way to complete this journey
3. Integrates the general safety advice above with route-specific details
4. Suggests alternatives if risk is high

Be specific about THIS route, not general campus safety.
"""
        return prompt
    
    def _generate_recommendations(self, risk_level: str, hour: int, copilot_response: Dict) -> List[Dict]:
        """Generate route recommendations"""
        recommendations = []
        
        if risk_level == "High":
            recommendations.append({
                'type': 'transport',
                'title': '🚗 Use Safe Ride',
                'description': 'Call Safe Ride: 573-882-1010 (Free campus shuttle)',
                'priority': 1
            })
            recommendations.append({
                'type': 'escort',
                'title': '👥 Request Friend Walk',
                'description': 'Walking escort: 573-884-9255 (7PM-3AM)',
                'priority': 1
            })
        
        if risk_level in ["High", "Medium"] and (hour >= 20 or hour <= 6):
            recommendations.append({
                'type': 'timing',
                'title': '⏰ Consider Alternate Time',
                'description': 'If possible, travel during daylight hours',
                'priority': 2
            })
        
        # Add primary action from Safety Copilot
        recommendations.append({
            'type': 'emergency_contact',
            'title': copilot_response['primary_action']['name'],
            'description': f"{copilot_response['primary_action']['contact']}: {copilot_response['primary_action']['description']}",
            'priority': 1 if copilot_response['urgency']['level'] == 'emergency' else 2
        })
        
        return sorted(recommendations, key=lambda x: x['priority'])
