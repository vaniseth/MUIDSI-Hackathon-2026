"""
TigerTown — Campus Safety Intelligence Platform
Streamlit UI with Missouri License Plate theme
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import json
import sys
from pathlib import Path

# ── Backend integration (graceful fallback if modules unavailable) ────────────
ROOT = Path(__file__).parent
sys.path.append(str(ROOT))

BACKEND_AVAILABLE = False
scanner = None

try:
    from src.campus_scanner import CampusScanner
    from src.data_integrator import DataIntegrator
    BACKEND_AVAILABLE = True
except Exception:
    pass

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="TigerTown | Fix the Campus, Not the Route",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ══════════════════════════════════════════════════════════════════════════════
# MISSOURI LICENSE PLATE CSS
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=Source+Sans+3:wght@400;500;600&display=swap');

/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; }
.main { padding: 0 !important; background: #EDEAE0; }
.block-container { padding: 0 !important; max-width: 100% !important; }
#MainMenu, footer, header { visibility: hidden; }
.stApp { background: #EDEAE0; }

/* ── Font defaults ── */
body, p, div, span, label {
    font-family: 'Source Sans 3', Georgia, sans-serif;
    color: #1a1a2e;
}

/* ══════════════════════════════════════════
   TOP HEADER — the license plate
   ══════════════════════════════════════════ */
.plate-header {
    background: #F5F2E4;
    border-top: 8px solid #14532d;
    border-bottom: 6px solid #14532d;
    padding: 22px 52px 18px;
    display: flex;
    justify-content: center;
    align-items: center;
    position: relative;
    box-shadow: 0 3px 16px rgba(0,0,0,0.18);
}

/* Bolt holes */
.plate-header::before,
.plate-header::after {
    content: '';
    width: 18px; height: 18px;
    background: #d8d3c4;
    border: 3px solid #b8b0a0;
    border-radius: 50%;
    position: absolute;
    top: 50%; transform: translateY(-50%);
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.3);
}
.plate-header::before { left: 22px; }
.plate-header::after  { right: 22px; }

/* Meta info — top corners */
.plate-meta-left {
    position: absolute;
    left: 52px; top: 50%; transform: translateY(-50%);
    font-family: 'Oswald', sans-serif;
    font-size: 10px;
    letter-spacing: 0.18em;
    color: #8a7a5a;
    text-transform: uppercase;
    text-align: left;
    line-height: 1.6;
}
.plate-meta-right {
    position: absolute;
    right: 52px; top: 50%; transform: translateY(-50%);
    font-family: 'Oswald', sans-serif;
    font-size: 10px;
    letter-spacing: 0.15em;
    color: #8a7a5a;
    text-transform: uppercase;
    text-align: right;
    line-height: 1.6;
}
.plate-meta-right .status-live { color: #14532d; font-weight: 700; font-size: 11px; }

.plate-logo-area {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0;
}

/* The green road sign badge — now the hero */
.sign-badge {
    background: #2E7D32;
    border: 5px solid #1B5E20;
    border-radius: 8px;
    padding: 12px 36px 10px;
    display: flex;
    flex-direction: column;
    align-items: center;
    box-shadow: 3px 3px 0 #1B5E20, 6px 6px 0 rgba(0,0,0,0.15);
    position: relative;
}
.sign-badge::before {
    content: '';
    position: absolute;
    inset: 4px;
    border: 1px solid rgba(255,255,255,0.25);
    border-radius: 4px;
    pointer-events: none;
}
.sign-title {
    font-family: 'Oswald', sans-serif;
    font-size: 42px;
    font-weight: 700;
    color: white;
    letter-spacing: 0.14em;
    line-height: 1;
    text-shadow: 2px 2px 0 rgba(0,0,0,0.35);
}
.sign-paws { font-size: 28px; margin-left: 8px; vertical-align: middle; }
.sign-tagline {
    background: #F4B942;
    color: #3d2b00;
    font-family: 'Oswald', sans-serif;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    padding: 4px 14px;
    margin-top: 8px;
    border-radius: 2px;
    width: 100%;
    text-align: center;
    box-shadow: 1px 1px 0 rgba(0,0,0,0.2);
}

.plate-sub {
    font-family: 'Oswald', sans-serif;
    font-size: 10px;
    font-weight: 500;
    color: #8a7a5a;
    letter-spacing: 0.32em;
    text-transform: uppercase;
    margin-top: 10px;
    text-align: center;
}

/* Keep these for any remaining refs */
.plate-center { display: none; }
.plate-main-text { display: none; }
.plate-state { display: none; }
.plate-right { display: none; }
.plate-date { display: none; }
.plate-status { display: none; }

/* ══════════════════════════════════════════
   NAV STRIP
   ══════════════════════════════════════════ */
.nav-strip {
    background: #14532d;
    padding: 0 36px;
    display: flex;
    gap: 0;
}
.nav-item {
    padding: 12px 22px;
    font-family: 'Oswald', sans-serif;
    font-size: 13px;
    font-weight: 500;
    color: #86efac;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    border-bottom: 3px solid transparent;
    cursor: default;
    transition: color 0.2s;
}
.nav-item.active {
    color: #F4B942;
    border-bottom-color: #F4B942;
}

/* ══════════════════════════════════════════
   KPI ROW
   ══════════════════════════════════════════ */
.kpi-strip {
    background: #14532d;
    padding: 20px 32px;
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 12px;
}
.kpi-tile {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 4px;
    padding: 14px 16px;
    border-top: 3px solid;
    transition: background 0.2s;
}
.kpi-tile:hover { background: rgba(255,255,255,0.09); }
.kpi-tile.red    { border-top-color: #ef4444; }
.kpi-tile.amber  { border-top-color: #F4B942; }
.kpi-tile.green  { border-top-color: #4ade80; }
.kpi-tile.blue   { border-top-color: #60a5fa; }
.kpi-tile.teal   { border-top-color: #2dd4bf; }
.kpi-lbl {
    font-family: 'Oswald', sans-serif;
    font-size: 9px;
    font-weight: 500;
    letter-spacing: 0.25em;
    text-transform: uppercase;
    color: rgba(255,255,255,0.45);
    margin-bottom: 5px;
}
.kpi-val {
    font-family: 'Oswald', sans-serif;
    font-size: 30px;
    font-weight: 700;
    line-height: 1;
    color: white;
}
.kpi-val.red   { color: #fca5a5; }
.kpi-val.amber { color: #fcd34d; }
.kpi-val.green { color: #86efac; }
.kpi-val.blue  { color: #93c5fd; }
.kpi-val.teal  { color: #5eead4; }
.kpi-sub {
    font-size: 11px;
    color: rgba(255,255,255,0.35);
    margin-top: 3px;
    font-family: 'Source Sans 3', sans-serif;
}

/* ══════════════════════════════════════════
   ROAD SIGN SECTION HEADERS
   ══════════════════════════════════════════ */
.sign-header {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    background: #2E7D32;
    color: white;
    font-family: 'Oswald', sans-serif;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    padding: 7px 16px;
    border-radius: 4px;
    border: 2px solid #1B5E20;
    box-shadow: 2px 2px 0 #1B5E20;
    margin-bottom: 16px;
}
.sign-header.amber {
    background: #F4B942;
    color: #3d2b00;
    border-color: #c48f00;
    box-shadow: 2px 2px 0 #c48f00;
}
.sign-header.navy {
    background: #14532d;
    color: white;
    border-color: #0f3d1f;
    box-shadow: 2px 2px 0 #0f3d1f;
}
.sign-header.red {
    background: #b91c1c;
    color: white;
    border-color: #7f1d1d;
    box-shadow: 2px 2px 0 #7f1d1d;
}

/* ══════════════════════════════════════════
   CARDS
   ══════════════════════════════════════════ */
.card {
    background: #F5F2E4;
    border: 1px solid #ccc9b8;
    border-radius: 6px;
    padding: 20px;
    margin-bottom: 14px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
}
.card-title {
    font-family: 'Oswald', sans-serif;
    font-size: 16px;
    font-weight: 600;
    color: #14532d;
    letter-spacing: 0.06em;
    margin-bottom: 6px;
}
.card-body {
    font-size: 14px;
    color: #3a3830;
    line-height: 1.65;
}

/* Hotspot cards */
.hotspot-card {
    background: #F5F2E4;
    border: 1px solid #ccc9b8;
    border-left: 5px solid;
    border-radius: 0 6px 6px 0;
    padding: 18px 20px;
    margin-bottom: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    transition: box-shadow 0.2s, transform 0.15s;
}
.hotspot-card:hover {
    box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    transform: translateX(2px);
}
.hotspot-card.critical { border-left-color: #dc2626; }
.hotspot-card.high     { border-left-color: #F4B942; }
.hotspot-card.medium   { border-left-color: #14532d; }

.hotspot-location {
    font-family: 'Oswald', sans-serif;
    font-size: 17px;
    font-weight: 600;
    color: #14532d;
    letter-spacing: 0.04em;
}
.hotspot-meta {
    font-size: 12px;
    color: #6b6458;
    margin: 6px 0 10px;
    display: flex;
    gap: 20px;
    font-family: 'Oswald', sans-serif;
    letter-spacing: 0.08em;
}
.hotspot-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 3px;
    font-family: 'Oswald', sans-serif;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}
.badge-critical { background: #fee2e2; color: #7f1d1d; border: 1px solid #fca5a5; }
.badge-high     { background: #fef3c7; color: #78350f; border: 1px solid #fcd34d; }
.badge-medium   { background: #dcfce7; color: #14532d; border: 1px solid #86efac; }

.deficiency-item {
    font-size: 13px;
    color: #3a3830;
    padding: 3px 0;
    display: flex;
    gap: 8px;
    align-items: flex-start;
    line-height: 1.4;
}
.deficiency-bullet {
    color: #dc2626;
    font-weight: 700;
    flex-shrink: 0;
    margin-top: 1px;
}

/* Intervention rows */
.intervention-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 14px;
    background: white;
    border: 1px solid #e0ddd0;
    border-radius: 4px;
    margin: 6px 0;
    font-size: 13px;
}
.iv-name { font-weight: 600; color: #14532d; font-family: 'Oswald', sans-serif; letter-spacing: 0.04em; }
.iv-cost { color: #2E7D32; font-weight: 600; font-family: 'Oswald', sans-serif; }
.iv-impact { 
    background: #2E7D32; color: white;
    padding: 2px 9px; border-radius: 3px;
    font-size: 11px; font-weight: 600;
    font-family: 'Oswald', sans-serif;
    letter-spacing: 0.08em;
}

/* ROI summary bar */
.roi-bar {
    background: #14532d;
    color: white;
    border-radius: 4px;
    padding: 14px 18px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 14px;
    font-family: 'Oswald', sans-serif;
}
.roi-stat { text-align: center; }
.roi-num { font-size: 22px; font-weight: 700; color: #F4B942; }
.roi-lbl { font-size: 10px; letter-spacing: 0.15em; color: rgba(255,255,255,0.5); text-transform: uppercase; }

/* Survey callout */
.survey-box {
    background: #14532d;
    border-radius: 6px;
    padding: 18px 20px;
    margin-bottom: 16px;
}
.survey-box .s-title {
    font-family: 'Oswald', sans-serif;
    font-size: 13px;
    font-weight: 600;
    color: #F4B942;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-bottom: 10px;
}
.survey-stat {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    font-size: 13px;
    color: rgba(255,255,255,0.75);
}
.survey-stat:last-child { border-bottom: none; }
.survey-stat strong { color: white; font-weight: 600; }

/* Page content wrapper */
.page-body { padding: 20px 28px; }

/* Stframe tab override */
.stTabs [data-baseweb="tab-list"] {
    background: #e8e4d8;
    padding: 6px;
    border-radius: 6px;
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Oswald', sans-serif !important;
    font-weight: 500 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    font-size: 13px !important;
    color: #6b6458 !important;
    border-radius: 4px !important;
    padding: 8px 18px !important;
    border: none !important;
}
.stTabs [aria-selected="true"] {
    background: #14532d !important;
    color: white !important;
}
.stTabs [data-baseweb="tab-panel"] {
    padding: 16px 0 !important;
}

/* Divider */
.plate-divider {
    height: 3px;
    background: linear-gradient(to right, #14532d, #F4B942, #166534, #F4B942, #14532d);
    margin: 0;
}

/* Download btn */
.stDownloadButton > button {
    background: #2E7D32 !important;
    color: white !important;
    border: 2px solid #1B5E20 !important;
    font-family: 'Oswald', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    font-size: 13px !important;
    border-radius: 4px !important;
    box-shadow: 2px 2px 0 #1B5E20 !important;
    padding: 0.55rem 1.4rem !important;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300)
def load_data(hour_param: int):
    """Load real data from backend or return demo data."""
    if BACKEND_AVAILABLE:
        try:
            sc = CampusScanner(hour=hour_param)
            report = sc.analyze_top_hotspots(
                top_n=5, hour=hour_param,
                min_risk_score=0.3,
                include_policy_context=False,
                export=False
            )
            return report, "live"
        except Exception as e:
            pass

    # ── Demo / fallback data ──────────────────────────────────────────────────
    return {
        "generated_date": datetime.now().strftime("%B %d, %Y at %I:%M %p"),
        "locations_scanned": 22,
        "hotspots_analyzed": 5,
        "campus_risk_summary": {
            "high_risk_locations": 3,
            "medium_risk_locations": 8,
            "low_risk_locations": 11,
            "campus_risk_index": 5.2,
        },
        "infrastructure_gaps": {
            "locations_needing_lighting": 4,
            "locations_needing_call_box": 2,
            "isolated_locations": 3,
        },
        "campus_roi_summary": {
            "total_infrastructure_cost": 54200,
            "total_incidents_prevented": 47,
            "total_annual_savings": 414000,
            "overall_roi_pct": 663,
            "vs_consulting_savings": 145000,
        },
        "student_survey": {
            "available": True,
            "n": 25,
            "day_safety_avg": 4.76,
            "night_safety_avg": 3.72,
            "safety_drop": 1.04,
            "route_changed_pct": 44,
            "mizzou_safe_used_pct": 16,
            "top_unsafe_locations": [
                {"location": "Downtown",        "mentions": 22, "pct": 88},
                {"location": "Parking Garages", "mentions": 18, "pct": 72},
                {"location": "Hitt Street",     "mentions": 9,  "pct": 36},
                {"location": "Greek Town",      "mentions": 8,  "pct": 32},
                {"location": "Conley Ave",      "mentions": 7,  "pct": 28},
            ],
            "top_concerns": [
                {"concern": "Poor Lighting",  "pct": 56},
                {"concern": "Isolation",      "pct": 56},
                {"concern": "Harassment",     "pct": 44},
            ],
        },
        "temporal_analysis": {
            "by_hour": {f"{h:02d}:00": max(0, int(8 * (1 - abs(h-22)/12)**2)) for h in range(24)},
            "peak_hours": [("22:00", 8), ("23:00", 7), ("21:00", 6)],
            "night_pct": 71,
            "insight": "Peak incident hour: 22:00. Highest-incident day: Friday. 71% of incidents occur at night.",
        },
        "comparative_benchmarks": {
            "mu_rate_per_10k": 58,
            "peer_average_per_10k": 52,
            "top_quartile_per_10k": 31,
            "national_average_per_10k": 68,
            "current_ranking": "Above peer average",
            "projected_rate_per_10k": 34,
            "projected_ranking": "Top 30% nationally (estimated)",
        },
        "top_hotspots": [
            {
                "rank": 1,
                "location_name": "Parking Lot A1",
                "lat": 38.9450, "lon": -92.3240,
                "risk_level": "High",
                "risk_score": 8.1,
                "incident_count": 23,
                "dominant_crime": "theft",
                "viirs_luminance": 0.84,
                "viirs_label": "Dim",
                "viirs_source": "campus_estimate",
                "cpted_priority": "Critical",
                "deficiency_count": 4,
                "environmental_profile": {
                    "deficiencies": [
                        "Insufficient illumination: 0.84 nW/cm²/sr — below 2.0 nW/cm²/sr threshold [Dim]",
                        "Nearest call box 580ft away — exceeds 500ft safe threshold",
                        "Parking lot road type — surveillance score 3/10 [Very Poor]",
                        "Theft-dominant — concealment opportunities likely",
                    ],
                    "sightline": {"surveillance_score": 3.0, "surveillance_label": "Very Poor"},
                    "nearest_light": {"distance_ft": 310},
                    "nearest_call_box": {"distance_ft": 580},
                },
                "sightline": {"surveillance_score": 3.0, "surveillance_label": "Very Poor"},
                "cpted_report": (
                    "**Environmental Diagnosis**\n"
                    "Parking Lot A1 exhibits three compounding CPTED failures. "
                    "Satellite luminance (0.84 nW/cm²/sr) is 58% below the 2.0 nW/cm²/sr safe pedestrian threshold, "
                    "and the surrounding road network scores 3/10 for natural surveillance — "
                    "dominated by parking lot roads with minimal through-traffic.\n\n"
                    "**Root Cause Factors**\n"
                    "- Critical lighting deficit confirmed by VIIRS satellite measurement\n"
                    "- Emergency call box 580ft away (exceeds 500ft standard)\n"
                    "- Low natural surveillance: no primary/secondary roads within 300ft\n"
                    "- 78% of incidents occur after 8 PM — lighting is primary amplifier\n\n"
                    "**Priority Score**\nCritical — satellite-confirmed lighting gap combined with theft-dominant crime pattern and call box coverage failure."
                ),
                "roi": {
                    "financials": {
                        "total_infrastructure_cost": 19450,
                        "total_annual_savings": 156400,
                        "roi_percentage": 704,
                        "payback_label": "45 days",
                        "total_incidents_prevented": 14,
                    },
                    "interventions": [
                        {"priority": 1, "name": "LED Motion-Activated Light Pole", "quantity": 2,
                         "total_cost": 17000, "reduction_pct_low": 45, "reduction_pct_high": 65,
                         "reduction_pct_median": 55, "incidents_prevented": 12, "annual_savings": 102000,
                         "citation_count": 3, "citations": [
                             {"authors": "Welsh & Farrington", "year": 2008, "finding": "20-39% crime reduction from improved lighting"},
                             {"authors": "NIJ Campus Safety", "year": 2019, "finding": "45-65% nighttime reduction at pilot campuses"},
                         ]},
                        {"priority": 2, "name": "Emergency Blue-Light Call Box", "quantity": 1,
                         "total_cost": 12000, "reduction_pct_low": 15, "reduction_pct_high": 22,
                         "reduction_pct_median": 18, "incidents_prevented": 2, "annual_savings": 17000,
                         "citation_count": 1, "citations": [
                             {"authors": "COPS Office", "year": 2018, "finding": "15-22% personal crime reduction"},
                         ]},
                    ],
                },
            },
            {
                "rank": 2,
                "location_name": "Greek Town",
                "lat": 38.9395, "lon": -92.3320,
                "risk_level": "High",
                "risk_score": 7.4,
                "incident_count": 19,
                "dominant_crime": "harassment",
                "viirs_luminance": 1.21,
                "viirs_label": "Dim",
                "viirs_source": "campus_estimate",
                "cpted_priority": "High",
                "deficiency_count": 3,
                "environmental_profile": {
                    "deficiencies": [
                        "Insufficient illumination: 1.21 nW/cm²/sr below 2.0 nW/cm²/sr threshold",
                        "Weekend concentration: 62% of incidents Friday–Sunday",
                        "Harassment-dominant — isolation and poor sightlines are primary contributors",
                    ],
                    "sightline": {"surveillance_score": 5.2, "surveillance_label": "Moderate"},
                    "nearest_light": {"distance_ft": 180},
                    "nearest_call_box": {"distance_ft": 320},
                },
                "sightline": {"surveillance_score": 5.2, "surveillance_label": "Moderate"},
                "cpted_report": (
                    "**Environmental Diagnosis**\n"
                    "Greek Town exhibits a clear temporal pattern — 62% of incidents cluster on weekends "
                    "after 10 PM, correlated with the lighting gap (1.21 nW/cm²/sr, 40% below safe threshold). "
                    "Road network surveillance is moderate (5.2/10), providing some deterrence during peak hours "
                    "but insufficient after the area empties post-midnight.\n\n"
                    "**Root Cause Factors**\n"
                    "- Lighting 40% below safe pedestrian threshold (VIIRS measured)\n"
                    "- Weekend/Friday incident spike (62%) — activity programming gap\n"
                    "- Harassment-dominant pattern suggests isolation opportunities\n\n"
                    "**Priority Score**\nHigh — temporal pattern strongly suggests motion-activated lighting as primary intervention."
                ),
                "roi": {
                    "financials": {
                        "total_infrastructure_cost": 8950,
                        "total_annual_savings": 69200,
                        "roi_percentage": 673,
                        "payback_label": "47 days",
                        "total_incidents_prevented": 10,
                    },
                    "interventions": [
                        {"priority": 1, "name": "LED Motion-Activated Light Pole", "quantity": 1,
                         "total_cost": 8500, "reduction_pct_low": 30, "reduction_pct_high": 55,
                         "reduction_pct_median": 42, "incidents_prevented": 8, "annual_savings": 56000,
                         "citation_count": 2, "citations": [
                             {"authors": "Chalfin et al.", "year": 2022, "finding": "36% reduction in nighttime crime"},
                         ]},
                        {"priority": 2, "name": "Safety Signage Package", "quantity": 2,
                         "total_cost": 700, "reduction_pct_low": 5, "reduction_pct_high": 15,
                         "reduction_pct_median": 10, "incidents_prevented": 2, "annual_savings": 14000,
                         "citation_count": 1, "citations": []},
                    ],
                },
            },
            {
                "rank": 3,
                "location_name": "Hitt Street Corridor",
                "lat": 38.9415, "lon": -92.3280,
                "risk_level": "High",
                "risk_score": 6.8,
                "incident_count": 16,
                "dominant_crime": "assault",
                "viirs_luminance": 0.61,
                "viirs_label": "Dim",
                "viirs_source": "campus_estimate",
                "cpted_priority": "High",
                "deficiency_count": 3,
                "environmental_profile": {
                    "deficiencies": [
                        "Insufficient illumination: 0.61 nW/cm²/sr — severely underlit [Dim]",
                        "Assault-dominant — isolation and poor sightlines are primary contributors",
                        "69% of incidents occur after 8 PM",
                    ],
                    "sightline": {"surveillance_score": 4.1, "surveillance_label": "Poor"},
                    "nearest_light": {"distance_ft": 260},
                    "nearest_call_box": {"distance_ft": 420},
                },
                "sightline": {"surveillance_score": 4.1, "surveillance_label": "Poor"},
                "cpted_report": (
                    "**Environmental Diagnosis**\n"
                    "Hitt Street Corridor is severely underlit at 0.61 nW/cm²/sr — 70% below the safe pedestrian minimum — "
                    "with a road surveillance score of 4.1/10. The corridor functions as a connecting pathway with "
                    "limited natural surveillance after 9 PM, creating the isolation conditions associated with "
                    "the assault-dominant crime pattern.\n\n"
                    "**Root Cause Factors**\n"
                    "- Severely underlit (0.61 nW/cm²/sr, 70% below threshold)\n"
                    "- Road surveillance 4.1/10 — connector path with low through-traffic\n"
                    "- 69% nighttime concentration\n\n"
                    "**Priority Score**\nHigh — assault pattern with severe lighting gap demands immediate lighting intervention."
                ),
                "roi": {
                    "financials": {
                        "total_infrastructure_cost": 17450,
                        "total_annual_savings": 119600,
                        "roi_percentage": 585,
                        "payback_label": "53 days",
                        "total_incidents_prevented": 11,
                    },
                    "interventions": [
                        {"priority": 1, "name": "LED Motion-Activated Light Pole", "quantity": 2,
                         "total_cost": 17000, "reduction_pct_low": 45, "reduction_pct_high": 65,
                         "reduction_pct_median": 55, "incidents_prevented": 9, "annual_savings": 99000,
                         "citation_count": 3, "citations": [
                             {"authors": "Welsh & Farrington", "year": 2008, "finding": "20-39% crime reduction"},
                         ]},
                        {"priority": 2, "name": "Vegetation Management", "quantity": 1,
                         "total_cost": 450, "reduction_pct_low": 9, "reduction_pct_high": 29,
                         "reduction_pct_median": 19, "incidents_prevented": 2, "annual_savings": 22000,
                         "citation_count": 2, "citations": [
                             {"authors": "Kondo et al.", "year": 2018, "finding": "9-29% crime reduction"},
                         ]},
                    ],
                },
            },
            {
                "rank": 4,
                "location_name": "Conley Ave Corridor",
                "lat": 38.9380, "lon": -92.3250,
                "risk_level": "Medium",
                "risk_score": 5.3,
                "incident_count": 12,
                "dominant_crime": "theft",
                "viirs_luminance": 1.54,
                "viirs_label": "Dim",
                "viirs_source": "campus_estimate",
                "cpted_priority": "Medium",
                "deficiency_count": 2,
                "environmental_profile": {
                    "deficiencies": [
                        "Insufficient illumination: 1.54 nW/cm²/sr below 2.0 nW/cm²/sr threshold",
                        "Theft-dominant — concealment opportunities likely",
                    ],
                    "sightline": {"surveillance_score": 6.1, "surveillance_label": "Moderate"},
                    "nearest_light": {"distance_ft": 155},
                    "nearest_call_box": {"distance_ft": 290},
                },
                "sightline": {"surveillance_score": 6.1, "surveillance_label": "Moderate"},
                "cpted_report": "Medium priority lighting improvement and vegetation management recommended.",
                "roi": {
                    "financials": {
                        "total_infrastructure_cost": 8950,
                        "total_annual_savings": 56400,
                        "roi_percentage": 530,
                        "payback_label": "58 days",
                        "total_incidents_prevented": 7,
                    },
                    "interventions": [
                        {"priority": 1, "name": "LED Motion-Activated Light Pole", "quantity": 1,
                         "total_cost": 8500, "reduction_pct_low": 30, "reduction_pct_high": 55,
                         "reduction_pct_median": 42, "incidents_prevented": 5, "annual_savings": 42000,
                         "citation_count": 2, "citations": []},
                        {"priority": 2, "name": "Vegetation Management", "quantity": 1,
                         "total_cost": 450, "reduction_pct_low": 9, "reduction_pct_high": 29,
                         "reduction_pct_median": 19, "incidents_prevented": 2, "annual_savings": 14400,
                         "citation_count": 2, "citations": []},
                    ],
                },
            },
            {
                "rank": 5,
                "location_name": "West Campus Connector",
                "lat": 38.9410, "lon": -92.3340,
                "risk_level": "Medium",
                "risk_score": 4.9,
                "incident_count": 9,
                "dominant_crime": "suspicious",
                "viirs_luminance": 1.82,
                "viirs_label": "Dim",
                "viirs_source": "campus_estimate",
                "cpted_priority": "Medium",
                "deficiency_count": 2,
                "environmental_profile": {
                    "deficiencies": [
                        "Insufficient illumination: 1.82 nW/cm²/sr just below 2.0 threshold",
                        "No high-traffic roads within 300ft — isolated location",
                    ],
                    "sightline": {"surveillance_score": 3.8, "surveillance_label": "Poor"},
                    "nearest_light": {"distance_ft": 210},
                    "nearest_call_box": {"distance_ft": 445},
                },
                "sightline": {"surveillance_score": 3.8, "surveillance_label": "Poor"},
                "cpted_report": "Medium priority — marginal lighting gap and low surveillance. Signage and minor lighting improvement recommended.",
                "roi": {
                    "financials": {
                        "total_infrastructure_cost": 8850,
                        "total_annual_savings": 45600,
                        "roi_percentage": 415,
                        "payback_label": "71 days",
                        "total_incidents_prevented": 6,
                    },
                    "interventions": [
                        {"priority": 1, "name": "LED Motion-Activated Light Pole", "quantity": 1,
                         "total_cost": 8500, "reduction_pct_low": 30, "reduction_pct_high": 55,
                         "reduction_pct_median": 42, "incidents_prevented": 4, "annual_savings": 36000,
                         "citation_count": 2, "citations": []},
                        {"priority": 2, "name": "Safety Signage Package", "quantity": 1,
                         "total_cost": 350, "reduction_pct_low": 5, "reduction_pct_high": 15,
                         "reduction_pct_median": 10, "incidents_prevented": 1, "annual_savings": 8000,
                         "citation_count": 1, "citations": []},
                    ],
                },
            },
        ],
    }, "demo"


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — controls
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### 🐾 TigerTown Controls")
    scan_hour = st.slider("Scan Hour", 0, 23, datetime.now().hour,
                          help="Simulate campus scan at this hour of day")
    top_n = st.selectbox("Hotspots to analyze", [3, 5, 8], index=1)
    st.divider()
    st.markdown("**Data Sources**")
    st.caption(f"Backend: {'🟢 Live' if BACKEND_AVAILABLE else '🟡 Demo data'}")
    if st.button("🔄 Refresh Scan"):
        st.cache_data.clear()
        st.rerun()

# ── Load data ─────────────────────────────────────────────────────────────────
report, data_mode = load_data(scan_hour)
summary  = report.get("campus_risk_summary", {})
gaps     = report.get("infrastructure_gaps", {})
roi_sum  = report.get("campus_roi_summary", {})
survey   = report.get("student_survey", {})
temporal = report.get("temporal_analysis", {})
bench    = report.get("comparative_benchmarks", {})
hotspots = report.get("top_hotspots", [])

# ══════════════════════════════════════════════════════════════════════════════
# HEADER — License Plate
# ══════════════════════════════════════════════════════════════════════════════

st.markdown(f"""
<div class="plate-header">
  <div class="plate-meta-left">
    University of Missouri<br>
    Campus Safety Intelligence
  </div>
  <div class="plate-logo-area">
    <div class="sign-badge">
      <div class="sign-title">TIGER TOWN <span class="sign-paws">🐾</span></div>
      <div class="sign-tagline">Fix the campus, not the route</div>
    </div>
    <div class="plate-sub">TigerTown · MUIDSI Hackathon 2026</div>
  </div>
  <div class="plate-meta-right">
    {report.get('generated_date', datetime.now().strftime('%b %d, %Y'))}<br>
    <span class="status-live">{"⬤ LIVE" if data_mode == "live" else "⬤ DEMO"}</span>
  </div>
</div>
<div class="plate-divider"></div>
""", unsafe_allow_html=True)

# ── KPI Strip ─────────────────────────────────────────────────────────────────
total_incidents = sum(h.get("incident_count", 0) for h in hotspots)
n_critical = sum(1 for h in hotspots if h.get("cpted_priority") == "Critical")

st.markdown(f"""
<div class="kpi-strip">
  <div class="kpi-tile red">
    <div class="kpi-lbl">Critical Hotspots</div>
    <div class="kpi-val red">{n_critical}</div>
    <div class="kpi-sub">Immediate action needed</div>
  </div>
  <div class="kpi-tile amber">
    <div class="kpi-lbl">Total Incidents (90d)</div>
    <div class="kpi-val amber">{total_incidents}</div>
    <div class="kpi-sub">Across top {len(hotspots)} hotspots</div>
  </div>
  <div class="kpi-tile green">
    <div class="kpi-lbl">Incidents Prevented/yr</div>
    <div class="kpi-val green">{roi_sum.get('total_incidents_prevented', 0)}</div>
    <div class="kpi-sub">With full intervention</div>
  </div>
  <div class="kpi-tile blue">
    <div class="kpi-lbl">Total Investment</div>
    <div class="kpi-val blue">${roi_sum.get('total_infrastructure_cost', 0):,}</div>
    <div class="kpi-sub">All hotspots combined</div>
  </div>
  <div class="kpi-tile teal">
    <div class="kpi-lbl">Overall ROI</div>
    <div class="kpi-val teal">{roi_sum.get('overall_roi_pct', 0)}%</div>
    <div class="kpi-sub">Annual savings / investment</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="page-body">', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════

tab_map, tab_recs, tab_impact, tab_survey, tab_export = st.tabs([
    "🗺️  Hotspot Map",
    "🔧  CPTED Recommendations",
    "📊  Impact & ROI",
    "📋  Student Survey",
    "📄  Export Report",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — MAP
# ─────────────────────────────────────────────────────────────────────────────

with tab_map:
    st.markdown('<div class="sign-header">🗺 Crime Hotspot Map — MU Campus</div>', unsafe_allow_html=True)

    fig = go.Figure()

    # Priority colors for hotspot markers
    priority_cfg = {
        "Critical": {"color": "#dc2626", "size": 28},
        "High":     {"color": "#F4B942", "size": 22},
        "Medium":   {"color": "#14532d", "size": 17},
    }

    # Group by priority to avoid legend duplicates
    grouped = {}
    for h in hotspots:
        p = h.get("cpted_priority", "Medium")
        grouped.setdefault(p, []).append(h)

    for priority, hs in grouped.items():
        cfg = priority_cfg.get(priority, priority_cfg["Medium"])
        hover = [
            f"<b>{h['location_name']}</b><br>"
            f"Risk: {h['risk_level']} ({h['risk_score']:.1f}/10)<br>"
            f"Incidents (90d): {h['incident_count']}<br>"
            f"Dominant crime: {h.get('dominant_crime','N/A')}<br>"
            f"VIIRS: {h.get('viirs_luminance', 0):.2f} nW/cm²/sr [{h.get('viirs_label','')}]<br>"
            f"Sightline: {h.get('sightline', {}).get('surveillance_score', 0):.1f}/10<br>"
            f"Investment: ${h.get('roi',{}).get('financials',{}).get('total_infrastructure_cost',0):,}<br>"
            f"ROI: {h.get('roi',{}).get('financials',{}).get('roi_percentage',0)}%"
            for h in hs
        ]
        fig.add_trace(go.Scattermapbox(
            lat=[h["lat"] for h in hs],
            lon=[h["lon"] for h in hs],
            mode="markers",
            name=f"{priority} Priority",
            marker=dict(size=cfg["size"], color=cfg["color"], opacity=0.92),
            hovertext=hover,
            hovertemplate="%{hovertext}<extra></extra>",
        ))

    # Center map on MU campus
    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=38.9420, lon=-92.3285),
            zoom=15,
        ),
        height=520,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            bgcolor="rgba(245,242,228,0.95)",
            bordercolor="#ccc9b8",
            borderwidth=1,
            font=dict(family="Oswald, sans-serif", size=12, color="#14532d"),
        ),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Summary row below map
    c1, c2, c3, c4 = st.columns(4)
    sightline_poor = sum(1 for h in hotspots
                         if h.get("sightline", {}).get("surveillance_score", 10) < 5)
    lighting_gaps  = sum(1 for h in hotspots
                         if h.get("viirs_luminance", 3) < 2.0)

    for col, (label, val, clr) in zip(
        [c1, c2, c3, c4],
        [
            ("Locations Scanned", report.get("locations_scanned", 22), "#14532d"),
            ("Lighting Gaps (VIIRS)", lighting_gaps, "#dc2626"),
            ("Poor Sightline (<5/10)", sightline_poor, "#F4B942"),
            ("Locations Scanned", gaps.get("locations_needing_call_box", 0), "#2E7D32"),
        ],
    ):
        lbl2 = ["Locations Scanned", "Lighting Gaps (VIIRS)",
                 "Poor Sightline (<5/10)", "Call Box Gaps"][
            [c1,c2,c3,c4].index(col)
        ]
        col.markdown(
            f'<div style="background:#F5F2E4;border:1px solid #ccc9b8;border-top:3px solid {clr};'
            f'border-radius:4px;padding:12px 14px;text-align:center">'
            f'<div style="font-family:Oswald,sans-serif;font-size:9px;letter-spacing:0.2em;'
            f'text-transform:uppercase;color:#8a7a5a;margin-bottom:4px">{lbl2}</div>'
            f'<div style="font-family:Oswald,sans-serif;font-size:28px;font-weight:700;color:{clr}">{val}</div>'
            f'</div>', unsafe_allow_html=True
        )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — RECOMMENDATIONS
# ─────────────────────────────────────────────────────────────────────────────

with tab_recs:
    st.markdown('<div class="sign-header">🔧 CPTED Infrastructure Recommendations</div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:13px;color:#6b6458;margin-bottom:18px">'
        'Ranked by risk score · Satellite-backed deficiency analysis · Academic citation support'
        '</div>', unsafe_allow_html=True
    )

    for h in hotspots:
        p        = h.get("cpted_priority", "Medium")
        env      = h.get("environmental_profile", {})
        roi      = h.get("roi", {})
        fin      = roi.get("financials", {})
        badge_cls = {"Critical": "badge-critical", "High": "badge-high", "Medium": "badge-medium"}.get(p, "badge-medium")
        card_cls  = p.lower()

        deficiencies = env.get("deficiencies", [])
        def_html = "".join(
            f'<div class="deficiency-item"><span class="deficiency-bullet">✗</span><span>{d}</span></div>'
            for d in deficiencies
        )

        st.markdown(f"""
        <div class="hotspot-card {card_cls}">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">
            <div>
              <div class="hotspot-location">#{h['rank']} {h['location_name']}</div>
              <div class="hotspot-meta">
                <span>📍 {h['incident_count']} incidents (90d)</span>
                <span>🔦 {h.get('viirs_luminance',0):.2f} nW/cm²/sr [{h.get('viirs_label','')}]</span>
                <span>👁 Sightline {h.get('sightline',{}).get('surveillance_score',0):.1f}/10</span>
                <span>⚠ {h.get('dominant_crime','N/A').title()}-dominant</span>
              </div>
            </div>
            <span class="hotspot-badge {badge_cls}">{p} Priority</span>
          </div>
          <div style="margin:10px 0 6px">
            <div style="font-family:Oswald,sans-serif;font-size:10px;letter-spacing:0.2em;color:#8a7a5a;text-transform:uppercase;margin-bottom:5px">Environmental Deficiencies</div>
            {def_html}
          </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander(f"  CPTED Analysis & Interventions — {h['location_name']}"):
            st.markdown(h.get("cpted_report", ""), unsafe_allow_html=False)
            st.markdown("---")
            st.markdown(
                '<div style="font-family:Oswald,sans-serif;font-size:10px;letter-spacing:0.2em;'
                'color:#8a7a5a;text-transform:uppercase;margin-bottom:8px">Recommended Interventions</div>',
                unsafe_allow_html=True
            )
            for iv in roi.get("interventions", []):
                cites = " · ".join(
                    f"{c['authors']} ({c['year']})" for c in iv.get("citations", [])
                )
                st.markdown(f"""
                <div class="intervention-row">
                  <div>
                    <div class="iv-name">P{iv['priority']} — {iv['name']}</div>
                    <div style="font-size:11px;color:#8a7a5a;margin-top:2px">{cites}</div>
                  </div>
                  <div style="display:flex;gap:14px;align-items:center">
                    <span class="iv-cost">${iv['total_cost']:,}</span>
                    <span class="iv-impact">↓ {iv['reduction_pct_median']}%</span>
                    <span style="font-size:11px;color:#2E7D32">${iv['annual_savings']:,}/yr saved</span>
                  </div>
                </div>
                """, unsafe_allow_html=True)

            if fin.get("total_infrastructure_cost", 0) > 0:
                st.markdown(f"""
                <div class="roi-bar">
                  <div class="roi-stat"><div class="roi-num">${fin['total_infrastructure_cost']:,}</div><div class="roi-lbl">Total Cost</div></div>
                  <div class="roi-stat"><div class="roi-num">{fin['total_incidents_prevented']}</div><div class="roi-lbl">Prevented/yr</div></div>
                  <div class="roi-stat"><div class="roi-num">${fin['total_annual_savings']:,}</div><div class="roi-lbl">Annual Savings</div></div>
                  <div class="roi-stat"><div class="roi-num">{fin['roi_percentage']}%</div><div class="roi-lbl">ROI</div></div>
                  <div class="roi-stat"><div class="roi-num">{fin['payback_label']}</div><div class="roi-lbl">Payback</div></div>
                </div>
                """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — IMPACT & ROI
# ─────────────────────────────────────────────────────────────────────────────

with tab_impact:
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown('<div class="sign-header">📉 Before vs. After — Incident Projection</div>', unsafe_allow_html=True)
        names    = [h["location_name"][:22] for h in hotspots]
        current  = [h["incident_count"] for h in hotspots]
        projected = [
            max(0, h["incident_count"] - h.get("roi",{}).get("financials",{}).get("total_incidents_prevented",0))
            for h in hotspots
        ]
        fig = go.Figure()
        fig.add_trace(go.Bar(y=names, x=current,   name="Current",   orientation="h",
                             marker_color="#dc2626"))
        fig.add_trace(go.Bar(y=names, x=projected, name="Projected", orientation="h",
                             marker_color="#2E7D32"))
        fig.update_layout(
            barmode="group", height=320,
            margin=dict(l=0,r=0,t=10,b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#F5F2E4",
            legend=dict(font=dict(family="Oswald, sans-serif")),
            xaxis=dict(title="Incidents (90d)", gridcolor="#e0ddd0"),
            yaxis=dict(gridcolor="#e0ddd0"),
            font=dict(family="Oswald, sans-serif"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.markdown('<div class="sign-header amber">⏱ Time-of-Day Incident Pattern</div>', unsafe_allow_html=True)
        by_hour = temporal.get("by_hour", {})
        if by_hour:
            hours  = list(by_hour.keys())
            counts = list(by_hour.values())
            colors = ["#dc2626" if (int(h.split(":")[0]) >= 20 or int(h.split(":")[0]) < 6)
                      else "#14532d" for h in hours]
            fig2 = go.Figure(go.Bar(
                x=hours, y=counts,
                marker_color=colors,
                hovertemplate="<b>%{x}</b><br>Incidents: %{y}<extra></extra>",
            ))
            fig2.update_layout(
                height=320,
                margin=dict(l=0,r=0,t=10,b=0),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#F5F2E4",
                xaxis=dict(tickangle=45, gridcolor="#e0ddd0", tickfont=dict(size=9)),
                yaxis=dict(gridcolor="#e0ddd0"),
                font=dict(family="Oswald, sans-serif"),
            )
            fig2.add_annotation(
                text="🔴 Night hours (8PM–6AM)", x=0.98, y=0.98,
                xref="paper", yref="paper", showarrow=False,
                font=dict(size=10, family="Oswald, sans-serif", color="#dc2626"),
                align="right",
            )
            st.plotly_chart(fig2, use_container_width=True)

    # Campus-wide ROI + peer benchmarks
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="sign-header navy">💰 Campus-Wide ROI Summary</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="card">
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
            <div><div style="font-family:Oswald,sans-serif;font-size:9px;letter-spacing:0.2em;text-transform:uppercase;color:#8a7a5a">Total Investment</div>
              <div style="font-family:Oswald,sans-serif;font-size:26px;font-weight:700;color:#14532d">${roi_sum.get('total_infrastructure_cost',0):,}</div></div>
            <div><div style="font-family:Oswald,sans-serif;font-size:9px;letter-spacing:0.2em;text-transform:uppercase;color:#8a7a5a">Annual Savings</div>
              <div style="font-family:Oswald,sans-serif;font-size:26px;font-weight:700;color:#2E7D32">${roi_sum.get('total_annual_savings',0):,}</div></div>
            <div><div style="font-family:Oswald,sans-serif;font-size:9px;letter-spacing:0.2em;text-transform:uppercase;color:#8a7a5a">Overall ROI</div>
              <div style="font-family:Oswald,sans-serif;font-size:26px;font-weight:700;color:#F4B942">{roi_sum.get('overall_roi_pct',0)}%</div></div>
            <div><div style="font-family:Oswald,sans-serif;font-size:9px;letter-spacing:0.2em;text-transform:uppercase;color:#8a7a5a">vs. Consulting Saves</div>
              <div style="font-family:Oswald,sans-serif;font-size:26px;font-weight:700;color:#14532d">${roi_sum.get('vs_consulting_savings',0):,}</div></div>
          </div>
          <div style="margin-top:14px;padding:10px 14px;background:#14532d;border-radius:4px;font-size:12px;color:rgba(255,255,255,0.7);font-family:Oswald,sans-serif;letter-spacing:0.06em">
            Based on $8,500 national avg. cost per campus incident · <span style="color:#F4B942">Traditional consulting: ~$150,000</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="sign-header amber">🏫 Peer Institution Benchmarks</div>', unsafe_allow_html=True)
        mu_rate   = bench.get("mu_rate_per_10k", 58)
        peer_avg  = bench.get("peer_average_per_10k", 52)
        top_q     = bench.get("top_quartile_per_10k", 31)
        projected = bench.get("projected_rate_per_10k", 34)

        fig3 = go.Figure(go.Bar(
            x=["MU Current", "Peer Average", "Top Quartile", "MU Projected"],
            y=[mu_rate, peer_avg, top_q, projected],
            marker_color=["#dc2626", "#F4B942", "#2E7D32", "#14532d"],
            text=[f"{v}/10k" for v in [mu_rate, peer_avg, top_q, projected]],
            textposition="outside",
            textfont=dict(family="Oswald, sans-serif", size=11),
        ))
        fig3.update_layout(
            height=240, margin=dict(l=0,r=0,t=24,b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#F5F2E4",
            yaxis=dict(title="Incidents per 10k students", gridcolor="#e0ddd0"),
            font=dict(family="Oswald, sans-serif"),
            showlegend=False,
        )
        st.plotly_chart(fig3, use_container_width=True)
        st.markdown(
            f'<div style="font-size:12px;color:#2E7D32;font-family:Oswald,sans-serif;letter-spacing:0.06em">'
            f'With interventions: {bench.get("projected_ranking","Top 30% nationally")}</div>',
            unsafe_allow_html=True
        )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — STUDENT SURVEY
# ─────────────────────────────────────────────────────────────────────────────

with tab_survey:
    st.markdown('<div class="sign-header">📋 Student Safety Survey — February 2026</div>', unsafe_allow_html=True)

    if not survey.get("available"):
        st.info("Survey data not loaded. Save survey CSV to data/crime_data/survey_results.csv")
    else:
        c1, c2 = st.columns([1, 1.4])

        with c1:
            st.markdown(f"""
            <div class="survey-box">
              <div class="s-title">Key Findings · n={survey['n']}</div>
              <div class="survey-stat">
                <span>Daytime safety avg</span>
                <strong>4.76 / 5</strong>
              </div>
              <div class="survey-stat">
                <span>Night safety avg</span>
                <strong style="color:#fcd34d">{survey['night_safety_avg']} / 5</strong>
              </div>
              <div class="survey-stat">
                <span>Safety drop after dark</span>
                <strong style="color:#fca5a5">↓ {survey['safety_drop']} pts</strong>
              </div>
              <div class="survey-stat">
                <span>Changed route due to safety</span>
                <strong>{survey['route_changed_pct']}% of students</strong>
              </div>
              <div class="survey-stat">
                <span>Use existing Mizzou Safe App</span>
                <strong style="color:#fca5a5">Only {survey['mizzou_safe_used_pct']}%</strong>
              </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown('<div class="sign-header" style="font-size:11px">Top Concerns</div>', unsafe_allow_html=True)
            for concern in survey.get("top_concerns", []):
                pct = concern["pct"]
                st.markdown(f"""
                <div style="margin-bottom:7px">
                  <div style="display:flex;justify-content:space-between;font-family:Oswald,sans-serif;font-size:12px;margin-bottom:3px">
                    <span style="color:#14532d;font-weight:600">{concern['concern']}</span>
                    <span style="color:#F4B942;font-weight:700">{pct}%</span>
                  </div>
                  <div style="background:#e0ddd0;border-radius:2px;height:6px">
                    <div style="background:#F4B942;width:{pct}%;height:100%;border-radius:2px"></div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="sign-header amber" style="font-size:11px">Unsafe Locations Reported</div>', unsafe_allow_html=True)
            locs = survey.get("top_unsafe_locations", [])
            if locs:
                loc_names = [l["location"] for l in locs]
                loc_pcts  = [l["pct"] for l in locs]
                fig4 = go.Figure(go.Bar(
                    y=loc_names[::-1], x=loc_pcts[::-1],
                    orientation="h",
                    marker_color="#14532d",
                    text=[f"{p}%" for p in loc_pcts[::-1]],
                    textposition="outside",
                    textfont=dict(family="Oswald, sans-serif", size=11, color="#14532d"),
                ))
                fig4.update_layout(
                    height=280, margin=dict(l=0,r=40,t=10,b=0),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="#F5F2E4",
                    xaxis=dict(title="% of students", gridcolor="#e0ddd0", range=[0,105]),
                    yaxis=dict(gridcolor="rgba(0,0,0,0)"),
                    font=dict(family="Oswald, sans-serif"),
                    showlegend=False,
                )
                st.plotly_chart(fig4, use_container_width=True)

            st.markdown(f"""
            <div class="card" style="margin-top:8px">
              <div class="card-title">Why This Validates Our Approach</div>
              <div class="card-body">
                <b>Poor lighting and isolation</b> each cited by 56% of students — exactly 
                what VIIRS satellite data and TIGER road analysis measure. 
                <b>{survey['route_changed_pct']}% of students</b> actively change their behavior 
                around these locations, confirming this is a real quality-of-life impact, not 
                just a statistical pattern. The incumbent app has <b>only {survey['mizzou_safe_used_pct']}% adoption</b> — 
                because telling students to avoid places isn't enough. Fix the campus.
              </div>
            </div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — EXPORT
# ─────────────────────────────────────────────────────────────────────────────

with tab_export:
    st.markdown('<div class="sign-header navy">📄 Export Report</div>', unsafe_allow_html=True)

    rows = []
    for h in hotspots:
        for iv in h.get("roi", {}).get("interventions", []):
            cites = " | ".join(
                f"{c['authors']} ({c['year']})" for c in iv.get("citations", [])
            )
            rows.append({
                "Rank": h["rank"],
                "Location": h["location_name"],
                "CPTED Priority": h.get("cpted_priority", ""),
                "Risk Score": h.get("risk_score", 0),
                "Incidents (90d)": h.get("incident_count", 0),
                "Dominant Crime": h.get("dominant_crime", ""),
                "VIIRS (nW/cm²/sr)": h.get("viirs_luminance", 0),
                "VIIRS Label": h.get("viirs_label", ""),
                "Sightline Score": h.get("sightline", {}).get("surveillance_score", 0),
                "Intervention Priority": iv["priority"],
                "Intervention": iv["name"],
                "Cost ($)": iv["total_cost"],
                "Reduction % Median": iv["reduction_pct_median"],
                "Incidents Prevented/yr": iv["incidents_prevented"],
                "Annual Savings ($)": iv["annual_savings"],
                "Citations": cites,
            })

    if rows:
        df = pd.DataFrame(rows)
        csv = df.to_csv(index=False)
        ts  = datetime.now().strftime("%Y%m%d_%H%M")

        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "📥 Download Interventions CSV",
                data=csv,
                file_name=f"tigertown_cpted_{ts}.csv",
                mime="text/csv",
            )
        with c2:
            json_out = json.dumps(report, indent=2, default=str)
            st.download_button(
                "📥 Download Full JSON Report",
                data=json_out,
                file_name=f"tigertown_report_{ts}.json",
                mime="application/json",
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True, height=420, hide_index=True)
    else:
        st.info("Run a campus scan to generate export data.")


# Footer
st.markdown("</div>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;padding:18px 32px;background:#14532d;margin-top:24px;
     font-family:Oswald,sans-serif;font-size:11px;letter-spacing:0.15em;color:rgba(255,255,255,0.4)">
  TIGERTOWN · TigerTown · UNIVERSITY OF MISSOURI · MUIDSI HACKATHON 2026
  &nbsp;·&nbsp; EMERGENCY: 911 &nbsp;·&nbsp; MUPD: 573-882-7201 &nbsp;·&nbsp; SAFE RIDE: 573-882-1010
</div>
""", unsafe_allow_html=True)