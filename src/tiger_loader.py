"""
TIGER/Line Road Loader
======================
Loads Boone County road shapefile (tl_2025_29019_roads.shp) and provides:
  - Road classification for each campus location (major/minor/pedestrian/parking)
  - Sightline analysis based on road width and surrounding street network
  - Natural surveillance score derived from road type and connectivity

Data: US Census TIGER/Line 2025, Boone County MO (FIPS 29019)
Place files in: data/tiger/

MTFCC Road Classification Codes (relevant ones):
  S1100 - Primary Road (highway)
  S1200 - Secondary Road (major street)
  S1400 - Local Neighborhood Road
  S1500 - Vehicular Trail
  S1630 - Ramp
  S1640 - Service Drive
  S1710 - Walkway/Pedestrian Trail
  S1720 - Stairway
  S1730 - Alley
  S1740 - Private Road
  S1750 - Internal US Census Bureau Use
  S1780 - Parking Lot Road
  S1820 - Bike Path or Trail
  S1830 - Bridle Path
"""

import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys

sys.path.append(str(Path(__file__).parent.parent))
from src.config import DATA_DIR

TIGER_DIR = DATA_DIR / "tiger"

# MU Campus bounding box
CAMPUS_BOUNDS = {
    'lat_min': 38.925, 'lat_max': 38.960,
    'lon_min': -92.365, 'lon_max': -92.295,
}

# MTFCC code → human label + surveillance score (0-10)
ROAD_CLASSIFICATIONS = {
    'S1100': {'label': 'Primary Road',          'surveillance': 9, 'width_ft': 80},
    'S1200': {'label': 'Secondary Road',         'surveillance': 8, 'width_ft': 60},
    'S1400': {'label': 'Local Road',             'surveillance': 6, 'width_ft': 30},
    'S1500': {'label': 'Vehicular Trail',        'surveillance': 3, 'width_ft': 15},
    'S1630': {'label': 'Ramp',                   'surveillance': 4, 'width_ft': 25},
    'S1640': {'label': 'Service Drive',          'surveillance': 3, 'width_ft': 20},
    'S1710': {'label': 'Pedestrian Walkway',     'surveillance': 5, 'width_ft': 10},
    'S1720': {'label': 'Stairway',               'surveillance': 2, 'width_ft': 6},
    'S1730': {'label': 'Alley',                  'surveillance': 2, 'width_ft': 12},
    'S1740': {'label': 'Private Road',           'surveillance': 3, 'width_ft': 20},
    'S1780': {'label': 'Parking Lot Road',       'surveillance': 3, 'width_ft': 25},
    'S1820': {'label': 'Bike Path',              'surveillance': 4, 'width_ft': 8},
    'S1830': {'label': 'Bridle Path',            'surveillance': 2, 'width_ft': 8},
}

DEFAULT_ROAD = {'label': 'Unknown Road', 'surveillance': 4, 'width_ft': 20}


def _haversine(lat1, lon1, lat2, lon2) -> float:
    R = 3959
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    return R * 2 * math.asin(math.sqrt(a))


class TIGERLoader:
    """
    Loads Boone County road network data from TIGER/Line shapefile.
    Provides road classification and sightline analysis for CPTED.

    Falls back to basic classification if geopandas not installed or
    shapefile not found — system still works at demo time.
    """

    def __init__(self, tiger_dir: Path = TIGER_DIR):
        self.tiger_dir = tiger_dir
        self.roads_gdf = None
        self.campus_roads = None
        self.has_real_data = False
        self._try_load()

    def _try_load(self):
        """Attempt to load the TIGER shapefile."""
        shp_files = list(self.tiger_dir.glob("*.shp")) if self.tiger_dir.exists() else []

        if not shp_files:
            print("🗺️  TIGER: No shapefile found — using road type estimates")
            print(f"   Place tl_2025_29019_roads.shp in {self.tiger_dir}")
            return

        try:
            import geopandas as gpd
            shp_path = shp_files[0]
            print(f"🗺️  TIGER: Loading {shp_path.name}...")

            gdf = gpd.read_file(str(shp_path))
            print(f"   Total roads in Boone County: {len(gdf)}")

            # Filter to MU campus area
            bounds = CAMPUS_BOUNDS
            campus = gdf.cx[
                bounds['lon_min']:bounds['lon_max'],
                bounds['lat_min']:bounds['lat_max']
            ]
            self.roads_gdf   = gdf
            self.campus_roads = campus
            self.has_real_data = True
            print(f"   Campus roads: {len(campus)} segments")
            print(f"   Road types: {campus['MTFCC'].value_counts().head(5).to_dict()}")

        except ImportError:
            print("🗺️  TIGER: geopandas not installed — using road type estimates")
            print("   Install: pip install geopandas --break-system-packages")
        except Exception as e:
            print(f"🗺️  TIGER: Load error — {e}")

    def get_roads_near(self, lat: float, lon: float,
                       radius_ft: float = 300) -> List[Dict]:
        """
        Get all road segments within radius_ft of a coordinate.
        Returns list of road dicts with name, type, classification, surveillance score.
        """
        if not self.has_real_data or self.campus_roads is None:
            return self._estimate_roads(lat, lon)

        try:
            import geopandas as gpd
            from shapely.geometry import Point

            radius_deg = (radius_ft / 5280) / 69  # approx degrees
            point = Point(lon, lat)
            buffer = point.buffer(radius_deg)

            nearby = self.campus_roads[self.campus_roads.intersects(buffer)]

            roads = []
            for _, row in nearby.iterrows():
                mtfcc = str(row.get('MTFCC', ''))
                cls   = ROAD_CLASSIFICATIONS.get(mtfcc, DEFAULT_ROAD)
                roads.append({
                    'name':        str(row.get('FULLNAME', 'Unnamed')),
                    'mtfcc':       mtfcc,
                    'type_label':  cls['label'],
                    'surveillance_score': cls['surveillance'],
                    'width_ft':    cls['width_ft'],
                })
            return roads

        except Exception as e:
            return self._estimate_roads(lat, lon)

    def _estimate_roads(self, lat: float, lon: float) -> List[Dict]:
        """
        Estimate road context from known MU campus geography.
        Used when TIGER data is unavailable.
        """
        # Core campus — well-connected secondary roads
        core_locs = [
            (38.9404, -92.3277), (38.9441, -92.3269),
            (38.9423, -92.3268), (38.9415, -92.3280),
        ]
        for clat, clon in core_locs:
            if _haversine(lat, lon, clat, clon) < 0.1:
                return [{'name': 'Campus Road', 'mtfcc': 'S1400',
                         'type_label': 'Local Road', 'surveillance_score': 7,
                         'width_ft': 30}]

        # Parking areas
        parking_locs = [(38.9450, -92.3240), (38.9380, -92.3350)]
        for plat, plon in parking_locs:
            if _haversine(lat, lon, plat, plon) < 0.08:
                return [{'name': 'Parking Access', 'mtfcc': 'S1780',
                         'type_label': 'Parking Lot Road', 'surveillance_score': 3,
                         'width_ft': 20}]

        # Perimeter / connectors
        return [{'name': 'Campus Path', 'mtfcc': 'S1710',
                 'type_label': 'Pedestrian Walkway', 'surveillance_score': 4,
                 'width_ft': 10}]

    def get_sightline_analysis(self, lat: float, lon: float) -> Dict:
        """
        Full sightline analysis for a location.
        Returns natural surveillance score and contributing factors.
        """
        roads = self.get_roads_near(lat, lon, radius_ft=300)

        if not roads:
            return {
                'surveillance_score': 2,
                'surveillance_label': 'Very Poor',
                'road_count':         0,
                'dominant_road_type': 'No roads detected',
                'sightline_issues':   ['No road infrastructure detected nearby'],
                'source':             'tiger' if self.has_real_data else 'estimate',
            }

        avg_score    = sum(r['surveillance_score'] for r in roads) / len(roads)
        max_score    = max(r['surveillance_score'] for r in roads)
        dominant     = max(roads, key=lambda r: r['surveillance_score'])

        # Classify overall surveillance quality
        if avg_score >= 7:
            label = 'Good'
        elif avg_score >= 5:
            label = 'Moderate'
        elif avg_score >= 3:
            label = 'Poor'
        else:
            label = 'Very Poor'

        issues = []
        low_surveillance = [r for r in roads if r['surveillance_score'] <= 3]
        if low_surveillance:
            types = set(r['type_label'] for r in low_surveillance)
            issues.append(f"Low-surveillance road types nearby: {', '.join(types)}")
        if avg_score < 5:
            issues.append("Limited natural surveillance from road network")
        if max_score < 6:
            issues.append("No high-traffic roads within 300ft — isolated location")

        alley_or_parking = [r for r in roads
                            if r['mtfcc'] in ('S1730', 'S1780', 'S1640')]
        if alley_or_parking:
            issues.append("Alleys or service drives nearby create concealment opportunities")

        return {
            'surveillance_score': round(avg_score, 1),
            'surveillance_label': label,
            'road_count':         len(roads),
            'dominant_road_type': dominant['type_label'],
            'dominant_road_name': dominant['name'],
            'roads_nearby':       roads[:5],
            'sightline_issues':   issues,
            'source':             'tiger' if self.has_real_data else 'estimate',
        }

    def get_campus_road_summary(self) -> Dict:
        """Summary stats of campus road network."""
        if not self.has_real_data or self.campus_roads is None:
            return {'note': 'TIGER data not loaded'}
        counts = self.campus_roads['MTFCC'].value_counts().to_dict()
        labeled = {}
        for code, count in counts.items():
            label = ROAD_CLASSIFICATIONS.get(code, DEFAULT_ROAD)['label']
            labeled[f"{code} ({label})"] = count
        return {
            'total_segments': len(self.campus_roads),
            'by_type':        labeled,
            'source_file':    str(list(self.tiger_dir.glob("*.shp"))[0].name)
                              if list(self.tiger_dir.glob("*.shp")) else None,
        }


if __name__ == '__main__':
    loader = TIGERLoader()
    print("\nSightline analysis for key campus locations:\n")
    test_locs = [
        ("Memorial Union",   38.9404, -92.3277),
        ("Greek Town",       38.9395, -92.3320),
        ("Parking Lot A1",   38.9450, -92.3240),
        ("West Connector",   38.9410, -92.3340),
    ]
    for name, lat, lon in test_locs:
        analysis = loader.get_sightline_analysis(lat, lon)
        print(f"  {name:<25} Score: {analysis['surveillance_score']}/10 "
              f"[{analysis['surveillance_label']}] "
              f"({analysis['dominant_road_type']})")
        for issue in analysis['sightline_issues']:
            print(f"    ⚠ {issue}")