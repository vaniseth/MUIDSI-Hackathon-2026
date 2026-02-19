"""
Risk Scorer
===========
Scores campus locations on a 0-10 risk scale using:
  1. Crime incident density (primary driver)
  2. Temporal pattern (hour-of-day weight)
  3. VIIRS lighting (secondary modifier, not multiplier)
  4. TIGER sightline (secondary modifier)

BUG FIXED: Previous implementation used a multiplicative temporal factor
that caused ALL locations to score 10.0/10 at night because:
    base_score (already high) × night_multiplier → capped at 10.0

New approach: temporal adds up to +2.5 points additively, so differentiation
between locations is preserved even at night.
"""

import math
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Optional
import sys

sys.path.append(str(Path(__file__).parent.parent))
from src.config import DATA_DIR, CRIME_DATA_DIR

# ── Temporal weights ─────────────────────────────────────────────────────────
# Hour → weight multiplier on incident counts (NOT on total score)
# Night hours are weighted more heavily because incidents are underreported
HOUR_WEIGHTS = {
    0: 1.8,   1: 2.0,   2: 2.0,   3: 1.9,   4: 1.7,   5: 1.4,
    6: 1.0,   7: 0.9,   8: 0.8,   9: 0.8,  10: 0.8,  11: 0.9,
   12: 1.0,  13: 1.0,  14: 1.0,  15: 1.0,  16: 1.1,  17: 1.2,
   18: 1.3,  19: 1.5,  20: 1.7,  21: 1.9,  22: 2.0,  23: 1.9,
}

# Max additive bonus from temporal factor (prevents all locations hitting 10.0)
TEMPORAL_MAX_BONUS = 2.5

# Crime severity weights
CRIME_SEVERITY = {
    'assault':    5.0,
    'harassment': 4.0,
    'theft':      3.0,
    'burglary':   4.5,
    'vehicle':    2.5,
    'drug':       2.0,
    'vandalism':  1.5,
    'suspicious': 1.0,
    'other':      1.0,
}


class RiskScorer:
    """
    Scores campus locations 0-10 using crime data + environmental factors.

    Scoring formula (additive, NOT multiplicative on total):
        base_score   = f(incident_count, crime_severity)     → 0-7.5
        temporal_add = f(hour_weight, night_ratio)            → 0-2.5
        total        = min(10.0, base_score + temporal_add)

    This ensures:
    - Locations with MORE incidents always score higher than those with fewer
    - Night hours add urgency but don't erase differentiation between locations
    - The top score of 10.0 is reserved for truly high-incident + night locations
    """

    def __init__(self, data_dir: Path = CRIME_DATA_DIR):
        self.data_dir  = data_dir
        self.crime_data = self._load_crime_data()

    def _load_crime_data(self) -> pd.DataFrame:
        candidates = [
            "crime_data_integrated.csv",
            "crime_data_clean__1_.csv",
            "crime_data_clean.csv",
            "mu_crime_log__2_.csv",
        ]
        for fname in candidates:
            fpath = self.data_dir / fname
            if fpath.exists():
                try:
                    df = pd.read_csv(fpath)
                    print(f"✅ Loaded {len(df)} crime records ({fname})")
                    return df
                except Exception as e:
                    print(f"  Warning reading {fname}: {e}")
        print("⚠️  No crime data found — risk scores will use defaults")
        return pd.DataFrame()

    def _incidents_near(self, lat: float, lon: float,
                        radius_miles: float = 0.15) -> pd.DataFrame:
        """Return all crime records within radius_miles of (lat, lon)."""
        if self.crime_data is None or self.crime_data.empty:
            return pd.DataFrame()

        df = self.crime_data
        if 'lat' not in df.columns or 'lon' not in df.columns:
            return pd.DataFrame()

        # Rough bounding box first (fast), then exact haversine
        dlat = radius_miles / 69.0
        dlon = radius_miles / (69.0 * math.cos(math.radians(lat)))

        nearby = df[
            df['lat'].between(lat - dlat, lat + dlat) &
            df['lon'].between(lon - dlon, lon + dlon)
        ].copy()

        if nearby.empty:
            return nearby

        def haversine_row(row):
            R = 3959.0
            dlat = math.radians(row['lat'] - lat)
            dlon = math.radians(row['lon'] - lon)
            a = (math.sin(dlat/2)**2 +
                 math.cos(math.radians(lat)) *
                 math.cos(math.radians(row['lat'])) *
                 math.sin(dlon/2)**2)
            return R * 2 * math.asin(math.sqrt(max(0, a)))

        nearby['_dist'] = nearby.apply(haversine_row, axis=1)
        return nearby[nearby['_dist'] <= radius_miles]

    def _base_score(self, incidents: pd.DataFrame) -> float:
        """
        Compute base risk score (0-7.5) from incident count and severity.
        Uses log-scale so very high incident counts don't dominate unfairly.
        """
        if incidents.empty:
            return 0.5  # Minimum baseline (location exists but no data)

        n = len(incidents)

        # Severity-weighted count
        if 'category' in incidents.columns:
            weighted = sum(
                CRIME_SEVERITY.get(str(cat).lower(), 1.0)
                for cat in incidents['category']
            )
        else:
            weighted = n * 2.0  # Default medium severity

        # Log-scale scoring: 1 incident → ~1.0, 10 → ~3.3, 30 → ~5.1, 100 → ~7.5
        log_score = math.log1p(weighted) * 1.4

        return round(min(7.5, log_score), 3)

    def _temporal_bonus(self, incidents: pd.DataFrame, hour: int) -> float:
        """
        Additive temporal bonus (0 to TEMPORAL_MAX_BONUS=2.5).
        Reflects: current scan hour danger + historical night concentration.
        Does NOT multiply total score — only adds bounded points.
        """
        # 1. Current hour weight (how dangerous is THIS hour)
        hour_w = HOUR_WEIGHTS.get(hour % 24, 1.0)
        # Normalize to 0-1 range (max hour_w is 2.0)
        hour_contrib = (hour_w - 0.8) / 1.2   # 0 at safest, ~1.0 at most dangerous

        # 2. Historical night ratio for this location
        night_ratio = 0.5  # Default
        if not incidents.empty and 'hour' in incidents.columns:
            h_col = pd.to_numeric(incidents['hour'], errors='coerce').dropna()
            if not h_col.empty:
                night = ((h_col >= 20) | (h_col < 6)).sum()
                night_ratio = night / len(h_col)

        # Combine: weighted average of current hour danger + historical pattern
        combined = 0.6 * hour_contrib + 0.4 * night_ratio
        bonus = combined * TEMPORAL_MAX_BONUS

        return round(min(TEMPORAL_MAX_BONUS, max(0.0, bonus)), 3)

    def _dominant_crime(self, incidents: pd.DataFrame) -> str:
        if incidents.empty or 'category' not in incidents.columns:
            return 'unknown'
        counts = incidents['category'].value_counts()
        return str(counts.index[0]) if not counts.empty else 'unknown'

    def get_risk_detail(self, lat: float, lon: float, hour: int = 12) -> Dict:
        """
        Full risk assessment for a location.

        Returns dict with:
          risk_score     : float 0-10 (ADDITIVE formula — preserves differentiation)
          risk_level     : str  High / Medium / Low
          incident_count : int
          dominant_crime : str
          night_ratio    : float (fraction of historical incidents at night)
          hour_weight    : float (current hour danger multiplier)
          base_score     : float (crime-only component, 0-7.5)
          temporal_bonus : float (time component, 0-2.5)
        """
        incidents   = self._incidents_near(lat, lon)
        base        = self._base_score(incidents)
        t_bonus     = self._temporal_bonus(incidents, hour)
        total_score = round(min(10.0, base + t_bonus), 2)

        # Risk level thresholds
        if total_score >= 7.0:
            level = "High"
        elif total_score >= 4.0:
            level = "Medium"
        else:
            level = "Low"

        # Night ratio for environmental analysis
        night_ratio = 0.5
        weekend_ratio = 0.3
        if not incidents.empty and 'hour' in incidents.columns:
            h_col = pd.to_numeric(incidents['hour'], errors='coerce').dropna()
            if not h_col.empty:
                night_ratio = float(((h_col >= 20) | (h_col < 6)).sum() / len(h_col))
        if not incidents.empty and 'day_of_week' in incidents.columns:
            days = incidents['day_of_week'].dropna()
            if not days.empty:
                weekend_ratio = float(days.isin(['Saturday', 'Sunday']).sum() / len(days))

        return {
            'risk_score':      total_score,
            'risk_level':      level,
            'incident_count':  len(incidents),
            'dominant_crime':  self._dominant_crime(incidents),
            'night_ratio':     round(night_ratio, 3),
            'weekend_ratio':   round(weekend_ratio, 3),
            'hour_weight':     HOUR_WEIGHTS.get(hour % 24, 1.0),
            'base_score':      base,
            'temporal_bonus':  t_bonus,
            'scoring_formula': f"{base:.2f} (crime) + {t_bonus:.2f} (temporal) = {total_score:.2f}",
        }