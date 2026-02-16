"""
Risk Scorer - Analyzes crime data to score location safety
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys
from math import radians, sin, cos, sqrt, atan2

sys.path.append(str(Path(__file__).parent.parent))
from src.config import CRIME_DATA_PATH, RISK_RADIUS_MILES, HIGH_RISK_THRESHOLD, MEDIUM_RISK_THRESHOLD


class RiskScorer:
    """
    Calculates risk scores based on historical crime data
    """
    
    def __init__(self, crime_data_path: Path = CRIME_DATA_PATH):
        self.crime_data_path = crime_data_path
        self.crime_data = None
        self.load_crime_data()
    
    def load_crime_data(self):
        """Load and prepare crime data"""
        # Try integrated data first
        integrated_path = self.crime_data_path.parent / "crime_data_integrated.csv"
        
        if integrated_path.exists():
            print(f"✅ Loading integrated crime data (MU + Como.gov)")
            self.crime_data = pd.read_csv(integrated_path)
            print(f"   Loaded {len(self.crime_data)} crime records from multiple sources")
            
            # Show breakdown by source if available
            if 'data_source' in self.crime_data.columns:
                sources = self.crime_data['data_source'].value_counts()
                for source, count in sources.items():
                    print(f"   - {source}: {count} records")
            return
        
        # Fall back to MU data only
        if not self.crime_data_path.exists():
            print(f"⚠️  Crime data not found: {self.crime_data_path}")
            print("Using empty dataset")
            self.crime_data = pd.DataFrame()
            return
        
        self.crime_data = pd.read_csv(self.crime_data_path)
        print(f"✅ Loaded {len(self.crime_data)} crime records (MU only)")
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points in miles
        """
        R = 3959  # Earth radius in miles
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    def get_risk_score(self, lat: float, lon: float, hour: int, radius: float = RISK_RADIUS_MILES) -> tuple:
        """
        Calculate risk score for a location at a specific time
        
        Returns:
            (risk_level, risk_score, incident_count)
        """
        if self.crime_data.empty:
            return "Low", 0.0, 0
        
        # Find nearby crimes
        nearby_crimes = []
        for idx, crime in self.crime_data.iterrows():
            distance = self.haversine_distance(lat, lon, crime['lat'], crime['lon'])
            if distance <= radius:
                # Time-based weight (same hour = higher weight)
                time_diff = min(abs(crime['hour'] - hour), 24 - abs(crime['hour'] - hour))
                time_weight = 1.0 if time_diff <= 1 else 0.5 if time_diff <= 3 else 0.2
                
                nearby_crimes.append({
                    'distance': distance,
                    'severity': crime['severity'],
                    'time_weight': time_weight
                })
        
        if not nearby_crimes:
            return "Low", 0.0, 0
        
        # Calculate weighted risk score
        total_weight = 0
        for crime in nearby_crimes:
            # Distance weight (closer = higher weight)
            distance_weight = max(0, 1 - (crime['distance'] / radius))
            weight = crime['severity'] * crime['time_weight'] * distance_weight
            total_weight += weight
        
        risk_score = min(10, total_weight)
        incident_count = len(nearby_crimes)
        
        # Determine risk level
        if risk_score >= HIGH_RISK_THRESHOLD:
            risk_level = "High"
        elif risk_score >= MEDIUM_RISK_THRESHOLD:
            risk_level = "Medium"
        else:
            risk_level = "Low"
        
        return risk_level, round(risk_score, 2), incident_count
    
    def get_zone_stats(self, zone: str) -> Dict:
        """Get crime statistics for a zone"""
        if self.crime_data.empty:
            return {"total_crimes": 0, "categories": {}}
        
        zone_data = self.crime_data[self.crime_data['zone'] == zone]
        
        if zone_data.empty:
            return {"total_crimes": 0, "categories": {}}
        
        return {
            "total_crimes": len(zone_data),
            "categories": zone_data['category'].value_counts().to_dict(),
            "avg_severity": zone_data['severity'].mean()
        }
