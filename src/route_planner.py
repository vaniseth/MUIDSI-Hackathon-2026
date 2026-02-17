"""
Route Planner - Feature 2: Step-level routing via OSRM
Fetches real walking directions, scores each step individually,
and attaches call box proximity + contextual safety notes.
"""
import math
import requests
from typing import Dict, List, Optional, Tuple
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from src.risk_scorer import RiskScorer

# Public OSRM demo server (walking profile)
OSRM_BASE = "http://router.project-osrm.org/route/v1/foot"

# MU Emergency Blue-Light Call Boxes (approximate locations)
CALL_BOXES = [
    {"name": "Call Box - Memorial Union",     "lat": 38.9404, "lon": -92.3277},
    {"name": "Call Box - Ellis Library",      "lat": 38.9445, "lon": -92.3263},
    {"name": "Call Box - Rec Center",         "lat": 38.9389, "lon": -92.3301},
    {"name": "Call Box - Parking Garage A",   "lat": 38.9450, "lon": -92.3240},
    {"name": "Call Box - Student Center",     "lat": 38.9423, "lon": -92.3268},
    {"name": "Call Box - Engineering",        "lat": 38.9438, "lon": -92.3256},
    {"name": "Call Box - Conley Ave",         "lat": 38.9380, "lon": -92.3250},
    {"name": "Call Box - Hitt St",            "lat": 38.9415, "lon": -92.3280},
    {"name": "Call Box - Virginia Ave",       "lat": 38.9456, "lon": -92.3264},
    {"name": "Call Box - Greek Town",         "lat": 38.9395, "lon": -92.3320},
]


def haversine(lat1, lon1, lat2, lon2) -> float:
    R = 3959
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2)
    return R * 2 * math.asin(math.sqrt(a))


def nearest_call_box(lat: float, lon: float) -> Optional[Dict]:
    best = None
    best_dist = float('inf')
    for box in CALL_BOXES:
        d = haversine(lat, lon, box['lat'], box['lon'])
        if d < best_dist:
            best_dist = d
            best = {**box, 'distance_miles': round(d, 3),
                    'distance_ft': round(d * 5280)}
    return best


class RoutePlanner:
    """
    Feature 2: Fetches real walking steps from OSRM,
    scores each step with RiskScorer, attaches call box proximity.
    """

    def __init__(self):
        self.risk_scorer = RiskScorer()

    def get_route(self, start_lat: float, start_lon: float,
                  end_lat: float, end_lon: float,
                  hour: int) -> Dict:
        """
        Fetch walking route and score each step.
        Returns enriched steps with risk detail per step.
        """
        osrm_url = (
            f"{OSRM_BASE}/{start_lon},{start_lat};{end_lon},{end_lat}"
            f"?steps=true&geometries=geojson&overview=full&annotations=true"
        )

        try:
            resp = requests.get(osrm_url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"⚠️  OSRM unavailable ({e}), using fallback straight-line route")
            return self._fallback_route(start_lat, start_lon, end_lat, end_lon, hour)

        if data.get('code') != 'Ok' or not data.get('routes'):
            return self._fallback_route(start_lat, start_lon, end_lat, end_lon, hour)

        route = data['routes'][0]
        legs  = route.get('legs', [])

        enriched_steps = []
        step_number = 1

        for leg in legs:
            for step in leg.get('steps', []):
                maneuver  = step.get('maneuver', {})
                location  = maneuver.get('location', [None, None])  # [lon, lat]
                step_lon, step_lat = location[0], location[1]

                if step_lat is None or step_lon is None:
                    continue

                instruction = step.get('name', '') or step.get('ref', '') or 'Unnamed road'
                maneuver_type = maneuver.get('type', '')
                modifier      = maneuver.get('modifier', '')
                distance_m    = step.get('distance', 0)
                duration_s    = step.get('duration', 0)

                # Score this specific step location
                risk_detail = self.risk_scorer.get_risk_detail(step_lat, step_lon, hour)

                # Nearest call box at this step
                call_box = nearest_call_box(step_lat, step_lon)

                # Build human direction string
                direction = self._build_direction(maneuver_type, modifier, instruction)

                # Safety note for this step
                safety_note = self._step_safety_note(risk_detail, call_box, distance_m)

                enriched_steps.append({
                    'step':        step_number,
                    'direction':   direction,
                    'road':        instruction,
                    'lat':         step_lat,
                    'lon':         step_lon,
                    'distance_m':  round(distance_m),
                    'duration_s':  round(duration_s),
                    'risk_detail': risk_detail,
                    'call_box':    call_box,
                    'safety_note': safety_note,
                })
                step_number += 1

        total_distance_m = route.get('distance', 0)
        total_duration_s = route.get('duration', 0)

        # Overall route risk = weighted average of step scores
        if enriched_steps:
            scores = [s['risk_detail']['risk_score'] for s in enriched_steps]
            max_score = max(scores)
            avg_score = round(sum(scores) / len(scores), 2)
        else:
            max_score, avg_score = 0, 0

        overall_risk = ('High' if max_score >= 8 else
                        'Medium' if max_score >= 4 else 'Low')

        # Flag the highest-risk step
        if enriched_steps:
            hotspot_step = max(enriched_steps,
                               key=lambda s: s['risk_detail']['risk_score'])
        else:
            hotspot_step = None

        return {
            'source': 'osrm',
            'total_distance_m': round(total_distance_m),
            'total_distance_miles': round(total_distance_m / 1609.34, 2),
            'total_duration_s': round(total_duration_s),
            'walk_minutes': round(total_duration_s / 60),
            'steps': enriched_steps,
            'step_count': len(enriched_steps),
            'overall_risk': overall_risk,
            'max_step_risk_score': round(max_score, 2),
            'avg_step_risk_score': avg_score,
            'hotspot_step': hotspot_step,
        }

    def _build_direction(self, maneuver_type: str, modifier: str, road: str) -> str:
        """Convert OSRM maneuver to plain English."""
        if maneuver_type == 'depart':
            return f"Start on {road}"
        if maneuver_type == 'arrive':
            return "Arrive at destination"
        if maneuver_type in ('turn', 'new name'):
            mod_map = {
                'left': 'Turn left', 'right': 'Turn right',
                'slight left': 'Bear left', 'slight right': 'Bear right',
                'sharp left': 'Sharp left', 'sharp right': 'Sharp right',
                'straight': 'Continue straight', 'uturn': 'U-turn',
            }
            action = mod_map.get(modifier, 'Continue')
            return f"{action} onto {road}" if road else action
        if maneuver_type == 'roundabout':
            return f"Enter roundabout, take exit onto {road}"
        if maneuver_type == 'continue':
            return f"Continue on {road}"
        return f"Head toward {road}" if road else maneuver_type.replace('-', ' ').title()

    def _step_safety_note(self, risk_detail: Dict, call_box: Optional[Dict],
                           distance_m: float) -> Optional[str]:
        """Generate a contextual safety note for a step."""
        notes = []

        risk_level = risk_detail.get('risk_level', 'Low')
        pattern    = risk_detail.get('pattern_summary', '')
        dominant   = risk_detail.get('dominant_crime')
        night_ratio = risk_detail.get('night_ratio', 0)

        if risk_level == 'High':
            notes.append(f"⚠️ High-risk segment — {pattern}")
        elif risk_level == 'Medium' and pattern:
            notes.append(f"🟡 Moderate risk — {pattern}")

        if dominant == 'theft' and risk_detail.get('incident_count', 0) > 2:
            notes.append("Theft is the dominant crime type here; keep valuables secured.")
        elif dominant == 'assault':
            notes.append("Physical incidents reported in this area — stay aware.")

        if night_ratio >= 0.7 and risk_level != 'Low':
            notes.append("This area is notably more dangerous at night.")

        if call_box and call_box['distance_ft'] <= 300:
            notes.append(
                f"🔵 Emergency call box {call_box['distance_ft']}ft ahead "
                f"({call_box['name']})."
            )

        return " ".join(notes) if notes else None

    def _fallback_route(self, start_lat, start_lon, end_lat, end_lon, hour) -> Dict:
        """Return a minimal 2-step route when OSRM is unavailable."""
        dist = haversine(start_lat, start_lon, end_lat, end_lon)
        walk_min = max(1, round((dist / 3) * 60))

        start_risk = self.risk_scorer.get_risk_detail(start_lat, start_lon, hour)
        end_risk   = self.risk_scorer.get_risk_detail(end_lat, end_lon, hour)

        steps = [
            {
                'step': 1, 'direction': 'Head toward your destination',
                'road': 'Campus path', 'lat': start_lat, 'lon': start_lon,
                'distance_m': round(dist * 1609),
                'duration_s': walk_min * 60,
                'risk_detail': start_risk,
                'call_box': nearest_call_box(start_lat, start_lon),
                'safety_note': start_risk.get('pattern_summary'),
            },
            {
                'step': 2, 'direction': 'Arrive at destination',
                'road': '', 'lat': end_lat, 'lon': end_lon,
                'distance_m': 0, 'duration_s': 0,
                'risk_detail': end_risk,
                'call_box': nearest_call_box(end_lat, end_lon),
                'safety_note': None,
            }
        ]

        max_score = max(start_risk['risk_score'], end_risk['risk_score'])
        overall = 'High' if max_score >= 8 else 'Medium' if max_score >= 4 else 'Low'

        return {
            'source': 'fallback',
            'total_distance_miles': round(dist, 2),
            'total_distance_m': round(dist * 1609),
            'walk_minutes': walk_min,
            'steps': steps,
            'step_count': 2,
            'overall_risk': overall,
            'max_step_risk_score': round(max_score, 2),
            'avg_step_risk_score': round((start_risk['risk_score'] + end_risk['risk_score']) / 2, 2),
            'hotspot_step': steps[0] if start_risk['risk_score'] >= end_risk['risk_score'] else steps[1],
        }