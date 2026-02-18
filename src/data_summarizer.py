"""
Data Summarizer
===============
Converts structured data (CSV, shapefiles, rasters) into text chunks
suitable for embedding and RAG retrieval.

Without this, the FAISS index only contains PDF/TXT policy documents.
With this, the index also contains:
  - Per-location crime pattern summaries (from crime CSVs)
  - Road network sightline summaries (from TIGER shapefile)
  - Lighting condition summaries (from VIIRS + estimates)
  - Campus-wide statistical summaries

These chunks let Agent 1 (Safety Copilot) and Agent 3 (CPTED) answer
data-grounded questions like:
  "What are the crime patterns near Greek Town?"
  "Which campus areas have poor road surveillance?"
  "Where are the lighting gaps on campus?"
"""

import math
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import sys

sys.path.append(str(Path(__file__).parent.parent))
from src.config import DATA_DIR, CRIME_DATA_DIR, DOCSTORE_PATH

# Campus locations used for summarization
CAMPUS_LOCATIONS = [
    {"name": "Memorial Union",        "lat": 38.9404, "lon": -92.3277},
    {"name": "Jesse Hall",            "lat": 38.9441, "lon": -92.3269},
    {"name": "Ellis Library",         "lat": 38.9445, "lon": -92.3263},
    {"name": "Engineering Building",  "lat": 38.9438, "lon": -92.3256},
    {"name": "Student Center",        "lat": 38.9423, "lon": -92.3268},
    {"name": "Rec Center",            "lat": 38.9389, "lon": -92.3301},
    {"name": "Mizzou Arena",          "lat": 38.9356, "lon": -92.3332},
    {"name": "Greek Town",            "lat": 38.9395, "lon": -92.3320},
    {"name": "Tiger Plaza",           "lat": 38.9430, "lon": -92.3275},
    {"name": "Hitt Street Corridor",  "lat": 38.9415, "lon": -92.3280},
    {"name": "Conley Ave Corridor",   "lat": 38.9380, "lon": -92.3250},
    {"name": "Parking Lot A1",        "lat": 38.9450, "lon": -92.3240},
    {"name": "Parking Lot C2",        "lat": 38.9380, "lon": -92.3350},
    {"name": "North Campus Green",    "lat": 38.9465, "lon": -92.3270},
    {"name": "South Campus Path",     "lat": 38.9360, "lon": -92.3270},
    {"name": "West Campus Connector", "lat": 38.9410, "lon": -92.3340},
    {"name": "East Campus Entrance",  "lat": 38.9420, "lon": -92.3220},
]


def _haversine(lat1, lon1, lat2, lon2) -> float:
    R = 3959
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    return R * 2 * math.asin(math.sqrt(a))


def _make_chunk(chunk_id: str, text: str, source: str,
                metadata: Dict = None) -> Dict:
    return {
        'chunk_id':  chunk_id,
        'text':      text.strip(),
        'source':    source,
        'type':      'data_summary',
        'metadata':  metadata or {},
        'created_at': datetime.now().isoformat(),
    }


# ── Crime Data Summarizer ─────────────────────────────────────────────────────

def summarize_crime_data(radius_miles: float = 0.1) -> List[Dict]:
    """
    For each campus location, generate a text summary of nearby crime patterns.
    Returns list of text chunks ready for embedding.
    """
    chunks = []

    try:
        import pandas as pd
    except ImportError:
        print("  pandas not available — skipping crime data summarization")
        return []

    # Try loading integrated data first, then fallbacks
    candidates = [
        "crime_data_integrated.csv",
        "crime_data_clean__1_.csv",
        "crime_data_clean.csv",
        "mu_crime_log__2_.csv",
    ]
    df = None
    loaded_file = None
    for fname in candidates:
        fpath = CRIME_DATA_DIR / fname
        if fpath.exists():
            try:
                df = pd.read_csv(fpath)
                loaded_file = fname
                break
            except Exception:
                continue

    if df is None or df.empty:
        print("  No crime data found for summarization")
        return []

    print(f"  Summarizing crime data from {loaded_file} ({len(df)} records)...")

    # Ensure lat/lon columns exist
    if 'lat' not in df.columns or 'lon' not in df.columns:
        print("  Crime data has no lat/lon columns — skipping location summaries")
        # Still generate an overall summary
        chunks.append(_make_chunk(
            'crime_overall_summary',
            _overall_crime_summary(df),
            loaded_file,
            {'type': 'campus_wide'}
        ))
        return chunks

    # Per-location summaries
    for loc in CAMPUS_LOCATIONS:
        nearby = df[
            df.apply(lambda row: _haversine(
                loc['lat'], loc['lon'],
                row['lat'], row['lon']
            ) <= radius_miles if pd.notna(row.get('lat')) and pd.notna(row.get('lon'))
            else False, axis=1)
        ]

        if nearby.empty:
            # Still write a "no incidents" chunk — useful for RAG
            text = (
                f"Crime data summary for {loc['name']} (MU Campus, Missouri):\n"
                f"No recorded incidents within {round(radius_miles*5280)}ft "
                f"of this location in the dataset. "
                f"Location coordinates: {loc['lat']:.4f}N, {abs(loc['lon']):.4f}W."
            )
        else:
            text = _location_crime_summary(loc['name'], loc['lat'], loc['lon'], nearby)

        chunks.append(_make_chunk(
            f"crime_summary_{loc['name'].lower().replace(' ', '_')}",
            text,
            loaded_file,
            {'location': loc['name'], 'lat': loc['lat'], 'lon': loc['lon'],
             'incident_count': len(nearby)}
        ))

    # Campus-wide summary
    chunks.append(_make_chunk(
        'crime_campus_wide_summary',
        _overall_crime_summary(df),
        loaded_file,
        {'type': 'campus_wide', 'total_records': len(df)}
    ))

    # Category breakdown chunk
    chunks.append(_make_chunk(
        'crime_category_breakdown',
        _category_breakdown_summary(df),
        loaded_file,
        {'type': 'category_breakdown'}
    ))

    # Temporal pattern chunk
    chunks.append(_make_chunk(
        'crime_temporal_patterns',
        _temporal_summary(df),
        loaded_file,
        {'type': 'temporal_analysis'}
    ))

    print(f"  Generated {len(chunks)} crime data chunks")
    return chunks


def _location_crime_summary(name: str, lat: float, lon: float,
                             nearby_df) -> str:
    import pandas as pd

    total = len(nearby_df)

    # Category breakdown
    cat_col = next((c for c in ['category', 'offense_type', 'offense', 'crime_type']
                    if c in nearby_df.columns), None)
    cat_text = ""
    if cat_col:
        counts = nearby_df[cat_col].value_counts().head(3)
        parts = [f"{cat} ({cnt})" for cat, cnt in counts.items()]
        cat_text = f"Top crime types: {', '.join(parts)}. "
        dominant = counts.index[0] if len(counts) > 0 else 'unknown'
    else:
        dominant = 'unknown'

    # Temporal breakdown
    hour_col = next((c for c in ['hour', 'time_hour'] if c in nearby_df.columns), None)
    time_text = ""
    if hour_col:
        nearby_df = nearby_df.copy()
        nearby_df[hour_col] = pd.to_numeric(nearby_df[hour_col], errors='coerce')
        night_mask = (nearby_df[hour_col] >= 20) | (nearby_df[hour_col] < 6)
        night_pct = round(night_mask.mean() * 100)
        time_text = f"{night_pct}% of incidents occur between 8 PM and 6 AM (nighttime). "

    day_col = next((c for c in ['day_of_week', 'day'] if c in nearby_df.columns), None)
    day_text = ""
    if day_col:
        weekend_days = ['Friday', 'Saturday', 'Sunday']
        weekend_mask = nearby_df[day_col].isin(weekend_days)
        weekend_pct = round(weekend_mask.mean() * 100)
        if weekend_pct >= 40:
            day_text = f"{weekend_pct}% of incidents occur on weekends/Fridays. "

    # Severity
    sev_col = next((c for c in ['severity', 'crime_severity'] if c in nearby_df.columns), None)
    sev_text = ""
    if sev_col:
        avg_sev = round(nearby_df[sev_col].mean(), 1)
        sev_text = f"Average severity score: {avg_sev}/5. "

    return (
        f"Crime data summary for {name} area (MU Campus, Missouri):\n"
        f"Total recorded incidents within {round(0.1*5280)}ft: {total}. "
        f"{cat_text}"
        f"{time_text}"
        f"{day_text}"
        f"{sev_text}"
        f"This location has coordinates {lat:.4f}N, {abs(lon):.4f}W. "
        f"Dominant crime type: {dominant}. "
        f"This data is used by the CPTED analysis agent to prioritize "
        f"infrastructure improvements at this location."
    )


def _overall_crime_summary(df) -> str:
    import pandas as pd

    total = len(df)

    # Source breakdown
    src_text = ""
    if 'data_source' in df.columns:
        sources = df['data_source'].value_counts().to_dict()
        src_parts = [f"{src}: {cnt}" for src, cnt in sources.items()]
        src_text = f"Data sources: {', '.join(src_parts)}. "

    # Category breakdown
    cat_col = next((c for c in ['category', 'offense_type', 'offense'] if c in df.columns), None)
    cat_text = ""
    if cat_col:
        top = df[cat_col].value_counts().head(5)
        parts = [f"{cat} ({cnt})" for cat, cnt in top.items()]
        cat_text = f"Top crime categories: {', '.join(parts)}. "

    # Date range
    date_col = next((c for c in ['date', 'incident_date'] if c in df.columns), None)
    date_text = ""
    if date_col:
        try:
            dates = pd.to_datetime(df[date_col], errors='coerce').dropna()
            if len(dates) > 0:
                date_text = (f"Date range: {dates.min().strftime('%Y-%m-%d')} "
                            f"to {dates.max().strftime('%Y-%m-%d')}. ")
        except Exception:
            pass

    return (
        f"Campus-wide crime data summary for University of Missouri:\n"
        f"Total integrated records: {total}. "
        f"{src_text}"
        f"{date_text}"
        f"{cat_text}"
        f"This dataset covers the MU Columbia campus and surrounding areas "
        f"including incidents reported to MUPD and Columbia PD 911 dispatch."
    )


def _category_breakdown_summary(df) -> str:
    cat_col = next((c for c in ['category', 'offense_type', 'offense'] if c in df.columns), None)
    if not cat_col:
        return "Crime category breakdown not available — offense column not found in dataset."

    counts = df[cat_col].value_counts()
    total  = len(df)
    lines  = ["Crime category breakdown for MU campus area:"]
    for cat, cnt in counts.items():
        pct = round(cnt / total * 100, 1)
        lines.append(f"  {cat}: {cnt} incidents ({pct}%)")

    lines.append(
        "\nTheft and vehicle crimes are often linked to lighting and surveillance gaps. "
        "Assault and harassment are often linked to isolation and low foot traffic. "
        "CPTED interventions target the environmental conditions that enable each category."
    )
    return "\n".join(lines)


def _temporal_summary(df) -> str:
    import pandas as pd

    lines = ["Temporal crime patterns for MU campus:"]

    hour_col = next((c for c in ['hour', 'time_hour'] if c in df.columns), None)
    if hour_col:
        df = df.copy()
        df[hour_col] = pd.to_numeric(df[hour_col], errors='coerce')
        by_hour = df[hour_col].dropna().value_counts().sort_index()
        peak_hours = by_hour.nlargest(3).index.tolist()
        night_pct  = round(((df[hour_col] >= 20) | (df[hour_col] < 6)).mean() * 100)
        lines.append(f"Peak incident hours: {[f'{h:02d}:00' for h in peak_hours]}")
        lines.append(f"Nighttime incidents (8 PM - 6 AM): {night_pct}% of total")
        lines.append("Lighting interventions are most impactful for night-dominant locations.")

    day_col = next((c for c in ['day_of_week', 'day'] if c in df.columns), None)
    if day_col:
        by_day = df[day_col].value_counts()
        peak_day = by_day.index[0] if len(by_day) > 0 else 'unknown'
        lines.append(f"Highest-incident day of week: {peak_day}")
        weekend_days = ['Friday', 'Saturday', 'Sunday']
        weekend_pct = round(df[day_col].isin(weekend_days).mean() * 100)
        lines.append(f"Weekend/Friday concentration: {weekend_pct}%")

    lines.append(
        "Temporal patterns inform CPTED prioritization: "
        "night-dominant hotspots need lighting; "
        "weekend-dominant hotspots may need activity programming or patrol presence."
    )
    return "\n".join(lines)


# ── TIGER Road Summarizer ─────────────────────────────────────────────────────

def summarize_tiger_data() -> List[Dict]:
    """
    Generate text summaries of road network characteristics
    for each campus location using TIGER data.
    """
    chunks = []

    try:
        from src.tiger_loader import TIGERLoader
        loader = TIGERLoader()
    except Exception as e:
        print(f"  TIGER loader unavailable: {e}")
        return []

    print(f"  Summarizing TIGER road data for {len(CAMPUS_LOCATIONS)} locations...")

    for loc in CAMPUS_LOCATIONS:
        analysis = loader.get_sightline_analysis(loc['lat'], loc['lon'])
        text = _tiger_location_summary(loc['name'], loc['lat'], loc['lon'], analysis)
        chunks.append(_make_chunk(
            f"tiger_sightline_{loc['name'].lower().replace(' ', '_')}",
            text,
            'tiger_tl_2025_29019_roads',
            {'location': loc['name'], 'lat': loc['lat'], 'lon': loc['lon'],
             'surveillance_score': analysis['surveillance_score'],
             'source': analysis['source']}
        ))

    # Campus road network overview
    summary = loader.get_campus_road_summary()
    if 'total_segments' in summary:
        overview = (
            f"MU campus road network overview (US Census TIGER/Line 2025, Boone County MO):\n"
            f"Total road segments on campus: {summary['total_segments']}. "
            f"Road type breakdown: "
            + "; ".join(f"{rtype}: {cnt}" for rtype, cnt in
                        list(summary.get('by_type', {}).items())[:8])
            + ". "
            "Road types determine natural surveillance levels in CPTED analysis. "
            "Primary and secondary roads provide high surveillance (score 8-9/10). "
            "Alleys, service drives, and parking lot roads provide low surveillance (score 2-3/10). "
            "Pedestrian walkways score moderate (4-5/10) depending on foot traffic."
        )
        chunks.append(_make_chunk(
            'tiger_campus_road_overview',
            overview,
            'tiger_tl_2025_29019_roads',
            {'type': 'campus_overview', 'total_segments': summary['total_segments']}
        ))

    print(f"  Generated {len(chunks)} TIGER sightline chunks")
    return chunks


def _tiger_location_summary(name: str, lat: float, lon: float,
                             analysis: Dict) -> str:
    score  = analysis['surveillance_score']
    label  = analysis['surveillance_label']
    dom    = analysis['dominant_road_type']
    count  = analysis['road_count']
    source = analysis['source']
    issues = analysis.get('sightline_issues', [])

    issue_text = ""
    if issues:
        issue_text = "Sightline issues: " + "; ".join(issues) + ". "

    risk_note = ""
    if score < 4:
        risk_note = (
            "This low surveillance score indicates the location is a CPTED risk factor. "
            "Low road surveillance correlates with higher crime rates — "
            "few passersby means fewer natural witnesses to deter offenders. "
        )
    elif score >= 7:
        risk_note = (
            "This high surveillance score is a protective factor. "
            "High road density and traffic volume provide natural deterrence. "
        )

    return (
        f"Road network sightline analysis for {name} (MU Campus, Missouri):\n"
        f"Natural surveillance score: {score}/10 [{label}] "
        f"(source: {source}). "
        f"Dominant road type within 300ft: {dom}. "
        f"Road segments within 300ft: {count}. "
        f"{issue_text}"
        f"{risk_note}"
        f"Location coordinates: {lat:.4f}N, {abs(lon):.4f}W. "
        f"Road classification data from US Census TIGER/Line 2025, Boone County MO (FIPS 29019)."
    )


# ── VIIRS Lighting Summarizer ─────────────────────────────────────────────────

def summarize_viirs_data() -> List[Dict]:
    """
    Generate text summaries of nighttime lighting conditions
    for each campus location using VIIRS data.
    """
    chunks = []

    try:
        from src.viirs_loader import VIIRSLoader, THRESHOLD_DIM, THRESHOLD_ADEQUATE
        loader = VIIRSLoader()
    except Exception as e:
        print(f"  VIIRS loader unavailable: {e}")
        return []

    print(f"  Summarizing VIIRS lighting data for {len(CAMPUS_LOCATIONS)} locations...")

    for loc in CAMPUS_LOCATIONS:
        reading = loader.sample(loc['lat'], loc['lon'])
        summary = loader.get_lighting_summary(loc['lat'], loc['lon'])
        text    = _viirs_location_summary(loc['name'], loc['lat'], loc['lon'],
                                           reading, summary)
        chunks.append(_make_chunk(
            f"viirs_lighting_{loc['name'].lower().replace(' ', '_')}",
            text,
            f"viirs_{reading['source']}",
            {'location': loc['name'], 'lat': loc['lat'], 'lon': loc['lon'],
             'luminance': reading['luminance_nw'], 'label': reading['label'],
             'source': reading['source'], 'below_threshold': reading['below_threshold']}
        ))

    # Campus lighting overview
    readings = [loader.sample(l['lat'], l['lon']) for l in CAMPUS_LOCATIONS]
    dark_count     = sum(1 for r in readings if r['luminance_nw'] < 0.5)
    dim_count      = sum(1 for r in readings if 0.5 <= r['luminance_nw'] < 2.0)
    adequate_count = sum(1 for r in readings if r['luminance_nw'] >= 2.0)
    avg_lum = sum(r['luminance_nw'] for r in readings) / len(readings)

    overview = (
        f"Campus-wide nighttime lighting summary for University of Missouri:\n"
        f"Average campus luminance: {avg_lum:.2f} nW/cm2/sr "
        f"({'below' if avg_lum < 2.0 else 'meets'} 2.0 nW/cm2/sr safe pedestrian threshold). "
        f"Critically dark locations (<0.5 nW/cm2/sr): {dark_count} of {len(CAMPUS_LOCATIONS)} scanned. "
        f"Dim locations (0.5-2.0 nW/cm2/sr): {dim_count}. "
        f"Adequately lit locations (>2.0 nW/cm2/sr): {adequate_count}. "
        f"VIIRS (Visible Infrared Imaging Radiometer Suite) satellite nighttime lights data "
        f"from Earth Observation Group, Colorado School of Mines. "
        f"Annual VNL V2.2 composite, units: nW/cm2/sr (nanowatts per square centimeter per steradian). "
        f"Safe pedestrian minimum: 2.0 nW/cm2/sr (IESNA RP-33 standard). "
        f"Lighting gaps are primary CPTED risk factors — Welsh & Farrington (2008) found "
        f"20-39% crime reduction from improved street lighting."
    )
    chunks.append(_make_chunk(
        'viirs_campus_lighting_overview',
        overview,
        'viirs_annual_vnl_v2.2',
        {'type': 'campus_overview', 'avg_luminance': round(avg_lum, 2),
         'dark_count': dark_count, 'dim_count': dim_count}
    ))

    loader.close()
    print(f"  Generated {len(chunks)} VIIRS lighting chunks")
    return chunks


def _viirs_location_summary(name: str, lat: float, lon: float,
                              reading: Dict, summary: str) -> str:
    lum    = reading['luminance_nw']
    label  = reading['label']
    source = reading['source']
    below  = reading['below_threshold']

    cpted_note = ""
    if lum < 0.5:
        cpted_note = (
            "CRITICAL CPTED FINDING: This location is severely underlit. "
            "Satellite measurement confirms a major lighting gap. "
            "Immediate LED lighting installation is recommended. "
            "Research basis: Welsh & Farrington (2008) found 20-39% crime reduction "
            "from improved street lighting; NIJ (2019) found 45-65% reduction at campus pilot sites."
        )
    elif lum < 2.0:
        deficit = round((2.0 - lum) / 2.0 * 100)
        cpted_note = (
            f"CPTED FINDING: Lighting is {deficit}% below the 2.0 nW/cm2/sr safe pedestrian minimum. "
            "Lighting improvement is recommended as a CPTED intervention. "
        )
    else:
        cpted_note = "Lighting meets minimum safe pedestrian standard at this location. "

    return (
        f"Nighttime lighting assessment for {name} (MU Campus, Missouri):\n"
        f"VIIRS satellite luminance: {lum:.3f} nW/cm2/sr [{label}] "
        f"(data source: {source}). "
        f"Assessment: {summary} "
        f"{cpted_note}"
        f"Location coordinates: {lat:.4f}N, {abs(lon):.4f}W. "
        f"Safe pedestrian threshold: 2.0 nW/cm2/sr (IESNA RP-33). "
        f"Data: VIIRS Annual VNL V2.2, Earth Observation Group, Colorado School of Mines."
    )


# ── ROI / Research Summaries ──────────────────────────────────────────────────

def summarize_roi_research() -> List[Dict]:
    """
    Convert the ROI calculator's research citation database into
    RAG-indexable chunks so Agent 1 can answer questions about evidence.
    """
    chunks = []

    try:
        from src.roi_calculator import RESEARCH_CITATIONS, INTERVENTION_COSTS, COST_PER_INCIDENT
    except Exception as e:
        print(f"  ROI calculator unavailable: {e}")
        return []

    print("  Summarizing ROI research database...")

    # Per-category research chunks
    for category, citations in RESEARCH_CITATIONS.items():
        lines = [f"Research evidence for CPTED intervention category: {category}\n"]
        for cite in citations:
            low, high = cite['reduction_range']
            lines.append(
                f"Study: {cite['authors']} ({cite['year']}). "
                f"\"{cite['title']}\". {cite['journal']}. "
                f"Finding: {cite['finding']} "
                f"Reduction range: {low}-{high}% (median {cite['median_reduction']}%)."
            )
        lines.append(
            f"\nThese studies inform the MizzouSafe ROI calculator's "
            f"expected impact estimates for {category} interventions."
        )
        chunks.append(_make_chunk(
            f"research_evidence_{category}",
            "\n".join(lines),
            'roi_calculator_research_database',
            {'category': category, 'citation_count': len(citations)}
        ))

    # Intervention costs chunk
    cost_lines = ["CPTED intervention cost database for MU campus planning:\n"]
    for key, iv in INTERVENTION_COSTS.items():
        cost_lines.append(
            f"{iv['name']}: ${iv['unit_cost']:,} per {iv['unit']} installed. "
            f"Cost tier: {iv['cost_tier']}. "
            f"Lifespan: {iv['lifespan_years']} years. "
            f"Annual maintenance: ${iv['annual_maintenance']:,}."
        )
    cost_lines.append(
        "\nThese cost estimates are used by the ROI calculator to generate "
        "budget proposals for campus facilities management."
    )
    chunks.append(_make_chunk(
        'cpted_intervention_costs',
        "\n".join(cost_lines),
        'roi_calculator_cost_database',
        {'intervention_count': len(INTERVENTION_COSTS)}
    ))

    # Incident cost chunk
    inc_lines = [
        "Cost per campus incident benchmarks (for ROI calculation):\n",
        "These figures represent total incident costs: legal, medical, "
        "security response, and reputational impact.\n"
    ]
    for crime_type, cost in COST_PER_INCIDENT.items():
        inc_lines.append(f"{crime_type.title()}: ${cost:,} per incident")
    inc_lines.append(
        "\nSource: Federal campus crime cost estimates and national averages. "
        "Used by MizzouSafe to calculate annual savings from incident prevention."
    )
    chunks.append(_make_chunk(
        'campus_incident_cost_benchmarks',
        "\n".join(inc_lines),
        'roi_calculator_cost_database',
        {'type': 'incident_costs'}
    ))

    print(f"  Generated {len(chunks)} ROI/research chunks")
    return chunks


# ── Main runner ───────────────────────────────────────────────────────────────

class DataSummarizer:
    """
    Orchestrates all structured data summarization.
    Produces text chunks ready for embedding in the FAISS index.
    """

    def run(self, include_crime: bool = True,
            include_tiger: bool = True,
            include_viirs: bool = True,
            include_research: bool = True,
            include_survey: bool = True) -> List[Dict]:

        print("\n" + "=" * 55)
        print("  Data Summarizer — Converting Structured Data to Text")
        print("=" * 55)
        all_chunks = []

        if include_crime:
            print("\n[1/5] Crime Data...")
            all_chunks += summarize_crime_data()

        if include_tiger:
            print("\n[2/5] TIGER Road Network...")
            all_chunks += summarize_tiger_data()

        if include_viirs:
            print("\n[3/5] VIIRS Lighting Data...")
            all_chunks += summarize_viirs_data()

        if include_research:
            print("\n[4/5] ROI Research Database...")
            all_chunks += summarize_roi_research()

        if include_survey:
            print("\n[5/5] Student Survey Data...")
            all_chunks += summarize_survey_data()

        print(f"\n  Total data chunks generated: {len(all_chunks)}")
        return all_chunks

    def save_chunks(self, chunks: List[Dict], output_path: Path = None):
        """Append data chunks to the docstore JSONL file."""
        if not chunks:
            return

        out_path = output_path or DOCSTORE_PATH
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Read existing chunks to avoid duplicates by chunk_id
        existing_ids = set()
        if out_path.exists():
            with open(out_path, 'r') as f:
                for line in f:
                    try:
                        existing_ids.add(json.loads(line)['chunk_id'])
                    except Exception:
                        continue

        new_count = 0
        with open(out_path, 'a') as f:
            for chunk in chunks:
                if chunk['chunk_id'] not in existing_ids:
                    f.write(json.dumps(chunk) + '\n')
                    new_count += 1

        print(f"  Appended {new_count} new chunks to {out_path.name} "
              f"({len(chunks) - new_count} duplicates skipped)")
        return new_count


if __name__ == '__main__':
    summarizer = DataSummarizer()
    chunks = summarizer.run()
    summarizer.save_chunks(chunks)
    print(f"\nDone. Run python src/vector_index.py to rebuild the FAISS index.")

def summarize_survey_data() -> List[Dict]:
    """Load survey RAG chunks via SurveyAnalyzer."""
    try:
        from src.survey_analyzer import SurveyAnalyzer
        analyzer = SurveyAnalyzer()
        if not analyzer.load():
            return []
        return analyzer.generate_rag_chunks()
    except Exception as e:
        print(f"  Survey summarizer error: {e}")
        return []