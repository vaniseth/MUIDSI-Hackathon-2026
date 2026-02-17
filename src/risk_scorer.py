"""
Risk Scorer - Analyzes crime data to score location safety
"""
"""
Risk Scorer - Feature 1: Richer incident breakdown
Returns category breakdown, time patterns, and dominant crime types
not just a raw weighted number.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from collections import Counter
from typing import Dict, List, Tuple
import sys
from math import radians, sin, cos, sqrt, atan2

sys.path.append(str(Path(__file__).parent.parent))
from src.config import (CRIME_DATA_PATH, RISK_RADIUS_MILES,
                        HIGH_RISK_THRESHOLD, MEDIUM_RISK_THRESHOLD)


class RiskScorer:
    def __init__(self, crime_data_path: Path = CRIME_DATA_PATH):
        self.crime_data_path = crime_data_path
        self.crime_data = None
        self.load_crime_data()

    def load_crime_data(self):
        integrated_path = self.crime_data_path.parent / "crime_data_integrated.csv"
        if integrated_path.exists():
            self.crime_data = pd.read_csv(integrated_path)
            sources = ""
            if 'data_source' in self.crime_data.columns:
                s = self.crime_data['data_source'].value_counts()
                sources = " (" + ", ".join(f"{k}: {v}" for k, v in s.items()) + ")"
            print(f"✅ Loaded {len(self.crime_data)} crime records (MU + Como){sources}")
            return

        if not self.crime_data_path.exists():
            print(f"⚠️  Crime data not found. Using empty dataset.")
            self.crime_data = pd.DataFrame()
            return

        self.crime_data = pd.read_csv(self.crime_data_path)
        print(f"✅ Loaded {len(self.crime_data)} crime records (MU only)")

    def haversine_distance(self, lat1, lon1, lat2, lon2) -> float:
        R = 3959
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        return R * 2 * atan2(sqrt(a), sqrt(1 - a))

    def get_nearby_incidents(self, lat: float, lon: float,
                              radius: float = RISK_RADIUS_MILES) -> pd.DataFrame:
        """Return all incidents within radius of a point."""
        if self.crime_data is None or self.crime_data.empty:
            return pd.DataFrame()

        rows = []
        for _, crime in self.crime_data.iterrows():
            dist = self.haversine_distance(lat, lon, crime['lat'], crime['lon'])
            if dist <= radius:
                rows.append({**crime.to_dict(), 'distance_miles': dist})
        return pd.DataFrame(rows)

    def get_risk_score(self, lat: float, lon: float, hour: int,
                       radius: float = RISK_RADIUS_MILES) -> Tuple[str, float, int]:
        """
        Original interface preserved for backwards compatibility.
        Returns (risk_level, risk_score, incident_count)
        """
        detail = self.get_risk_detail(lat, lon, hour, radius)
        return detail['risk_level'], detail['risk_score'], detail['incident_count']

    def get_risk_detail(self, lat: float, lon: float, hour: int,
                        radius: float = RISK_RADIUS_MILES) -> Dict:
        """
        Feature 1: Full incident breakdown.
        Returns rich dict with category breakdown, patterns, dominant types.
        """
        nearby = self.get_nearby_incidents(lat, lon, radius)

        if nearby.empty:
            return {
                'risk_level': 'Low', 'risk_score': 0.0, 'incident_count': 0,
                'category_breakdown': {}, 'dominant_crime': None,
                'night_ratio': 0.0, 'weekend_ratio': 0.0,
                'peak_hour': None, 'pattern_summary': 'No recorded incidents in this area.',
                'same_hour_incidents': 0, 'severity_breakdown': {}
            }

        # ── Weighted risk score ─────────────────────────────────────────────
        total_weight = 0.0
        for _, crime in nearby.iterrows():
            time_diff = min(abs(crime['hour'] - hour), 24 - abs(crime['hour'] - hour))
            time_weight = 1.0 if time_diff <= 1 else 0.5 if time_diff <= 3 else 0.2
            dist_weight = max(0, 1 - (crime['distance_miles'] / radius))
            sev = crime.get('severity', 1)
            total_weight += sev * time_weight * dist_weight

        risk_score = round(min(10, total_weight), 2)
        risk_level = ('High' if risk_score >= HIGH_RISK_THRESHOLD
                      else 'Medium' if risk_score >= MEDIUM_RISK_THRESHOLD
                      else 'Low')

        # ── Category breakdown ──────────────────────────────────────────────
        cat_counts = {}
        if 'category' in nearby.columns:
            cat_counts = nearby['category'].value_counts().to_dict()

        dominant_crime = max(cat_counts, key=cat_counts.get) if cat_counts else None

        # ── Severity breakdown ──────────────────────────────────────────────
        sev_labels = {1: 'minor', 2: 'low', 3: 'moderate', 4: 'serious', 5: 'critical'}
        sev_breakdown = {}
        if 'severity' in nearby.columns:
            for sev_val, count in nearby['severity'].value_counts().items():
                sev_breakdown[sev_labels.get(int(sev_val), str(sev_val))] = int(count)

        # ── Time patterns ───────────────────────────────────────────────────
        night_hours = set(range(20, 24)) | set(range(0, 6))
        night_ratio = 0.0
        weekend_ratio = 0.0
        peak_hour = None

        if 'hour' in nearby.columns:
            night_count = nearby['hour'].apply(lambda h: h in night_hours).sum()
            night_ratio = round(night_count / len(nearby), 2)
            peak_hour = int(nearby['hour'].mode()[0]) if not nearby['hour'].empty else None

        if 'day_of_week' in nearby.columns:
            weekend_days = ['Saturday', 'Sunday', 'Friday']
            weekend_count = nearby['day_of_week'].apply(
                lambda d: str(d) in weekend_days
            ).sum()
            weekend_ratio = round(weekend_count / len(nearby), 2)

        same_hour = nearby[nearby['hour'].apply(
            lambda h: abs(h - hour) <= 1 or abs(h - hour) >= 23
        )] if 'hour' in nearby.columns else pd.DataFrame()

        # ── Natural language pattern summary ────────────────────────────────
        pattern_summary = self._build_pattern_summary(
            len(nearby), cat_counts, dominant_crime,
            night_ratio, weekend_ratio, peak_hour, sev_breakdown
        )

        return {
            'risk_level':         risk_level,
            'risk_score':         risk_score,
            'incident_count':     len(nearby),
            'same_hour_incidents': len(same_hour),
            'category_breakdown': cat_counts,
            'dominant_crime':     dominant_crime,
            'severity_breakdown': sev_breakdown,
            'night_ratio':        night_ratio,
            'weekend_ratio':      weekend_ratio,
            'peak_hour':          peak_hour,
            'pattern_summary':    pattern_summary,
        }

    def _build_pattern_summary(self, total, cat_counts, dominant,
                                night_ratio, weekend_ratio, peak_hour,
                                sev_breakdown) -> str:
        """Build a one-paragraph plain English summary of incident patterns."""
        if total == 0:
            return "No recorded incidents in this area."

        parts = [f"{total} incident{'s' if total > 1 else ''} recorded nearby."]

        if dominant and cat_counts:
            top_count = cat_counts[dominant]
            pct = round(top_count / total * 100)
            parts.append(f"Predominantly {dominant} ({pct}% of incidents).")

        if night_ratio >= 0.6:
            parts.append("Most incidents occur at night.")
        elif night_ratio >= 0.4:
            parts.append("Incidents split between day and night.")
        else:
            parts.append("Most incidents occur during the day.")

        if weekend_ratio >= 0.5:
            parts.append("Higher activity on weekends/Fridays.")

        if peak_hour is not None:
            period = "midnight–6am" if peak_hour < 6 else (
                "morning" if peak_hour < 12 else (
                "afternoon" if peak_hour < 17 else (
                "evening" if peak_hour < 20 else "late night")))
            parts.append(f"Peak activity: {period} (around {peak_hour:02d}:00).")

        critical = sev_breakdown.get('critical', 0) + sev_breakdown.get('serious', 0)
        if critical > 0:
            parts.append(f"{critical} serious/critical incident(s) in this area.")

        return " ".join(parts)

    def get_zone_stats(self, zone: str) -> Dict:
        if self.crime_data is None or self.crime_data.empty:
            return {"total_crimes": 0, "categories": {}}
        zone_data = self.crime_data[self.crime_data['zone'] == zone]
        if zone_data.empty:
            return {"total_crimes": 0, "categories": {}}
        return {
            "total_crimes": len(zone_data),
            "categories": zone_data['category'].value_counts().to_dict(),
            "avg_severity": round(zone_data['severity'].mean(), 2)
        }