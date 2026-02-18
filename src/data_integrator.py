"""
Data Integrator - Combines Multiple Crime Data Sources:
  1. MU Campus Crime Log (crime_data_clean.csv / crime_data_clean__1_.csv)
  2. MU Crime Log v2     (mu_crime_log__2_.csv)
  3. Columbia PD Open Data (como_crime data if present)
  4. Como 911 Dispatch   (como_911_dispatch.csv) <-- NEW
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys
from datetime import datetime
from typing import List, Dict

sys.path.append(str(Path(__file__).parent.parent))
from src.config import CRIME_DATA_DIR


class DataIntegrator:
    """
    Integrates crime and dispatch data from multiple sources into a single
    clean dataset for use by RiskScorer and the CPTED analysis pipeline.
    """

    def __init__(self, data_dir: Path = CRIME_DATA_DIR):
        self.data_dir = data_dir
        self.mu_data         = None
        self.como_data       = None
        self.dispatch_data   = None
        self.integrated_data = None

    # ── Loaders ───────────────────────────────────────────────────────────────

    def load_mu_crime_data(self) -> pd.DataFrame:
        """
        Load MU campus crime log. Tries multiple known filenames.
        Source: https://muop-mupdreports.missouri.edu/dclog.php
        """
        candidates = [
            "crime_data_integrated.csv",   # pre-integrated (highest priority)
            "crime_data_clean__1_.csv",
            "crime_data_clean.csv",
            "mu_crime_log__2_.csv",
        ]
        for fname in candidates:
            fpath = self.data_dir / fname
            if fpath.exists():
                df = pd.read_csv(fpath)
                df['data_source'] = 'MU_Campus'
                print(f"  MU crime data: {len(df)} records ({fname})")
                if 'date' in df.columns:
                    print(f"    Date range: {df['date'].min()} to {df['date'].max()}")
                self.mu_data = df
                return df

        print("  MU crime data: not found")
        return pd.DataFrame()

    def load_como_pd_data(self, filename: str = None) -> pd.DataFrame:
        """
        Load Columbia PD crime data.
        Source: https://www.como.gov/police/data-reporting-forms/
        """
        candidates = [filename] if filename else []
        candidates += ["como_crime_data.csv", "columbia_pd_crimes.csv"]

        for fname in candidates:
            if not fname:
                continue
            fpath = self.data_dir / fname
            if fpath.exists():
                df = pd.read_csv(fpath)
                df = self._standardize_como_data(df)
                df['data_source'] = 'Como_PD'
                print(f"  Como PD data: {len(df)} records ({fname})")
                self.como_data = df
                return df

        print("  Como PD data: not found (optional)")
        return pd.DataFrame()

    def load_911_dispatch(self, filename: str = "como_911_dispatch.csv") -> pd.DataFrame:
        """
        Load Como 911 dispatch data. This is richer than crime logs:
        it includes all calls by time/location, enabling pattern analysis
        even for incidents that don't result in formal reports.

        Expected columns (auto-detected): lat, lon, hour/time, call_type/category,
        date, priority/severity
        """
        fpath = self.data_dir / filename
        if not fpath.exists():
            # Try alternate names
            for alt in ["911_dispatch.csv", "dispatch_data.csv"]:
                fpath = self.data_dir / alt
                if fpath.exists():
                    break
            else:
                print(f"  911 dispatch data: not found at {filename}")
                return pd.DataFrame()

        try:
            df = pd.read_csv(fpath)
            print(f"  911 dispatch raw: {len(df)} records | columns: {list(df.columns)}")
            df = self._standardize_dispatch_data(df)
            if df.empty:
                return pd.DataFrame()
            df['data_source'] = 'Como_911_Dispatch'
            print(f"  911 dispatch standardized: {len(df)} usable records")
            self.dispatch_data = df
            return df
        except Exception as e:
            print(f"  911 dispatch load error: {e}")
            return pd.DataFrame()

    def _standardize_dispatch_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize 911 dispatch data to match our crime schema.
        Handles various column naming conventions from Como.gov exports.
        """
        out = pd.DataFrame()

        # ── Coordinate detection ──────────────────────────────────────────────
        lat_candidates = ['lat', 'latitude', 'y', 'lat_dd', 'Lat', 'LAT']
        lon_candidates = ['lon', 'lng', 'longitude', 'x', 'lon_dd', 'long', 'Lon', 'LON']

        lat_col = next((c for c in lat_candidates if c in df.columns), None)
        lon_col = next((c for c in lon_candidates if c in df.columns), None)

        if lat_col and lon_col:
            out['lat'] = pd.to_numeric(df[lat_col], errors='coerce')
            out['lon'] = pd.to_numeric(df[lon_col], errors='coerce')
        else:
            # Try to find any numeric pair in campus range
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            lat_col_found = None
            lon_col_found = None
            for col in numeric_cols:
                sample = df[col].dropna()
                if sample.between(38.9, 39.0).mean() > 0.5:
                    lat_col_found = col
                elif sample.between(-92.4, -92.2).mean() > 0.5:
                    lon_col_found = col
            if lat_col_found and lon_col_found:
                out['lat'] = pd.to_numeric(df[lat_col_found], errors='coerce')
                out['lon'] = pd.to_numeric(df[lon_col_found], errors='coerce')
            else:
                print("    Could not identify lat/lon columns in dispatch data")
                return pd.DataFrame()

        # Filter to MU campus area
        mask = (
            out['lat'].between(38.92, 38.96) &
            out['lon'].between(-92.36, -92.30)
        )
        out = out[mask].copy()
        if out.empty:
            print("    No dispatch records within MU campus bounds")
            return pd.DataFrame()

        # ── Time / hour ───────────────────────────────────────────────────────
        hour_candidates = ['hour', 'Hour', 'HOUR', 'time_hour']
        time_candidates = ['time', 'Time', 'call_time', 'CallTime', 'dispatch_time',
                          'incident_time', 'reported_time']
        date_candidates = ['date', 'Date', 'DATE', 'incident_date', 'call_date']

        hour_col = next((c for c in hour_candidates if c in df.columns), None)
        time_col = next((c for c in time_candidates if c in df.columns), None)
        date_col = next((c for c in date_candidates if c in df.columns), None)

        if hour_col:
            out['hour'] = pd.to_numeric(df.loc[mask, hour_col], errors='coerce').fillna(12).astype(int)
        elif time_col:
            # Parse time string to hour
            def extract_hour(t):
                try:
                    t = str(t)
                    if ':' in t:
                        return int(t.split(':')[0]) % 24
                    return int(float(t)) % 24
                except Exception:
                    return 12
            out['hour'] = df.loc[mask, time_col].apply(extract_hour)
        else:
            out['hour'] = 12  # Default to noon if no time data

        if date_col:
            out['date'] = df.loc[mask, date_col].astype(str)
            # Try to extract day of week
            try:
                dates = pd.to_datetime(out['date'], errors='coerce')
                out['day_of_week'] = dates.dt.day_name()
            except Exception:
                pass

        # ── Category / call type ──────────────────────────────────────────────
        cat_candidates = ['call_type', 'CallType', 'call_nature', 'Nature',
                         'incident_type', 'category', 'Category', 'type',
                         'offense', 'Offense', 'problem', 'Problem']
        cat_col = next((c for c in cat_candidates if c in df.columns), None)

        if cat_col:
            out['offense'] = df.loc[mask, cat_col].astype(str)
            out['category'] = out['offense'].apply(self._categorize_dispatch_call)
        else:
            out['category'] = 'other'
            out['offense']  = 'unknown'

        # ── Severity ──────────────────────────────────────────────────────────
        sev_candidates = ['priority', 'Priority', 'severity', 'Severity']
        sev_col = next((c for c in sev_candidates if c in df.columns), None)

        if sev_col:
            out['severity'] = df.loc[mask, sev_col].apply(self._normalize_severity)
        else:
            # Assign severity by category
            sev_map = {'assault': 5, 'harassment': 4, 'theft': 3,
                       'vehicle': 3, 'vandalism': 2, 'drug': 2, 'other': 1}
            out['severity'] = out['category'].map(sev_map).fillna(1).astype(int)

        # ── Zone ─────────────────────────────────────────────────────────────
        out['zone'] = 'campus_dispatch'
        out = out.reset_index(drop=True)

        return out

    def _categorize_dispatch_call(self, call_type: str) -> str:
        if pd.isna(call_type):
            return 'other'
        t = str(call_type).lower()
        if any(w in t for w in ['assault', 'fight', 'battery', 'attack', 'agg']):
            return 'assault'
        elif any(w in t for w in ['theft', 'larceny', 'steal', 'rob', 'burglary', 'shopli']):
            return 'theft'
        elif any(w in t for w in ['harass', 'stalk', 'threaten', 'menace']):
            return 'harassment'
        elif any(w in t for w in ['vandal', 'damage', 'graffiti', 'destruct']):
            return 'vandalism'
        elif any(w in t for w in ['drug', 'narcotic', 'controlled', 'dui', 'dwi']):
            return 'drug'
        elif any(w in t for w in ['vehicle', 'auto', 'car', 'hit run', 'parking']):
            return 'vehicle'
        elif any(w in t for w in ['suspicious', 'welfare', 'disturbance', 'disorderly']):
            return 'suspicious'
        else:
            return 'other'

    def _normalize_severity(self, val) -> int:
        """Normalize priority/severity to 1-5 scale."""
        try:
            v = str(val).lower()
            if v in ['1', 'high', 'critical', 'emergency', 'urgent', 'priority 1']:
                return 5
            elif v in ['2', 'medium-high', 'priority 2']:
                return 4
            elif v in ['3', 'medium', 'priority 3']:
                return 3
            elif v in ['4', 'low-medium', 'priority 4']:
                return 2
            else:
                return 1
        except Exception:
            return 1

    def _standardize_como_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize Como.gov crime data to match MU schema."""
        standardized = pd.DataFrame()
        field_mapping = {
            'Date': 'date', 'Time': 'hour', 'Address': 'location',
            'Offense': 'offense', 'OffenseType': 'category',
            'Latitude': 'lat', 'Longitude': 'lon'
        }
        for como_field, our_field in field_mapping.items():
            if como_field in df.columns:
                standardized[our_field] = df[como_field]
        if 'offense' in standardized.columns and 'category' not in standardized.columns:
            standardized['category'] = standardized['offense'].apply(
                self._categorize_dispatch_call
            )
        if 'severity' not in standardized.columns and 'category' in standardized.columns:
            sev_map = {'assault': 5, 'burglary': 4, 'theft': 2,
                       'vandalism': 1, 'drug': 2, 'vehicle': 4,
                       'harassment': 3, 'other': 1}
            standardized['severity'] = standardized['category'].map(sev_map).fillna(1)
        if 'zone' not in standardized.columns:
            standardized['zone'] = 'city_columbia'
        return standardized

    # ── Integration ───────────────────────────────────────────────────────────

    def integrate_data(self) -> pd.DataFrame:
        print("\nIntegrating crime data from all sources...\n")

        if self.mu_data is None:
            self.load_mu_crime_data()
        if self.como_data is None:
            self.load_como_pd_data()
        if self.dispatch_data is None:
            self.load_911_dispatch()

        frames = []
        for name, df in [('MU', self.mu_data), ('Como PD', self.como_data),
                          ('911 Dispatch', self.dispatch_data)]:
            if df is not None and not df.empty:
                frames.append(df)
                print(f"  + {name}: {len(df)} records")

        if not frames:
            print("No crime data loaded.")
            return pd.DataFrame()

        integrated = pd.concat(frames, ignore_index=True)

        if 'date' in integrated.columns:
            integrated = integrated.sort_values('date').reset_index(drop=True)

        # Deduplicate on location + date + offense
        dedup_cols = [c for c in ['location', 'lat', 'lon', 'date', 'offense']
                      if c in integrated.columns]
        if len(dedup_cols) >= 3:
            before = len(integrated)
            integrated = integrated.drop_duplicates(subset=dedup_cols)
            removed = before - len(integrated)
            if removed:
                print(f"  Removed {removed} duplicate records")

        print(f"\nTotal integrated: {len(integrated)} records")
        self.integrated_data = integrated
        return integrated

    def save_integrated_data(self, filename: str = "crime_data_integrated.csv"):
        if self.integrated_data is None or self.integrated_data.empty:
            print("No integrated data to save")
            return
        fpath = self.data_dir / filename
        self.integrated_data.to_csv(fpath, index=False)
        print(f"Saved: {fpath} ({len(self.integrated_data)} records)")

    def get_data_summary(self) -> Dict:
        if self.integrated_data is None or self.integrated_data.empty:
            return {}
        df = self.integrated_data
        return {
            'total_records': len(df),
            'date_range': {
                'start': df['date'].min() if 'date' in df.columns else None,
                'end':   df['date'].max() if 'date' in df.columns else None,
            },
            'sources':    df['data_source'].value_counts().to_dict()
                          if 'data_source' in df.columns else {},
            'categories': df['category'].value_counts().to_dict()
                          if 'category' in df.columns else {},
            'zones':      df['zone'].value_counts().to_dict()
                          if 'zone' in df.columns else {},
        }


def main():
    print("=" * 60)
    print("MIZZOU CRIME DATA INTEGRATOR")
    print("=" * 60 + "\n")

    integrator = DataIntegrator()
    integrator.load_mu_crime_data()
    integrator.load_como_pd_data()
    integrator.load_911_dispatch()

    integrated = integrator.integrate_data()
    if not integrated.empty:
        integrator.save_integrated_data()
        summary = integrator.get_data_summary()
        print("\nDATA SUMMARY:")
        print(f"  Total:      {summary['total_records']}")
        print(f"  By Source:")
        for src, cnt in summary.get('sources', {}).items():
            print(f"    {src}: {cnt}")
        print(f"  By Category:")
        for cat, cnt in list(summary.get('categories', {}).items())[:8]:
            print(f"    {cat}: {cnt}")


if __name__ == "__main__":
    main()