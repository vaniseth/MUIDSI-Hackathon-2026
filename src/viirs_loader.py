"""
VIIRS Nighttime Lights Loader
==============================
Loads satellite-measured nighttime luminance data from VIIRS (Visible Infrared
Imaging Radiometer Suite) and samples it at any lat/lon on campus.

Data source: https://eogdata.mines.edu/products/vnl/
Product: VNL V2.2 Annual composite (or monthly for recent data)
Format: GeoTIFF (.tif)

SETUP:
  1. Visit https://eogdata.mines.edu/products/vnl/
  2. Download the Annual VNL V2.2 tile covering Missouri:
       - Tile: 75N060W  (covers central US)
       - File: VNL_v22_npp_2023_global_vcmslcfg_c202402081200.average_masked.tif
       OR the smaller monthly product for 2024/2025
  3. Place the .tif file in: data/viirs/
  4. This loader will auto-detect it

FALLBACK:
  If no VIIRS data is present, the loader returns estimated luminance values
  based on known campus infrastructure, so the system still works at demo time.

LUMINANCE THRESHOLDS (nW/cm²/sr):
  < 0.5   → Very dark  — critical lighting gap
  0.5–2.0 → Dim        — below safe pedestrian threshold
  2.0–5.0 → Adequate   — meets minimum campus standard
  > 5.0   → Well-lit   — above standard
"""

import math
import struct
from pathlib import Path
from typing import Dict, Optional, Tuple
import sys

sys.path.append(str(Path(__file__).parent.parent))
from src.config import DATA_DIR

VIIRS_DIR = DATA_DIR / "viirs"

# Luminance thresholds in nW/cm²/sr
THRESHOLD_CRITICAL  = 0.5    # Very dark
THRESHOLD_DIM       = 2.0    # Below safe pedestrian standard
THRESHOLD_ADEQUATE  = 5.0    # Meets campus minimum
THRESHOLD_WELL_LIT  = 10.0   # Above standard

# Estimated luminance for known MU campus locations
# Based on Google Earth nighttime imagery + street infrastructure knowledge
# Used as fallback when no VIIRS raster is available
CAMPUS_LUMINANCE_ESTIMATES = {
    # (lat_center, lon_center, radius_miles, luminance_nw)
    # Core campus — well lit
    (38.9404, -92.3277, 0.05, 6.2),   # Memorial Union
    (38.9445, -92.3263, 0.05, 5.8),   # Ellis Library
    (38.9423, -92.3268, 0.05, 5.5),   # Student Center
    (38.9441, -92.3269, 0.05, 4.8),   # Jesse Hall
    (38.9438, -92.3256, 0.05, 4.5),   # Engineering
    # Rec & athletics — moderate
    (38.9389, -92.3301, 0.05, 3.2),   # Rec Center
    (38.9356, -92.3332, 0.06, 4.1),   # Mizzou Arena
    (38.9355, -92.3306, 0.06, 2.8),   # Faurot Field (dim when no event)
    # Residential & social — variable
    (38.9395, -92.3320, 0.06, 2.1),   # Greek Town — borderline
    (38.9430, -92.3275, 0.04, 3.8),   # Tiger Plaza
    (38.9415, -92.3280, 0.04, 3.1),   # Hitt Street
    # Parking — poorly lit
    (38.9450, -92.3240, 0.06, 1.4),   # Parking Lot A1 — dim
    (38.9380, -92.3350, 0.06, 0.9),   # Parking Lot C2 — very dim
    # Perimeter — dark
    (38.9380, -92.3250, 0.05, 1.8),   # Conley Ave
    (38.9360, -92.3270, 0.05, 1.2),   # South Campus Path
    (38.9465, -92.3270, 0.05, 2.3),   # North Campus
    (38.9420, -92.3220, 0.06, 1.6),   # East Entrance
    (38.9410, -92.3340, 0.06, 0.8),   # West Connector — dark
}


def _haversine(lat1, lon1, lat2, lon2) -> float:
    R = 3959
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    return R * 2 * math.asin(math.sqrt(a))


def _luminance_label(lum: float) -> str:
    if lum < THRESHOLD_CRITICAL:
        return "Very Dark"
    elif lum < THRESHOLD_DIM:
        return "Dim"
    elif lum < THRESHOLD_ADEQUATE:
        return "Adequate"
    elif lum < THRESHOLD_WELL_LIT:
        return "Well-Lit"
    else:
        return "Bright"


def _luminance_risk(lum: float) -> str:
    """Convert luminance to lighting risk level."""
    if lum < THRESHOLD_CRITICAL:
        return "High"
    elif lum < THRESHOLD_DIM:
        return "Medium"
    else:
        return "Low"


class VIIRSLoader:
    """
    Loads VIIRS nighttime luminance data and samples it at any lat/lon.

    Falls back to campus-specific estimates if no raster file is found,
    so the system works without downloading the full satellite dataset.
    """

    def __init__(self, viirs_dir: Path = VIIRS_DIR):
        self.viirs_dir = viirs_dir
        self.raster = None
        self.raster_path = None
        self.has_real_data = False
        self._try_load_raster()

    def _try_load_raster(self):
        """Attempt to load a VIIRS GeoTIFF from the data/viirs/ directory."""
        if not self.viirs_dir.exists():
            self.viirs_dir.mkdir(parents=True, exist_ok=True)
            print("📡 VIIRS: data/viirs/ created — no satellite data loaded yet")
            print("   Download from: https://eogdata.mines.edu/products/vnl/")
            return

        # Look for any .tif file
        tif_files = list(self.viirs_dir.glob("*.tif")) + \
                    list(self.viirs_dir.glob("*.tiff"))

        if not tif_files:
            print("📡 VIIRS: No raster file found — using campus luminance estimates")
            print("   To enable real satellite data, place a VIIRS .tif in data/viirs/")
            return

        # Filter out lit_mask files — those are binary 0/1 masks, NOT luminance values.
        # The correct files are: average_masked.tif, average.tif, or cf_cvg.tif
        luminance_files = [f for f in tif_files
                           if 'lit_mask' not in f.name.lower()
                           and 'cf_cvg' not in f.name.lower()]

        if not luminance_files:
            print(f"📡 VIIRS: Found {len(tif_files)} .tif file(s) but all are lit_mask/cf_cvg (binary masks).")
            print("   These are NOT luminance values — using campus estimates instead.")
            print("   Download the 'average_masked.tif' product from eogdata.mines.edu/products/vnl/")
            return

        tif_files = luminance_files  # Use only true luminance files

        # Try rasterio first (full GeoTIFF support)
        try:
            import rasterio
            self.raster_path = tif_files[0]
            self.raster = rasterio.open(str(self.raster_path))
            self.has_real_data = True
            print(f"✅ VIIRS: Loaded satellite data — {self.raster_path.name}")
            print(f"   Bounds: {self.raster.bounds}")
            print(f"   Resolution: {self.raster.res}")
            return
        except ImportError:
            pass  # rasterio not installed

        # Fallback: try gdal
        try:
            from osgeo import gdal
            self.raster_path = tif_files[0]
            self.raster = gdal.Open(str(self.raster_path))
            if self.raster:
                self.has_real_data = True
                self._setup_gdal_transform()
                print(f"✅ VIIRS: Loaded via GDAL — {self.raster_path.name}")
                return
        except ImportError:
            pass

        print("📡 VIIRS: .tif file found but rasterio/gdal not installed")
        print("   Install with: pip install rasterio --break-system-packages")
        print("   Falling back to campus luminance estimates")

    def _setup_gdal_transform(self):
        """Pre-compute inverse geotransform for GDAL raster."""
        gt = self.raster.GetGeoTransform()
        # Store geotransform: (xmin, pixel_width, 0, ymax, 0, -pixel_height)
        self._gdal_gt = gt

    def _sample_rasterio(self, lat: float, lon: float) -> Optional[float]:
        """Sample VIIRS raster at lat/lon using rasterio."""
        try:
            import rasterio
            from rasterio.transform import rowcol

            # Bounds check — return None if coordinate is outside the raster extent
            bounds = self.raster.bounds
            if not (bounds.left <= lon <= bounds.right and
                    bounds.bottom <= lat <= bounds.top):
                return None

            row, col = rowcol(self.raster.transform, lon, lat)

            # Validate pixel position is within raster dimensions
            if row < 0 or col < 0 or row >= self.raster.height or col >= self.raster.width:
                return None

            data = self.raster.read(1, window=((row, row+1), (col, col+1)))
            val = float(data[0][0])

            # VIIRS VNL V2 annual/monthly composite: values are in nW/cm²/sr
            # Typical campus values: 1-20 nW/cm²/sr
            # Nodata is typically -9999 or 65535 (uint16 overflow)
            nodata = self.raster.nodata
            if nodata is not None and abs(val - nodata) < 1e-3:
                return None
            if val <= 0 or val > 5000:   # Sanity check: 5000 nW is far above any campus
                return None

            return round(val, 3)
        except Exception:
            return None

    def _sample_gdal(self, lat: float, lon: float) -> Optional[float]:
        """Sample VIIRS raster at lat/lon using GDAL."""
        try:
            gt = self._gdal_gt
            cols = self.raster.RasterXSize
            rows = self.raster.RasterYSize
            # Convert lat/lon to pixel coordinates
            px = int((lon - gt[0]) / gt[1])
            py = int((lat - gt[3]) / gt[5])
            # Bounds check
            if px < 0 or py < 0 or px >= cols or py >= rows:
                return None
            band = self.raster.GetRasterBand(1)
            nodata = band.GetNoDataValue()
            data = band.ReadAsArray(px, py, 1, 1)
            if data is None:
                return None
            val = float(data[0][0])
            if nodata is not None and abs(val - nodata) < 1e-3:
                return None
            return val if (0 < val <= 5000) else None
        except Exception:
            return None

    def _estimate_luminance(self, lat: float, lon: float) -> float:
        """
        Estimate luminance from known campus infrastructure data.
        Weighted average of nearby reference points.
        """
        weights = []
        values = []

        for ref_lat, ref_lon, radius, lum in CAMPUS_LUMINANCE_ESTIMATES:
            dist = _haversine(lat, lon, ref_lat, ref_lon)
            if dist <= radius * 2:  # Sample within 2x the reference radius
                # Inverse-distance weighting
                weight = max(0.01, 1.0 / (dist + 0.001))
                weights.append(weight)
                values.append(lum)

        if not weights:
            # Outside all known reference zones — assume dim perimeter
            return 1.5

        weighted = sum(w * v for w, v in zip(weights, values)) / sum(weights)
        return round(weighted, 2)

    def sample(self, lat: float, lon: float) -> Dict:
        """
        Sample nighttime luminance at a given coordinate.

        Returns:
            {
              'luminance_nw':    float,   # nW/cm²/sr
              'label':           str,     # "Very Dark" / "Dim" / "Adequate" / "Well-Lit"
              'lighting_risk':   str,     # "High" / "Medium" / "Low"
              'below_threshold': bool,    # True if below safe pedestrian standard (2.0)
              'source':          str,     # "viirs_satellite" or "campus_estimate"
              'threshold':       float,   # The threshold used for "safe" classification
            }
        """
        luminance = None
        source = "campus_estimate"

        if self.has_real_data and self.raster is not None:
            # Try satellite data first
            try:
                import rasterio
                luminance = self._sample_rasterio(lat, lon)
                if luminance is not None:
                    source = "viirs_satellite"
            except ImportError:
                luminance = self._sample_gdal(lat, lon)
                if luminance is not None:
                    source = "viirs_satellite"

        if luminance is None:
            luminance = self._estimate_luminance(lat, lon)

        label        = _luminance_label(luminance)
        lighting_risk = _luminance_risk(luminance)
        below_threshold = luminance < THRESHOLD_DIM

        return {
            'luminance_nw':    round(luminance, 3),
            'label':           label,
            'lighting_risk':   lighting_risk,
            'below_threshold': below_threshold,
            'source':          source,
            'threshold':       THRESHOLD_DIM,
            'threshold_label': f"{THRESHOLD_DIM} nW/cm²/sr (safe pedestrian minimum)",
        }

    def sample_batch(self, locations: list) -> list:
        """
        Sample luminance for a list of {'lat', 'lon', 'name'} dicts.
        Returns each dict enriched with luminance data.
        """
        results = []
        for loc in locations:
            reading = self.sample(loc['lat'], loc['lon'])
            results.append({
                **loc,
                'viirs': reading
            })
        return results

    def get_lighting_summary(self, lat: float, lon: float) -> str:
        """
        Returns a plain-English lighting assessment for use in CPTED reports.
        """
        reading = self.sample(lat, lon)
        lum   = reading['luminance_nw']
        label = reading['label']
        source_note = "(satellite-measured)" if reading['source'] == "viirs_satellite" \
                      else "(campus-estimated)"

        if lum < THRESHOLD_CRITICAL:
            return (f"Critically dark — {lum:.2f} nW/cm²/sr {source_note}. "
                    f"Well below the {THRESHOLD_DIM} nW/cm²/sr safe pedestrian threshold. "
                    f"Immediate lighting intervention required.")
        elif lum < THRESHOLD_DIM:
            deficit = round(((THRESHOLD_DIM - lum) / THRESHOLD_DIM) * 100)
            return (f"Inadequate lighting — {lum:.2f} nW/cm²/sr {source_note}. "
                    f"{deficit}% below the {THRESHOLD_DIM} nW/cm²/sr safe minimum. "
                    f"Lighting improvement recommended.")
        elif lum < THRESHOLD_ADEQUATE:
            return (f"Marginal lighting — {lum:.2f} nW/cm²/sr {source_note}. "
                    f"Meets minimum standard but below the {THRESHOLD_ADEQUATE} nW/cm²/sr "
                    f"recommended campus level.")
        else:
            return (f"Adequate lighting — {lum:.2f} nW/cm²/sr {source_note}. "
                    f"Meets campus safety standard.")

    def close(self):
        """Release raster file handle."""
        if self.has_real_data and self.raster is not None:
            try:
                self.raster.close()
            except Exception:
                pass


# ── Download helper ───────────────────────────────────────────────────────────

def print_download_instructions():
    print("""
╔══════════════════════════════════════════════════════════════╗
║  VIIRS Nighttime Lights — Download Instructions              ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  1. Go to: https://eogdata.mines.edu/products/vnl/           ║
║                                                              ║
║  2. Select: Annual VNL V2.2 (recommended for stability)      ║
║     OR:     Monthly VCMSLCFG (for more recent data)          ║
║                                                              ║
║  3. Download the tile covering Missouri:                     ║
║     Filename contains: "75N060W" or use global composite     ║
║     File:  *.average_masked.tif  (cloud-free average)        ║
║                                                              ║
║  4. Place the .tif file in:  data/viirs/                     ║
║                                                              ║
║  5. Install rasterio:                                        ║
║     pip install rasterio --break-system-packages             ║
║                                                              ║
║  WITHOUT this file, the system uses campus luminance         ║
║  estimates based on known MU infrastructure — still works,   ║
║  just not satellite-backed.                                  ║
╚══════════════════════════════════════════════════════════════╝
""")


if __name__ == '__main__':
    print_download_instructions()
    loader = VIIRSLoader()
    print("\nSampling key campus locations:\n")
    test_locations = [
        ("Memorial Union",   38.9404, -92.3277),
        ("Parking Lot A1",   38.9450, -92.3240),
        ("Greek Town",       38.9395, -92.3320),
        ("West Connector",   38.9410, -92.3340),
        ("Rec Center",       38.9389, -92.3301),
    ]
    for name, lat, lon in test_locations:
        reading = loader.sample(lat, lon)
        bar = "█" * int(reading['luminance_nw'])
        print(f"  {name:<25} {reading['luminance_nw']:>5.2f} nW  "
              f"[{reading['label']:<12}]  {bar}")
    loader.close()