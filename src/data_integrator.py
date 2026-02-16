"""
Data Integrator - Combines Multiple Crime Data Sources
- MU Crime Log (from muop-mupdreports.missouri.edu)
- Columbia PD Data (from como.gov)
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys
from datetime import datetime
import requests
from typing import List, Dict

sys.path.append(str(Path(__file__).parent.parent))
from src.config import CRIME_DATA_DIR


class DataIntegrator:
    """
    Integrates crime data from multiple sources:
    1. MU Campus Crime Log
    2. Columbia Police Department Open Data
    """
    
    def __init__(self, data_dir: Path = CRIME_DATA_DIR):
        self.data_dir = data_dir
        self.mu_data = None
        self.como_data = None
        self.integrated_data = None
    
    def load_mu_crime_data(self, filename: str = "crime_data_clean__1_.csv") -> pd.DataFrame:
        """
        Load MU campus crime data
        
        Source: https://muop-mupdreports.missouri.edu/dclog.php
        """
        filepath = self.data_dir / filename
        
        if not filepath.exists():
            print(f"⚠️  MU crime data not found: {filepath}")
            return pd.DataFrame()
        
        df = pd.read_csv(filepath)
        
        # Add source marker
        df['data_source'] = 'MU_Campus'
        
        print(f"✅ Loaded {len(df)} MU campus crime records")
        print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
        
        self.mu_data = df
        return df
    
    def load_como_pd_data(self, filename: str = None) -> pd.DataFrame:
        """
        Load Columbia PD crime data
        
        Source: https://www.como.gov/police/data-reporting-forms/
        
        Available datasets:
        - Crime Statistics (annual reports)
        - Use of Force Reports
        - Traffic Stop Data
        - Part 1 Crime Data (serious crimes)
        """
        if filename and (self.data_dir / filename).exists():
            filepath = self.data_dir / filename
            df = pd.read_csv(filepath)
            
            # Standardize Como.gov data to match our schema
            df = self._standardize_como_data(df)
            df['data_source'] = 'Como_PD'
            
            print(f"✅ Loaded {len(df)} Como PD crime records")
            
            self.como_data = df
            return df
        else:
            print("ℹ️  No Como PD data file provided")
            print("   Download from: https://www.como.gov/police/data-reporting-forms/")
            return pd.DataFrame()
    
    def _standardize_como_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize Como.gov data to match MU schema
        
        Expected Como.gov fields (may vary):
        - Date/Time
        - Location/Address
        - Offense/Crime Type
        - Latitude/Longitude (may need geocoding)
        """
        standardized = pd.DataFrame()
        
        # Try to map common field names
        # Note: Actual Como.gov field names may differ - adjust as needed
        field_mapping = {
            # Como.gov field → Our standard field
            'Date': 'date',
            'Time': 'hour',
            'Address': 'location',
            'Offense': 'offense',
            'OffenseType': 'category',
            'Latitude': 'lat',
            'Longitude': 'lon'
        }
        
        for como_field, our_field in field_mapping.items():
            if como_field in df.columns:
                standardized[our_field] = df[como_field]
        
        # Categorize crimes if needed
        if 'offense' in standardized.columns and 'category' not in standardized.columns:
            standardized['category'] = standardized['offense'].apply(self._categorize_crime)
        
        # Add severity if not present
        if 'severity' not in standardized.columns and 'category' in standardized.columns:
            severity_map = {
                'assault': 5, 'burglary': 4, 'theft': 2,
                'vandalism': 1, 'drug': 2, 'vehicle': 4,
                'harassment': 3, 'other': 1
            }
            standardized['severity'] = standardized['category'].map(severity_map).fillna(1)
        
        # Add zone - classify as "city" for non-campus data
        if 'zone' not in standardized.columns:
            standardized['zone'] = 'city_columbia'
        
        return standardized
    
    def _categorize_crime(self, offense: str) -> str:
        """Categorize crime type"""
        if pd.isna(offense):
            return 'other'
        
        offense_lower = str(offense).lower()
        
        if any(word in offense_lower for word in ['assault', 'attack', 'battery']):
            return 'assault'
        elif any(word in offense_lower for word in ['theft', 'larceny', 'steal', 'robbery']):
            return 'theft'
        elif any(word in offense_lower for word in ['burglary', 'breaking', 'enter']):
            return 'burglary'
        elif any(word in offense_lower for word in ['harassment', 'stalking']):
            return 'harassment'
        elif any(word in offense_lower for word in ['vandalism', 'damage', 'graffiti']):
            return 'vandalism'
        elif any(word in offense_lower for word in ['drug', 'narcotic', 'controlled']):
            return 'drug'
        elif any(word in offense_lower for word in ['vehicle', 'auto', 'motor']):
            return 'vehicle'
        else:
            return 'other'
    
    def integrate_data(self) -> pd.DataFrame:
        """
        Combine MU and Como.gov data into single dataset
        
        Returns:
            Integrated DataFrame with all crime data
        """
        print("\n🔄 Integrating crime data from multiple sources...\n")
        
        # Load MU data if not already loaded
        if self.mu_data is None:
            self.load_mu_crime_data()
        
        # Load Como data if not already loaded  
        if self.como_data is None:
            self.load_como_pd_data()
        
        # Combine datasets
        if self.mu_data is not None and not self.mu_data.empty:
            if self.como_data is not None and not self.como_data.empty:
                # Both datasets available
                integrated = pd.concat([self.mu_data, self.como_data], ignore_index=True)
                print(f"✅ Integrated {len(self.mu_data)} MU + {len(self.como_data)} Como = {len(integrated)} total records")
            else:
                # Only MU data
                integrated = self.mu_data.copy()
                print(f"ℹ️  Using MU data only: {len(integrated)} records")
        elif self.como_data is not None and not self.como_data.empty:
            # Only Como data
            integrated = self.como_data.copy()
            print(f"ℹ️  Using Como PD data only: {len(integrated)} records")
        else:
            # No data
            print("❌ No crime data loaded!")
            return pd.DataFrame()
        
        # Sort by date
        if 'date' in integrated.columns:
            integrated = integrated.sort_values('date').reset_index(drop=True)
        
        # Remove duplicates (same location, date, offense)
        if all(col in integrated.columns for col in ['location', 'date', 'offense']):
            before = len(integrated)
            integrated = integrated.drop_duplicates(subset=['location', 'date', 'offense'])
            removed = before - len(integrated)
            if removed > 0:
                print(f"🗑️  Removed {removed} duplicate records")
        
        self.integrated_data = integrated
        return integrated
    
    def save_integrated_data(self, filename: str = "crime_data_integrated.csv"):
        """Save integrated dataset"""
        if self.integrated_data is None or self.integrated_data.empty:
            print("⚠️  No integrated data to save")
            return
        
        filepath = self.data_dir / filename
        self.integrated_data.to_csv(filepath, index=False)
        print(f"💾 Saved integrated dataset: {filepath}")
        print(f"   Total records: {len(self.integrated_data)}")
    
    def get_data_summary(self) -> Dict:
        """Get summary statistics of integrated data"""
        if self.integrated_data is None or self.integrated_data.empty:
            return {}
        
        df = self.integrated_data
        
        summary = {
            'total_records': len(df),
            'date_range': {
                'start': df['date'].min() if 'date' in df.columns else None,
                'end': df['date'].max() if 'date' in df.columns else None
            },
            'sources': df['data_source'].value_counts().to_dict() if 'data_source' in df.columns else {},
            'categories': df['category'].value_counts().to_dict() if 'category' in df.columns else {},
            'zones': df['zone'].value_counts().to_dict() if 'zone' in df.columns else {},
            'geocoded_percentage': (df[['lat', 'lon']].notna().all(axis=1).sum() / len(df) * 100) if all(col in df.columns for col in ['lat', 'lon']) else 0
        }
        
        return summary
    
    def download_como_data(self, url: str = None) -> bool:
        """
        Helper to download Como.gov data
        
        Note: Como.gov provides various datasets. You may need to:
        1. Visit https://www.como.gov/police/data-reporting-forms/
        2. Download CSV files manually
        3. Place in data/crime_data/ directory
        
        Or use their API if available.
        """
        print("📥 Como.gov Data Download Instructions:")
        print("   1. Visit: https://www.como.gov/police/data-reporting-forms/")
        print("   2. Download crime data CSV files")
        print("   3. Save to: data/crime_data/")
        print("   4. Run: integrator.load_como_pd_data('your_file.csv')")
        
        # If they have an API endpoint, implement here:
        # if url:
        #     response = requests.get(url)
        #     ...
        
        return False


def main():
    """Example usage"""
    print("="*70)
    print("MIZZOU CRIME DATA INTEGRATOR")
    print("="*70 + "\n")
    
    integrator = DataIntegrator()
    
    # Load MU data
    integrator.load_mu_crime_data()
    
    # Try to load Como data (if file exists)
    # integrator.load_como_pd_data("como_crime_data.csv")
    
    # Integrate
    integrated = integrator.integrate_data()
    
    # Save
    if not integrated.empty:
        integrator.save_integrated_data()
        
        # Show summary
        summary = integrator.get_data_summary()
        print("\n📊 DATA SUMMARY:")
        print(f"   Total Records: {summary['total_records']}")
        print(f"   Date Range: {summary['date_range']['start']} to {summary['date_range']['end']}")
        print(f"\n   By Source:")
        for source, count in summary['sources'].items():
            print(f"      {source}: {count}")
        print(f"\n   By Category:")
        for cat, count in list(summary['categories'].items())[:5]:
            print(f"      {cat}: {count}")
        print(f"\n   Geocoded: {summary['geocoded_percentage']:.1f}%")


if __name__ == "__main__":
    main()
