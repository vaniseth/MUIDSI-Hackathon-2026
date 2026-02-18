"""
Agent 3: CPTED Analysis Agent (Full Version)
============================================
Integrates:
  - VIIRS satellite nighttime luminance
  - TIGER/Line road network sightline analysis
  - ROI calculator with academic citations
  - Automated intervention prioritization

Dependency chain:
  CPTEDAgent -> VIIRSLoader  (satellite lighting)
  CPTEDAgent -> TIGERLoader  (road network/sightlines)
  CPTEDAgent -> ROICalculator (cost/citation engine)
  CPTEDAgent -> SafetyCopilot (Agent 1) for policy context
"""

import math
from typing import Dict, List, Optional
import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.archia_client import ArchiaClient
from src.viirs_loader import VIIRSLoader, THRESHOLD_DIM
from src.tiger_loader import TIGERLoader
from src.roi_calculator import ROICalculator


def _haversine(lat1, lon1, lat2, lon2) -> float:
    R = 3959
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    return R * 2 * math.asin(math.sqrt(a))


CALL_BOXES = [
    {"name": "Call Box - Memorial Union",    "lat": 38.9404, "lon": -92.3277},
    {"name": "Call Box - Ellis Library",     "lat": 38.9445, "lon": -92.3263},
    {"name": "Call Box - Rec Center",        "lat": 38.9389, "lon": -92.3301},
    {"name": "Call Box - Parking Garage A",  "lat": 38.9450, "lon": -92.3240},
    {"name": "Call Box - Student Center",    "lat": 38.9423, "lon": -92.3268},
    {"name": "Call Box - Engineering",       "lat": 38.9438, "lon": -92.3256},
    {"name": "Call Box - Conley Ave",        "lat": 38.9380, "lon": -92.3250},
    {"name": "Call Box - Hitt St",           "lat": 38.9415, "lon": -92.3280},
    {"name": "Call Box - Virginia Ave",      "lat": 38.9456, "lon": -92.3264},
    {"name": "Call Box - Greek Town",        "lat": 38.9395, "lon": -92.3320},
]

LIGHT_POLES = [
    {"name": "Light - Memorial Union North", "lat": 38.9408, "lon": -92.3280},
    {"name": "Light - Memorial Union South", "lat": 38.9400, "lon": -92.3275},
    {"name": "Light - Ellis Library East",   "lat": 38.9443, "lon": -92.3258},
    {"name": "Light - Student Center",       "lat": 38.9420, "lon": -92.3265},
    {"name": "Light - Rec Center Path",      "lat": 38.9392, "lon": -92.3298},
    {"name": "Light - Engineering Quad",     "lat": 38.9440, "lon": -92.3252},
    {"name": "Light - Conley Ave",           "lat": 38.9382, "lon": -92.3252},
    {"name": "Light - Greek Town Main",      "lat": 38.9398, "lon": -92.3318},
    {"name": "Light - Parking Garage A",     "lat": 38.9452, "lon": -92.3242},
    {"name": "Light - Virginia Ave",         "lat": 38.9455, "lon": -92.3260},
    {"name": "Light - Hitt St North",        "lat": 38.9418, "lon": -92.3282},
    {"name": "Light - Tiger Plaza",          "lat": 38.9432, "lon": -92.3273},
]

HIGH_TRAFFIC_CORRIDORS = [
    {"name": "Memorial Union to Jesse Hall", "lat": 38.9422, "lon": -92.3273},
    {"name": "Student Center to Rec Center", "lat": 38.9406, "lon": -92.3284},
    {"name": "Engineering Quad",             "lat": 38.9439, "lon": -92.3255},
    {"name": "Greek Town Main Strip",        "lat": 38.9397, "lon": -92.3322},
]

CPTED_SYSTEM_PROMPT = """You are a CPTED (Crime Prevention Through Environmental Design) expert 
consulting for the University of Missouri campus safety office.

Analyze the crime hotspot data and generate a professional infrastructure report for 
campus administrators and facilities management.

Output format (strictly follow):
**Environmental Diagnosis**
[2-3 sentences: WHY this location is a hotspot in environmental terms, referencing the 
satellite lighting data and road network analysis provided]

**Root Cause Factors**
[Bullet list of specific environmental deficiencies with data backing each one]

**Recommended Interventions**
[Numbered list. Each must include:
 What to do | Cost tier (Low/Medium/High) | Predicted incident reduction %]

**Priority Score**
[Critical / High / Medium — 1 sentence justification referencing the data]

Reference the VIIRS luminance values and road surveillance scores when relevant.
Be specific to MU campus. Under 300 words. Write for a facilities director.
"""


class CPTEDAgent:
    """
    Agent 3: Full CPTED Analysis Agent
    
    Integrates satellite lighting, road network analysis, ROI calculation,
    and academic citations into a comprehensive infrastructure report.
    """

    def __init__(self, safety_copilot=None):
        self.client = ArchiaClient()
        self.safety_copilot = safety_copilot
        self.viirs  = VIIRSLoader()
        self.tiger  = TIGERLoader()
        viirs_src = 'satellite' if self.viirs.has_real_data else 'estimated'
        tiger_src = 'shapefile' if self.tiger.has_real_data else 'estimated'
        print(f"  CPTED Agent: VIIRS={viirs_src} | TIGER={tiger_src}")

    def _nearest(self, lat, lon, locations):
        best, best_dist = None, float('inf')
        for loc in locations:
            d = _haversine(lat, lon, loc['lat'], loc['lon'])
            if d < best_dist:
                best_dist = d
                best = {**loc, 'distance_ft': round(d * 5280)}
        return best

    def _build_environmental_profile(self, lat, lon, risk_detail, location_name):
        nearest_light    = self._nearest(lat, lon, LIGHT_POLES)
        nearest_call_box = self._nearest(lat, lon, CALL_BOXES)
        nearest_corridor = self._nearest(lat, lon, HIGH_TRAFFIC_CORRIDORS)

        # VIIRS satellite luminance
        viirs_reading    = self.viirs.sample(lat, lon)
        luminance        = viirs_reading['luminance_nw']
        lighting_label   = viirs_reading['label']
        viirs_source     = viirs_reading['source']
        lighting_summary = self.viirs.get_lighting_summary(lat, lon)

        # TIGER road/sightline analysis
        sightline = self.tiger.get_sightline_analysis(lat, lon)

        viirs_lighting_gap = viirs_reading['below_threshold']
        pole_lighting_gap  = nearest_light['distance_ft'] > 200
        lighting_gap       = viirs_lighting_gap or pole_lighting_gap
        call_box_gap       = nearest_call_box['distance_ft'] > 500
        isolated           = (nearest_corridor['distance_ft'] > 400 or
                              sightline['surveillance_score'] < 5)
        night_dominant     = risk_detail.get('night_ratio', 0) >= 0.5
        weekend_spike      = risk_detail.get('weekend_ratio', 0) >= 0.5

        deficiencies = []

        # Lighting (VIIRS-backed)
        if viirs_lighting_gap:
            src_note = "satellite-measured" if viirs_source == "viirs_satellite" else "campus-estimated"
            deficiencies.append(
                f"Insufficient illumination: {luminance:.2f} nW/cm2/sr ({src_note}) "
                f"below {THRESHOLD_DIM} nW/cm2/sr safe pedestrian threshold [{lighting_label}]"
            )
        elif pole_lighting_gap:
            deficiencies.append(
                f"Nearest light pole {nearest_light['distance_ft']}ft away "
                f"({nearest_light['name']}) — exceeds 200ft spacing standard"
            )

        # Call box
        if call_box_gap:
            deficiencies.append(
                f"Call box coverage gap: nearest box {nearest_call_box['distance_ft']}ft "
                f"({nearest_call_box['name']}) — exceeds 500ft safe threshold"
            )

        # Sightline (TIGER-backed)
        for issue in sightline.get('sightline_issues', []):
            deficiencies.append(f"Road network: {issue}")

        if isolated and nearest_corridor['distance_ft'] > 400:
            deficiencies.append(
                f"Low natural surveillance: {nearest_corridor['distance_ft']}ft from "
                f"nearest high-traffic corridor ({nearest_corridor['name']})"
            )

        # Temporal
        if night_dominant:
            deficiencies.append(
                f"{round(risk_detail['night_ratio']*100)}% of incidents at night — "
                f"lighting is primary risk amplifier"
            )
        if weekend_spike:
            deficiencies.append(
                f"Weekend/Friday concentration ({round(risk_detail['weekend_ratio']*100)}%) "
                f"— targeted patrol or activity programming needed"
            )

        # Crime-type specific
        dominant = risk_detail.get('dominant_crime', 'unknown')
        if dominant == 'theft':
            deficiencies.append("Theft-dominant — concealment opportunities likely (vegetation, blind corners)")
        elif dominant == 'assault':
            deficiencies.append("Assault-dominant — isolation and poor sightlines are primary contributors")
        elif dominant == 'vehicle':
            deficiencies.append("Vehicle crime dominant — parking area lacks adequate lighting/surveillance")

        return {
            'location_name':       location_name,
            'lat': lat, 'lon': lon,
            'viirs_luminance':     luminance,
            'viirs_label':         lighting_label,
            'viirs_source':        viirs_source,
            'lighting_summary':    lighting_summary,
            'sightline':           sightline,
            'nearest_light':       nearest_light,
            'nearest_call_box':    nearest_call_box,
            'nearest_corridor':    nearest_corridor,
            'lighting_gap':        lighting_gap,
            'viirs_lighting_gap':  viirs_lighting_gap,
            'call_box_gap':        call_box_gap,
            'isolated':            isolated,
            'night_dominant':      night_dominant,
            'weekend_spike':       weekend_spike,
            'deficiencies':        deficiencies,
            'deficiency_count':    len(deficiencies),
        }

    def _get_policy_context(self, risk_detail, location_name):
        if self.safety_copilot is None:
            return ""
        dominant = risk_detail.get('dominant_crime', 'crime')
        query = (
            f"What does MU policy say about campus lighting standards, "
            f"emergency call box placement, and environmental design for "
            f"preventing {dominant} near {location_name}?"
        )
        try:
            response = self.safety_copilot.process_query(query)
            guidance = response.get('llm_guidance', '')
            return guidance if guidance and not guidance.startswith('Error') else ""
        except Exception:
            return ""

    def analyze_hotspot(self, lat, lon, risk_detail,
                        location_name="Campus Location",
                        include_policy_context=True) -> Dict:
        """Full CPTED analysis: environmental + VIIRS + TIGER + ROI + citations."""
        print(f"\n  Analyzing: {location_name}")
        print(f"   Risk: {risk_detail.get('risk_level')} | "
              f"Incidents: {risk_detail.get('incident_count')} | "
              f"Dominant: {risk_detail.get('dominant_crime')}")

        env = self._build_environmental_profile(lat, lon, risk_detail, location_name)
        print(f"   VIIRS: {env['viirs_luminance']:.2f} nW/cm2/sr [{env['viirs_label']}]")
        print(f"   TIGER sightline score: {env['sightline']['surveillance_score']}/10 "
              f"[{env['sightline']['surveillance_label']}]")

        # Policy context from Agent 1
        policy_context = ""
        if include_policy_context and self.safety_copilot:
            print(f"   Consulting Safety Copilot (Agent 1)...")
            policy_context = self._get_policy_context(risk_detail, location_name)

        # ROI calculation
        annual_incidents = max(1, risk_detail.get('incident_count', 1))
        roi_calc = ROICalculator(
            annual_incidents=annual_incidents,
            dominant_crime=risk_detail.get('dominant_crime', 'default'),
            location_name=location_name
        )
        roi_calc.from_deficiencies(env['deficiencies'], risk_detail, env)
        roi_result = roi_calc.calculate()

        # Build LLM prompt
        deficiency_text = "\n".join(f"  - {d}" for d in env['deficiencies']) \
            if env['deficiencies'] else "  - No major deficiencies detected"

        sightline = env['sightline']
        prompt = f"""Analyze this campus crime hotspot and generate a CPTED infrastructure report.

LOCATION: {location_name} | COORDINATES: {lat:.4f}, {lon:.4f}

CRIME DATA:
- Risk: {risk_detail.get('risk_level')} ({risk_detail.get('risk_score', 0)}/10) | Incidents: {annual_incidents}
- Dominant: {risk_detail.get('dominant_crime', 'N/A')} | Night rate: {round(risk_detail.get('night_ratio',0)*100)}%
- Pattern: {risk_detail.get('pattern_summary', 'N/A')}

SATELLITE LIGHTING (VIIRS):
- Luminance: {env['viirs_luminance']:.2f} nW/cm2/sr [{env['viirs_label']}] ({env['viirs_source']})
- Assessment: {env['lighting_summary']}

ROAD NETWORK SIGHTLINE (TIGER/Line 2025):
- Surveillance Score: {sightline['surveillance_score']}/10 [{sightline['surveillance_label']}]
- Dominant Road Type: {sightline['dominant_road_type']}
- Road Count (300ft): {sightline['road_count']}
- Issues: {'; '.join(sightline.get('sightline_issues', ['None']))}

INFRASTRUCTURE PROXIMITY:
- Nearest Light: {env['nearest_light']['name']} ({env['nearest_light']['distance_ft']}ft)
- Nearest Call Box: {env['nearest_call_box']['name']} ({env['nearest_call_box']['distance_ft']}ft)
- Nearest Corridor: {env['nearest_corridor']['name']} ({env['nearest_corridor']['distance_ft']}ft)

IDENTIFIED DEFICIENCIES:
{deficiency_text}

{"CAMPUS POLICY CONTEXT:" + chr(10) + policy_context if policy_context else ""}

Generate the CPTED infrastructure report now.
"""
        recommendation_text = self.client.chat(
            system_prompt=CPTED_SYSTEM_PROMPT,
            user_message=prompt,
            temperature=0.3,
            max_tokens=500
        )

        priority = 'Medium'
        lower = recommendation_text.lower()
        if 'critical' in lower:
            priority = 'Critical'
        elif 'high priority' in lower or 'high\n' in lower:
            priority = 'High'

        return {
            'agent':                 'cpted_agent',
            'location_name':         location_name,
            'lat': lat, 'lon': lon,
            'risk_detail':           risk_detail,
            'environmental_profile': env,
            'viirs_luminance':       env['viirs_luminance'],
            'viirs_label':           env['viirs_label'],
            'viirs_source':          env['viirs_source'],
            'sightline':             sightline,
            'policy_context':        policy_context,
            'cpted_report':          recommendation_text,
            'priority':              priority,
            'deficiency_count':      env['deficiency_count'],
            'roi':                   roi_result,
            'analyzed_at':           datetime.now().isoformat(),
        }

    def batch_analyze(self, hotspots, include_policy_context=True):
        results = []
        for i, spot in enumerate(hotspots):
            print(f"\n{'='*50}")
            print(f"Hotspot {i+1}/{len(hotspots)}: {spot.get('location_name')}")
            result = self.analyze_hotspot(
                lat=spot['lat'], lon=spot['lon'],
                risk_detail=spot['risk_detail'],
                location_name=spot.get('location_name', f'Location {i+1}'),
                include_policy_context=include_policy_context
            )
            results.append(result)
        results.sort(key=lambda r: r['risk_detail'].get('risk_score', 0), reverse=True)
        return results