import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import json

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="TigerTown | Campus Safety Intelligence Platform",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ══════════════════════════════════════════════════════════════════════════════
# PROFESSIONAL CSS
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  
  /* ── Base ── */
  * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
  .main { padding: 0 !important; background: #f8f9fb; }
  .block-container { padding: 0 !important; max-width: 100% !important; }
  #MainMenu, footer, header { visibility: hidden; }
  
  /* ── Navigation Bar ── */
  .navbar {
    background: linear-gradient(135deg, #1a2332 0%, #2d3748 100%);
    padding: 0.9rem 2rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.15);
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0;
  }
  
  .logo-container {
    display: flex;
    align-items: center;
    gap: 0.9rem;
  }
  
  .logo-hex {
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, #00d4ff 0%, #0ea5e9 100%);
    clip-path: polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%);
    position: relative;
  }
  
  .logo-hex::before {
    content: '';
    position: absolute;
    inset: 3px;
    background: #1a2332;
    clip-path: polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%);
  }
  
  .brand-name {
    font-size: 1.5rem;
    font-weight: 700;
    color: white;
    letter-spacing: -0.5px;
  }
  
  .brand-tagline {
    font-size: 0.75rem;
    color: #94a3b8;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 1px;
  }
  
  .nav-meta {
    display: flex;
    align-items: center;
    gap: 2rem;
    color: #94a3b8;
    font-size: 0.85rem;
  }
  
  .nav-meta strong { color: #00d4ff; }
  
  /* ── Hero Section ── */
  .hero {
    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
    padding: 2.5rem 2rem;
    color: white;
    border-bottom: 3px solid #00d4ff;
  }
  
  .hero-title {
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
    background: linear-gradient(135deg, #ffffff 0%, #94a3b8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  
  .hero-subtitle {
    font-size: 1.1rem;
    color: #cbd5e1;
    font-weight: 400;
    line-height: 1.6;
  }
  
  /* ── KPI Cards ── */
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    margin: 1.5rem 2rem;
  }
  
  .kpi-card {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    border: 1px solid #e2e8f0;
    transition: all 0.2s;
  }
  
  .kpi-card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.12);
    transform: translateY(-2px);
  }
  
  .kpi-label {
    font-size: 0.8rem;
    color: #64748b;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 0.5rem;
  }
  
  .kpi-value {
    font-size: 2.5rem;
    font-weight: 700;
    color: #1e293b;
    line-height: 1;
    margin-bottom: 0.3rem;
  }
  
  .kpi-value.danger  { color: #dc2626; }
  .kpi-value.warning { color: #f59e0b; }
  .kpi-value.success { color: #10b981; }
  .kpi-value.info    { color: #00d4ff; }
  
  .kpi-change {
    font-size: 0.8rem;
    color: #64748b;
    display: flex;
    align-items: center;
    gap: 0.3rem;
  }
  
  .kpi-change.positive { color: #10b981; }
  .kpi-change.negative { color: #dc2626; }
  
  /* ── Section Containers ── */
  .section {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    margin: 1rem 2rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    border: 1px solid #e2e8f0;
  }
  
  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 2px solid #f1f5f9;
  }
  
  .section-title {
    font-size: 1.3rem;
    font-weight: 700;
    color: #1e293b;
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }
  
  .section-subtitle {
    font-size: 0.85rem;
    color: #64748b;
    font-weight: 500;
  }
  
  /* ── Priority Badge ── */
  .priority-badge {
    display: inline-block;
    padding: 0.35rem 0.8rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  
  .priority-critical { background: #fee2e2; color: #991b1b; }
  .priority-high     { background: #fed7aa; color: #9a3412; }
  .priority-medium   { background: #fef3c7; color: #92400e; }
  .priority-low      { background: #d1fae5; color: #065f46; }
  
  /* ── Recommendation Cards ── */
  .rec-card {
    background: #f8fafc;
    border-left: 4px solid #00d4ff;
    padding: 1.2rem;
    margin: 0.8rem 0;
    border-radius: 8px;
    transition: all 0.2s;
  }
  
  .rec-card:hover {
    background: #f1f5f9;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  }
  
  .rec-card.critical { border-left-color: #dc2626; }
  .rec-card.high     { border-left-color: #f59e0b; }
  .rec-card.medium   { border-left-color: #3b82f6; }
  
  .rec-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 0.8rem;
  }
  
  .rec-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: #1e293b;
    line-height: 1.4;
  }
  
  .rec-meta {
    font-size: 0.8rem;
    color: #64748b;
    display: flex;
    gap: 1.5rem;
    margin-top: 0.5rem;
  }
  
  .rec-metric {
    display: flex;
    align-items: center;
    gap: 0.3rem;
  }
  
  /* ── Impact Pill ── */
  .impact-pill {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: white;
    padding: 0.4rem 0.9rem;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
    white-space: nowrap;
  }
  
  /* ── Tabs ── */
  .stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem;
    background: #f8fafc;
    padding: 0.5rem;
    border-radius: 10px;
  }
  
  .stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 8px;
    padding: 0.7rem 1.5rem;
    font-weight: 600;
    color: #64748b;
  }
  
  .stTabs [aria-selected="true"] {
    background: white;
    color: #1e293b;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  }
  
  /* ── Data Table Styling ── */
  .dataframe {
    font-size: 0.85rem !important;
    border: none !important;
  }
  
  .dataframe th {
    background: #f1f5f9 !important;
    color: #475569 !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.5px !important;
  }
  
  .dataframe td {
    border-bottom: 1px solid #f1f5f9 !important;
  }
  
  /* ── Export Button ── */
  .stDownloadButton > button {
    background: linear-gradient(135deg, #00d4ff 0%, #0ea5e9 100%) !important;
    color: white !important;
    border: none !important;
    font-weight: 600 !important;
    padding: 0.6rem 1.5rem !important;
    border-radius: 8px !important;
    box-shadow: 0 2px 8px rgba(0, 212, 255, 0.3) !important;
  }
  
  .stDownloadButton > button:hover {
    box-shadow: 0 4px 12px rgba(0, 212, 255, 0.4) !important;
    transform: translateY(-1px);
  }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data
def load_data():
    crime_df = pd.read_csv('crime_data_clean.csv')
    crime_df['date'] = pd.to_datetime(crime_df['date'])
    with open('safety_insights.json') as f:
        insights = json.load(f)
    return crime_df, insights

crime_df, insights = load_data()

# ══════════════════════════════════════════════════════════════════════════════
# MOCK ENVIRONMENTAL DATA (replace with real data when available)
# ══════════════════════════════════════════════════════════════════════════════

# Sample hotspots with environmental issues
hotspots = [
    {
        "id": 1,
        "location": "Parking Structure B - East Stairwell",
        "lat": 38.9398, "lon": -92.3285,
        "incidents": 23,
        "severity": "Critical",
        "root_causes": [
            "No lighting after parking structure",
            "Blind corner at stairwell entrance",
            "Overgrown hedge blocks sightline from street"
        ],
        "recommendations": [
            {"item": "Install 2 LED light poles", "cost": "$8,500", "impact": "60% reduction"},
            {"item": "Trim hedge line to 3ft height", "cost": "$450", "impact": "25% reduction"},
            {"item": "Add convex security mirror at corner", "cost": "$320", "impact": "15% reduction"}
        ],
        "estimated_reduction": "75%",
        "total_cost": "$9,270",
        "payback_months": 8
    },
    {
        "id": 2,
        "location": "Memorial Union North Path",
        "lat": 38.9405, "lon": -92.3275,
        "incidents": 18,
        "severity": "High",
        "root_causes": [
            "Emergency call box out of service (90+ days)",
            "Low foot traffic after 9 PM",
            "Dense tree canopy blocks ambient light"
        ],
        "recommendations": [
            {"item": "Repair call box CB-047", "cost": "$1,200", "impact": "40% reduction"},
            {"item": "Install motion-activated pathway lighting", "cost": "$6,800", "impact": "35% reduction"},
            {"item": "Selective tree pruning for light penetration", "cost": "$950", "impact": "20% reduction"}
        ],
        "estimated_reduction": "68%",
        "total_cost": "$8,950",
        "payback_months": 10
    },
    {
        "id": 3,
        "location": "Greektown Alley Corridor",
        "lat": 38.9392, "lon": -92.3295,
        "incidents": 15,
        "severity": "High",
        "root_causes": [
            "No visual surveillance from street",
            "Service entrance creates isolated alcove",
            "Single light fixture frequently burned out"
        ],
        "recommendations": [
            {"item": "Install security camera with monitoring", "cost": "$4,500", "impact": "55% reduction"},
            {"item": "Upgrade to vandal-resistant LED fixtures (3x)", "cost": "$2,100", "impact": "30% reduction"},
            {"item": "Paint walls light color for reflectivity", "cost": "$800", "impact": "10% reduction"}
        ],
        "estimated_reduction": "72%",
        "total_cost": "$7,400",
        "payback_months": 9
    },
    {
        "id": 4,
        "location": "Recreation Center South Entrance",
        "lat": 38.9388, "lon": -92.3298,
        "incidents": 12,
        "severity": "Medium",
        "root_causes": [
            "Bike rack placement creates visual barrier",
            "Landscape design allows concealment",
            "Poor pedestrian flow design"
        ],
        "recommendations": [
            {"item": "Relocate bike racks to visible location", "cost": "$1,800", "impact": "40% reduction"},
            {"item": "Replace dense shrubs with low groundcover", "cost": "$3,200", "impact": "35% reduction"},
            {"item": "Add blue light emergency marker", "cost": "$2,500", "impact": "20% reduction"}
        ],
        "estimated_reduction": "65%",
        "total_cost": "$7,500",
        "payback_months": 12
    }
]

# ══════════════════════════════════════════════════════════════════════════════
# NAVIGATION BAR
# ══════════════════════════════════════════════════════════════════════════════

st.markdown(f"""
<div class="navbar">
  <div class="logo-container">
    <div class="logo-hex"></div>
    <div>
      <div class="brand-name">SafetyLens</div>
      <div class="brand-tagline">Campus Safety Intelligence</div>
    </div>
  </div>
  <div class="nav-meta">
    <div>University of Missouri</div>
    <div>Updated <strong>{datetime.now().strftime('%b %d, %Y')}</strong></div>
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# HERO SECTION
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="hero">
  <div class="hero-title">Campus Safety Environmental Analysis</div>
  <div class="hero-subtitle">
    AI-powered CPTED (Crime Prevention Through Environmental Design) analysis 
    identifying infrastructure improvements to eliminate crime hotspots — not just avoid them.
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# KPI DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

total_incidents = len(crime_df)
total_hotspots = len(hotspots)
avg_reduction = sum([int(h['estimated_reduction'].rstrip('%')) for h in hotspots]) / len(hotspots)
total_investment = sum([int(h['total_cost'].replace('$','').replace(',','')) for h in hotspots])

st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-label">Active Hotspots</div>
    <div class="kpi-value danger">{total_hotspots}</div>
    <div class="kpi-change">Requiring immediate intervention</div>
  </div>
  
  <div class="kpi-card">
    <div class="kpi-label">Total Incidents (90d)</div>
    <div class="kpi-value warning">{sum([h['incidents'] for h in hotspots])}</div>
    <div class="kpi-change negative">↑ 18% vs. prior period</div>
  </div>
  
  <div class="kpi-card">
    <div class="kpi-label">Avg. Projected Reduction</div>
    <div class="kpi-value success">{avg_reduction:.0f}%</div>
    <div class="kpi-change positive">With environmental interventions</div>
  </div>
  
  <div class="kpi-card">
    <div class="kpi-label">Total Investment Needed</div>
    <div class="kpi-value info">${total_investment:,}</div>
    <div class="kpi-change">~9 month avg. payback period</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT TABS
# ══════════════════════════════════════════════════════════════════════════════

tab_map, tab_recs, tab_impact, tab_export = st.tabs([
    "🗺️ Hotspot Map",
    "🔧 Recommendations", 
    "📊 Impact Analysis",
    "📄 Export Report"
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: HOTSPOT MAP
# ─────────────────────────────────────────────────────────────────────────────

with tab_map:
    st.markdown("""
    <div style="margin-bottom:1rem">
      <div style="font-size:1.3rem;font-weight:700;color:#1e293b;margin-bottom:0.3rem">🗺️ Crime Hotspot Overlay</div>
      <div style="font-size:0.85rem;color:#64748b">Spatial analysis of incident clusters with environmental context</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Create map
    fig = go.Figure()
    
    # Crime type color mapping (unique colors, no overlap with hotspot red/orange/blue)
    crime_colors = {
        'theft':      '#8B5CF6',  # Purple
        'assault':    '#EC4899',  # Pink
        'burglary':   '#14B8A6',  # Teal
        'vandalism':  '#466D1D',  # Fern Green
        'drug':       '#F97316',  # Orange (different shade from hotspot)
        'vehicle':    '#06B6D4',  # Cyan
        'harassment': '#D946EF',  # Fuchsia
        'other':      '#64748B',  # Slate gray
    }
    
    # Add crime incidents by category (darker, fully opaque)
    for category in crime_df['category'].unique():
        cat_data = crime_df[crime_df['category'] == category]
        fig.add_trace(go.Scattermapbox(
            lat=cat_data['lat'],
            lon=cat_data['lon'],
            mode='markers',
            marker=dict(
                size=7,
                color=crime_colors.get(category, '#455A64'),
                opacity=0.85,
            ),
            name=category.title(),
            text=cat_data['offense'],
            hovertemplate='<b>%{text}</b><br>Category: ' + category.title() + '<extra></extra>',
            showlegend=True,
            legendgroup='crimes'
        ))
    
    # Add hotspot markers with distinct icons and colors
    hotspot_configs = {
        'Critical': {'color': '#dc2626', 'size': 28, 'label': 'Critical Priority'},
        'High':     {'color': '#f59e0b', 'size': 24, 'label': 'High Priority'},
        'Medium':   {'color': '#3b82f6', 'size': 20, 'label': 'Medium Priority'},
    }
    
    # Group hotspots by severity to avoid duplicate legend entries
    hotspots_by_severity = {}
    for h in hotspots:
        sev = h['severity']
        if sev not in hotspots_by_severity:
            hotspots_by_severity[sev] = []
        hotspots_by_severity[sev].append(h)
    
    # Add one trace per severity level (prevents duplicates in legend)
    for severity, hs in hotspots_by_severity.items():
        config = hotspot_configs.get(severity, hotspot_configs['Medium'])
        
        lats = [h['lat'] for h in hs]
        lons = [h['lon'] for h in hs]
        locations = [h['location'] for h in hs]
        hover_texts = []
        
        for h in hs:
            hover_text = f"""
            <b>{h['location']}</b><br>
            {h['incidents']} incidents (90 days)<br>
            Priority: {h['severity']}<br>
            Expected Reduction: {h['estimated_reduction']}<br>
            Investment: {h['total_cost']}<br>
            ROI: {h['payback_months']} month payback
            """
            hover_texts.append(hover_text)
        
        # Add single trace for this severity level
        fig.add_trace(go.Scattermapbox(
            lat=lats,
            lon=lons,
            mode='markers',
            marker=dict(
                size=config['size'],
                color=config['color'],
                opacity=0.95,
            ),
            name=f"{config['label']} Hotspot",
            text=locations,
            hovertext=hover_texts,
            hovertemplate='%{hovertext}<extra></extra>',
            showlegend=True,
            legendgroup='hotspots'
        ))
    
    # Center on campus
    center_lat = crime_df['lat'].mean()
    center_lon = crime_df['lon'].mean()
    
    fig.update_layout(
        mapbox=dict(
            style='open-street-map',
            center=dict(lat=center_lat, lon=center_lon),
            zoom=16
        ),
        height=650,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.98,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255, 255, 255, 0.95)",
            bordercolor="#e2e8f0",
            borderwidth=2,
            font=dict(size=11, color='#1e293b'),
            title=dict(
                text="<b>Map Legend</b>",
                font=dict(size=12, color='#1e293b')
            ),
            orientation="v",
            itemsizing='constant',
            tracegroupgap=8
        )
    )
    
    st.plotly_chart(fig, use_container_width=True, key="crime_hotspot_map")
    
    # Add summary stats below map
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div style="background:#fef2f2;padding:1rem;border-radius:8px;border-left:4px solid #dc2626">
          <div style="font-size:0.75rem;color:#991b1b;font-weight:600;text-transform:uppercase">Critical Hotspots</div>
          <div style="font-size:2rem;font-weight:700;color:#dc2626">{len([h for h in hotspots if h['severity']=='Critical'])}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="background:#fef3c7;padding:1rem;border-radius:8px;border-left:4px solid #f59e0b">
          <div style="font-size:0.75rem;color:#92400e;font-weight:600;text-transform:uppercase">High Priority</div>
          <div style="font-size:2rem;font-weight:700;color:#f59e0b">{len([h for h in hotspots if h['severity']=='High'])}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div style="background:#dbeafe;padding:1rem;border-radius:8px;border-left:4px solid #3b82f6">
          <div style="font-size:0.75rem;color:#1e40af;font-weight:600;text-transform:uppercase">Medium Priority</div>
          <div style="font-size:2rem;font-weight:700;color:#3b82f6">{len([h for h in hotspots if h['severity']=='Medium'])}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        total_crime_incidents = sum([h['incidents'] for h in hotspots])
        st.markdown(f"""
        <div style="background:#f1f5f9;padding:1rem;border-radius:8px;border-left:4px solid #64748b">
          <div style="font-size:0.75rem;color:#475569;font-weight:600;text-transform:uppercase">Total Incidents</div>
          <div style="font-size:2rem;font-weight:700;color:#1e293b">{total_crime_incidents}</div>
        </div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: RECOMMENDATIONS
# ─────────────────────────────────────────────────────────────────────────────

with tab_recs:
    st.markdown('<div class="section">', unsafe_allow_html=True)
    st.markdown("""
    <div class="section-header">
      <div>
        <div class="section-title">🔧 Prioritized Infrastructure Recommendations</div>
        <div class="section-subtitle">CPTED-based interventions ranked by cost-benefit impact</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Sort hotspots by severity and incidents
    severity_order = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3}
    sorted_hotspots = sorted(hotspots, key=lambda x: (severity_order[x['severity']], -x['incidents']))
    
    for h in sorted_hotspots:
        priority_class = h['severity'].lower()
        rec_class = {'Critical': 'critical', 'High': 'high', 'Medium': 'medium'}.get(h['severity'], 'medium')
        
        root_causes_html = '<br>'.join([f'• {cause}' for cause in h['root_causes']])
        
        st.markdown(f"""
        <div class="rec-card {rec_class}">
          <div class="rec-header">
            <div>
              <div class="rec-title">{h['location']}</div>
              <div class="rec-meta">
                <div class="rec-metric">📍 <strong>{h['incidents']} incidents</strong> in 90 days</div>
                <div class="rec-metric">💰 Investment: <strong>{h['total_cost']}</strong></div>
                <div class="rec-metric">⏱️ ROI: <strong>{h['payback_months']} months</strong></div>
              </div>
            </div>
            <div>
              <span class="priority-badge priority-{priority_class}">{h['severity']} Priority</span>
              <div style="margin-top:0.5rem">
                <span class="impact-pill">↓ {h['estimated_reduction']} crime reduction</span>
              </div>
            </div>
          </div>
          
          <div style="margin-top:1rem">
            <div style="font-weight:600;font-size:0.85rem;color:#64748b;margin-bottom:0.5rem">ROOT CAUSES (AI Analysis)</div>
            <div style="font-size:0.9rem;color:#475569;line-height:1.7">{root_causes_html}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Detailed recommendations table
        rec_df = pd.DataFrame(h['recommendations'])
        rec_df.columns = ['Intervention', 'Cost', 'Impact']
        st.dataframe(rec_df, use_container_width=True, hide_index=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3: IMPACT ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

with tab_impact:
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="section">', unsafe_allow_html=True)
        st.markdown("""
        <div class="section-title">📈 Projected Crime Reduction</div>
        """, unsafe_allow_html=True)
        
        # Bar chart of projected reductions
        reduction_data = pd.DataFrame([
            {'Location': h['location'][:30], 
             'Current': h['incidents'],
             'Projected': h['incidents'] * (1 - int(h['estimated_reduction'].rstrip('%'))/100)}
            for h in hotspots
        ])
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=reduction_data['Location'],
            x=reduction_data['Current'],
            name='Current Incidents',
            orientation='h',
            marker=dict(color='#dc2626')
        ))
        fig.add_trace(go.Bar(
            y=reduction_data['Location'],
            x=reduction_data['Projected'],
            name='Projected After Intervention',
            orientation='h',
            marker=dict(color='#10b981')
        ))
        
        fig.update_layout(
            barmode='group',
            height=400,
            margin=dict(l=0, r=0, t=20, b=0),
            legend=dict(orientation='h', y=1.05, x=0),
            xaxis_title="Incidents (90 days)",
            yaxis_title=""
        )
        
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="section">', unsafe_allow_html=True)
        st.markdown("""
        <div class="section-title">💵 Cost vs. Impact Matrix</div>
        """, unsafe_allow_html=True)
        
        # Scatter plot of cost vs impact
        scatter_data = pd.DataFrame([
            {
                'Location': h['location'][:20],
                'Cost': int(h['total_cost'].replace('$','').replace(',','')),
                'Impact': int(h['estimated_reduction'].rstrip('%')),
                'Incidents': h['incidents']
            }
            for h in hotspots
        ])
        
        fig = px.scatter(
            scatter_data,
            x='Cost',
            y='Impact',
            size='Incidents',
            color='Impact',
            color_continuous_scale='RdYlGn',
            hover_data=['Location'],
            labels={'Cost': 'Investment ($)', 'Impact': 'Crime Reduction (%)'}
        )
        
        fig.update_layout(
            height=400,
            margin=dict(l=0, r=0, t=20, b=0),
            coloraxis_colorbar=dict(title="Impact %")
        )
        
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Summary stats
    st.markdown('<div class="section">', unsafe_allow_html=True)
    st.markdown("""
    <div class="section-title">📊 Investment Summary</div>
    """, unsafe_allow_html=True)
    
    summary_col1, summary_col2, summary_col3 = st.columns(3)
    
    with summary_col1:
        total_current = sum([h['incidents'] for h in hotspots])
        total_projected = sum([h['incidents'] * (1 - int(h['estimated_reduction'].rstrip('%'))/100) for h in hotspots])
        incidents_prevented = total_current - total_projected
        
        st.metric(
            "Incidents Prevented Annually",
            f"{int(incidents_prevented * 4)}/year",
            f"-{int((incidents_prevented/total_current)*100)}%"
        )
    
    with summary_col2:
        st.metric(
            "Total Investment Required",
            f"${total_investment:,}",
            "One-time capital expense"
        )
    
    with summary_col3:
        # Assuming $15k cost per incident (national avg)
        savings = incidents_prevented * 4 * 15000
        st.metric(
            "Projected Annual Savings",
            f"${int(savings):,}",
            f"ROI: {int(savings/total_investment*100)}%"
        )
    
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4: EXPORT REPORT
# ─────────────────────────────────────────────────────────────────────────────

with tab_export:
    st.markdown('<div class="section">', unsafe_allow_html=True)
    st.markdown("""
    <div class="section-header">
      <div>
        <div class="section-title">📄 Executive Report Generator</div>
        <div class="section-subtitle">Export analysis for stakeholder review and budget approval</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Generate CSV export
    export_data = []
    for h in hotspots:
        for rec in h['recommendations']:
            export_data.append({
                'Location': h['location'],
                'Priority': h['severity'],
                'Current Incidents (90d)': h['incidents'],
                'Intervention': rec['item'],
                'Cost': rec['cost'],
                'Impact': rec['impact'],
                'Total Site Cost': h['total_cost'],
                'Site Reduction': h['estimated_reduction'],
                'Payback (months)': h['payback_months']
            })
    
    export_df = pd.DataFrame(export_data)
    csv = export_df.to_csv(index=False)
    
    st.download_button(
        label="📥 Download Full Report (CSV)",
        data=csv,
        file_name=f"safetylens_cpted_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Preview the data
    st.dataframe(export_df, use_container_width=True, height=400)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="text-align:center;padding:2rem;color:#94a3b8;font-size:0.85rem;background:#f8fafc;margin-top:2rem">
  <strong>SafetyLens</strong> — Powered by Multi-Agent AI & CPTED Analysis<br>
  University of Missouri | MUIDSI Hackathon 2026<br>
  <span style="font-size:0.75rem;color:#cbd5e1">
    Emergency: 911 | MUPD: 573-882-7201
  </span>
</div>
""", unsafe_allow_html=True)
