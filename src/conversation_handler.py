"""
Conversation Handler
Manages multi-turn safety conversations:
  Turn 1: User reports concern → Agent 1 assesses + asks for location
  Turn 2: User gives location → Agent 2 finds safest route to safe destination
"""
import math
from datetime import datetime
from typing import Dict, Optional
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from src.config import (
    LOCATION_TRIGGER_KEYWORDS, SAFE_DESTINATIONS,
    EMERGENCY_CONTACTS
)

# Known campus locations - name → (lat, lon)
KNOWN_LOCATIONS = {
    "memorial union":           (38.9404, -92.3277),
    "ellis library":            (38.9445, -92.3263),
    "student center":           (38.9423, -92.3268),
    "rec center":               (38.9389, -92.3301),
    "mizzou arena":             (38.9356, -92.3332),
    "faurot field":             (38.9355, -92.3306),
    "jesse hall":               (38.9441, -92.3269),
    "engineering building":     (38.9438, -92.3256),
    "trulaske":                 (38.9398, -92.3271),
    "parking lot a1":           (38.9450, -92.3240),
    "parking lot c2":           (38.9380, -92.3350),
    "greek town":               (38.9395, -92.3320),
    "hitt street":              (38.9415, -92.3280),
    "tiger plaza":              (38.9430, -92.3275),
    "conley ave":               (38.9380, -92.3250),
    "university hospital":      (38.9403, -92.3245),
    "hospital":                 (38.9403, -92.3245),
    "mupd":                     (38.9456, -92.3264),
    "police":                   (38.9456, -92.3264),
}


def haversine(lat1, lon1, lat2, lon2) -> float:
    """Distance between two coordinates in miles"""
    R = 3959
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def parse_location(user_input: str) -> Optional[tuple]:
    """
    Try to extract a location from user input.
    Returns (lat, lon) or None if not found.
    """
    text = user_input.lower().strip()

    # Check known locations
    for location_name, coords in KNOWN_LOCATIONS.items():
        if location_name in text:
            return coords

    # Try to parse raw coordinates (e.g. "38.9404, -92.3277")
    import re
    coord_match = re.search(r'(-?\d+\.\d+)[,\s]+(-?\d+\.\d+)', text)
    if coord_match:
        try:
            lat = float(coord_match.group(1))
            lon = float(coord_match.group(2))
            if 38.9 < lat < 39.0 and -92.4 < lon < -92.2:  # MU campus range
                return (lat, lon)
        except ValueError:
            pass

    return None


def needs_location(query: str, urgency_level: str) -> bool:
    """Decide if we should ask for the user's location"""
    query_lower = query.lower()
    has_trigger = any(kw in query_lower for kw in LOCATION_TRIGGER_KEYWORDS)
    is_urgent = urgency_level in ['emergency', 'high', 'medium']
    return has_trigger and is_urgent


def nearest_safe_destination(user_lat: float, user_lon: float, hour: int) -> Dict:
    """Find the closest safe destination to the user"""
    best = None
    best_dist = float('inf')

    for key, dest in SAFE_DESTINATIONS.items():
        dist = haversine(user_lat, user_lon, dest['lat'], dest['lon'])
        # Always include 24/7 locations; others only if likely open
        if dist < best_dist:
            best_dist = dist
            best = {**dest, 'key': key, 'distance_miles': round(dist, 3)}

    # Estimated walk time (avg 3 mph)
    if best:
        walk_minutes = round((best['distance_miles'] / 3) * 60)
        best['walk_minutes'] = max(walk_minutes, 1)

    return best


class ConversationHandler:
    """
    Handles multi-turn conversations with location awareness.

    State machine:
      'initial'            → waiting for first message
      'awaiting_location'  → safety concern detected, asked for location
      'route_provided'     → gave safe route, conversation can continue
    """

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.state = 'initial'
        self.pending_query = None          # Saved original safety query
        self.pending_safety_response = None  # Agent 1's response saved
        self.conversation_history = []

    def reset(self):
        self.state = 'initial'
        self.pending_query = None
        self.pending_safety_response = None

    def handle(self, user_message: str, user_context: Dict = None) -> Dict:
        """
        Main entry point. Routes message based on conversation state.
        Returns a response dict with 'message', 'type', and optional 'route'.
        """
        user_context = user_context or {}
        self.conversation_history.append({'role': 'user', 'content': user_message})

        if self.state == 'awaiting_location':
            response = self._handle_location_response(user_message, user_context)
        else:
            response = self._handle_initial_message(user_message, user_context)

        self.conversation_history.append({'role': 'assistant', 'content': response.get('message', '')})
        return response

    def _handle_initial_message(self, message: str, user_context: Dict) -> Dict:
        """Turn 1: assess the query, ask for location if needed"""

        # Run Agent 1 first
        safety_response = self.orchestrator.handle_query(
            query_type='safety',
            query=message,
            user_context=user_context
        )

        urgency = safety_response.get('urgency', {})
        urgency_level = urgency.get('level', 'low')
        primary_action = safety_response.get('primary_action', {})
        checklist = safety_response.get('safety_checklist', [])
        llm_guidance = safety_response.get('llm_guidance', '')
        relevant_links = safety_response.get('relevant_links', [])

        # Build the base response text
        response_text = self._format_safety_response(
            llm_guidance, primary_action, checklist, relevant_links, urgency_level
        )

        # If location is needed, save state and ask
        if needs_location(message, urgency_level):
            self.state = 'awaiting_location'
            self.pending_query = message
            self.pending_safety_response = safety_response

            response_text += (
                "\n\n📍 **To help you get to safety, can you tell me where you are right now?**\n"
                "You can say a building name (e.g. 'Ellis Library', 'Memorial Union', 'Mizzou Arena') "
                "or describe your location."
            )

            return {
                'type': 'safety_with_location_request',
                'message': response_text,
                'urgency': urgency_level,
                'primary_action': primary_action,
                'safety_response': safety_response,
                'awaiting_location': True
            }

        # No location needed — just return safety response
        self.state = 'initial'
        return {
            'type': 'safety',
            'message': response_text,
            'urgency': urgency_level,
            'primary_action': primary_action,
            'safety_response': safety_response,
            'awaiting_location': False
        }

    def _handle_location_response(self, message: str, user_context: Dict) -> Dict:
        """Turn 2: user gave their location, now provide a safe route"""

        coords = parse_location(message)

        if coords is None:
            # Couldn't parse location - ask again more specifically
            return {
                'type': 'location_unclear',
                'message': (
                    "I wasn't able to identify that location. "
                    "Please name a campus building — for example:\n"
                    "• Ellis Library\n• Memorial Union\n• Student Center\n"
                    "• Mizzou Arena\n• Rec Center\n• Greek Town\n\n"
                    "Or call MUPD now at **573-882-7201** and they can come to you."
                ),
                'awaiting_location': True
            }

        user_lat, user_lon = coords
        hour = datetime.now().hour

        # Find nearest safe destination
        nearest = nearest_safe_destination(user_lat, user_lon, hour)

        # Run Agent 2 with route to nearest safe destination
        route_response = self.orchestrator.handle_query(
            query_type='route',
            start_lat=user_lat,
            start_lon=user_lon,
            end_lat=nearest['lat'],
            end_lon=nearest['lon'],
            hour=hour,
            user_context={**user_context, 'is_alone': True, 'emergency': True}
        )

        # Build combined response
        route_message = self._format_route_response(nearest, route_response, hour)

        self.state = 'route_provided'

        return {
            'type': 'route',
            'message': route_message,
            'user_location': {'lat': user_lat, 'lon': user_lon},
            'destination': nearest,
            'route_response': route_response,
            'original_safety_response': self.pending_safety_response,
            'awaiting_location': False
        }

    def _format_safety_response(self, llm_guidance, primary_action,
                                  checklist, relevant_links, urgency_level) -> str:
        """Format Agent 1 response into clean text"""
        lines = []

        if urgency_level == 'emergency':
            lines.append("🚨 **EMERGENCY — Call 911 immediately.**\n")
        elif urgency_level == 'high':
            lines.append("⚠️ **This sounds serious. Here's what to do:**\n")

        if llm_guidance and not llm_guidance.startswith('Error'):
            lines.append(llm_guidance)
        else:
            # Fallback if LLM fails
            if primary_action:
                lines.append(f"**Immediate Action:** {primary_action.get('name', '')} — {primary_action.get('contact', '')}")
            if checklist:
                lines.append("\n**Safety Checklist:**")
                for item in checklist:
                    lines.append(f"• {item}")

        if relevant_links:
            lines.append("\n**Reporting Links:**")
            for link in relevant_links:
                lines.append(f"• [{link['name']}]({link['url']})")

        return "\n".join(lines)

    def _format_route_response(self, destination: Dict,
                                route_response: Dict, hour: int) -> str:
        """Format Agent 2 route response into clean text"""
        lines = []

        dest_name = destination.get('name', 'Safe Location')
        walk_min = destination.get('walk_minutes', 5)
        dist = destination.get('distance_miles', 0)
        phone = destination.get('phone', '573-882-7201')
        available = destination.get('available', '24/7')

        lines.append(f"🗺️ **Nearest safe destination: {dest_name}**")
        lines.append(f"📏 Distance: {dist:.2f} miles (~{walk_min} min walk)")
        lines.append(f"📞 Phone: {phone} | Open: {available}\n")

        # Route risk
        route_risk = route_response.get('route_risk', {})
        risk_level = route_risk.get('overall_risk', 'Unknown')
        risk_emoji = {'Low': '🟢', 'Medium': '🟡', 'High': '🔴'}.get(risk_level, '⚪')
        lines.append(f"{risk_emoji} **Route Risk Level: {risk_level}**\n")

        # Route analysis from AI
        route_analysis = route_response.get('route_analysis', '')
        if route_analysis and not route_analysis.startswith('Error'):
            lines.append(route_analysis)

        # Recommendations
        recommendations = route_response.get('recommendations', [])
        if recommendations:
            lines.append("\n**Recommendations:**")
            for rec in recommendations[:3]:
                lines.append(f"• **{rec.get('title', '')}** — {rec.get('description', '')}")

        # Always end with key contacts
        lines.append(f"\n📞 **Call MUPD anytime: 573-882-7201**")
        if hour >= 19 or hour < 3:
            lines.append("🚗 **Safe Ride available now: 573-882-1010**")
            lines.append("👥 **Friend Walk available now: 573-884-9255**")

        return "\n".join(lines)