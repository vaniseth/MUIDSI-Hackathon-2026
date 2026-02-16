# Como.gov Police Data Integration Guide

## 🎯 Overview

You can significantly enhance your route safety analysis by combining:
1. **MU Campus Crime Log** (from muop-mupdreports.missouri.edu) - Campus-specific
2. **Columbia Police Department Data** (from como.gov) - City-wide

This gives you comprehensive coverage of both on-campus and off-campus areas.

---

## 📥 Available Data Sources

### 1. MU Crime Log (Already Integrated) ✅
**Source:** https://muop-mupdreports.missouri.edu/dclog.php

**Coverage:**
- MU Campus and University-owned property
- Updated regularly by MUPD
- Specific campus locations

**What You Have:**
- ✅ `crime_data_clean__1_.csv` - Cleaned and geocoded
- ✅ `locations__1_.csv` - Campus location coordinates
- ✅ `mu_crime_log__2_.csv` - Raw log data

### 2. Columbia Police Department Data
**Source:** https://www.como.gov/police/data-reporting-forms/

**Available Datasets:**
- **Crime Statistics** - Annual crime data
- **Part 1 Crime Data** - Serious crimes (homicide, rape, robbery, assault, burglary, theft, auto theft)
- **Use of Force Reports**
- **Traffic Stop Data**
- **Monthly Crime Reports**

**Coverage:**
- City of Columbia (including off-campus areas)
- Broader geographic scope than MU data
- Complements campus data

---

## 🚀 How to Integrate Como.gov Data

### Step 1: Download Como.gov Data

1. Visit: https://www.como.gov/police/data-reporting-forms/

2. Download relevant datasets:
   - **Crime Statistics** (CSV or Excel)
   - **Part 1 Crimes** (most useful for safety routing)
   - Any other recent crime reports

3. Save files to your project:
```bash
mv ~/Downloads/como_crime_data.csv mizzou-integrated/data/crime_data/
```

### Step 2: Integrate the Data

```bash
cd mizzou-integrated

# Run the data integrator
python src/data_integrator.py
```

Or programmatically:

```python
from src.data_integrator import DataIntegrator

integrator = DataIntegrator()

# Load MU campus data
integrator.load_mu_crime_data("crime_data_clean__1_.csv")

# Load Como.gov data
integrator.load_como_pd_data("como_crime_data.csv")

# Combine both
integrated = integrator.integrate_data()

# Save integrated dataset
integrator.save_integrated_data()

# Get summary
summary = integrator.get_data_summary()
print(summary)
```

### Step 3: System Will Auto-Use Integrated Data

Once you have `crime_data_integrated.csv`, the system automatically uses it:

```python
from src.agents.route_safety import RouteSafetyAgent

# Automatically loads integrated data (MU + Como)
agent = RouteSafetyAgent()

# Now has comprehensive coverage!
response = agent.analyze_route(
    start_lat=38.9404, start_lon=-92.3277,
    end_lat=38.95, end_lon=-92.33,  # Off-campus location
    hour=22
)
```

---

## 📊 Data Schema Mapping

### Como.gov Data Format (Typical)

Como.gov datasets often include:
```csv
Date,Time,Location,Offense,Type,Status
01/15/2025,14:30,123 Main St,Theft,Part 1,Closed
```

### Our Standard Schema

```csv
date,hour,location,offense,category,severity,lat,lon,zone,data_source
2025-01-15,14,123 Main St,Theft,theft,2,38.95,-92.33,city_columbia,Como_PD
```

### Automatic Mapping

The `DataIntegrator` automatically maps common field names:

```python
field_mapping = {
    'Date': 'date',
    'Time': 'hour',
    'Address': 'location',
    'Offense': 'offense',
    'OffenseType': 'category',
    'Latitude': 'lat',
    'Longitude': 'lon'
}
```

### If Como.gov Format Differs

Edit `src/data_integrator.py` in the `_standardize_como_data()` method:

```python
def _standardize_como_data(self, df: pd.DataFrame) -> pd.DataFrame:
    standardized = pd.DataFrame()
    
    # ADD YOUR MAPPINGS HERE
    if 'ReportDate' in df.columns:  # Como uses "ReportDate"
        standardized['date'] = df['ReportDate']
    
    if 'OffenseCode' in df.columns:  # Como uses codes
        standardized['offense'] = df['OffenseCode'].map(code_to_offense)
    
    # ... etc
```

---

## 🗺️ Geographic Coverage

### With MU Data Only
- ✅ Campus buildings
- ✅ Parking lots
- ✅ Greek Town
- ❌ Off-campus apartments
- ❌ Downtown Columbia
- ❌ Surrounding neighborhoods

### With MU + Como.gov Data
- ✅ Campus buildings
- ✅ Parking lots
- ✅ Greek Town
- ✅ Off-campus apartments **NEW!**
- ✅ Downtown Columbia **NEW!**
- ✅ Surrounding neighborhoods **NEW!**

### Zone Classification

The integrator automatically assigns zones:

```python
# MU data - campus zones
- campus_north
- campus_south
- campus_center
- off_campus (near campus)

# Como.gov data - city zones
- city_columbia (general city area)

# You can customize this in _standardize_como_data()
```

---

## 🔍 What Como.gov Data Adds

### Better Coverage for:
1. **Off-Campus Housing**
   - Apartments near campus
   - Student housing areas
   - Greek life off-campus

2. **Downtown Routes**
   - Broadway corridor
   - District area
   - Off-campus bars/restaurants

3. **Surrounding Areas**
   - Neighborhoods around campus
   - Bus routes
   - Walking paths to off-campus locations

### Enhanced Risk Analysis
- More data points = more accurate risk scores
- City-wide crime patterns
- Better route recommendations for off-campus travel

---

## 📈 Example: Before & After

### Before (MU Data Only)
```python
# Route: Campus → Off-campus apartment
response = agent.analyze_route(
    start_lat=38.9404, start_lon=-92.3277,  # Memorial Union
    end_lat=38.95, end_lon=-92.33,          # Off-campus apt
    hour=22
)

# Result: Limited data for off-campus portion
# Risk Score: Based mainly on proximity to campus crimes
```

### After (MU + Como.gov Data)
```python
# Same route
response = agent.analyze_route(
    start_lat=38.9404, start_lon=-92.3277,
    end_lat=38.95, end_lon=-92.33,
    hour=22
)

# Result: Comprehensive data for entire route
# Risk Score: Includes city crimes in off-campus area
# Better recommendations!
```

---

## 🛠️ Customization Options

### 1. Adjust Zone Weights

Give more weight to campus vs. city data:

```python
# In risk_scorer.py
def get_risk_score(self, lat, lon, hour):
    # ...
    for crime in nearby_crimes:
        # Weight campus crimes more heavily
        if crime['zone'].startswith('campus'):
            weight_multiplier = 1.5  # Campus crimes weighed 50% more
        else:
            weight_multiplier = 1.0
```

### 2. Filter by Data Source

Only use certain data sources:

```python
# Only MU data
risk_scorer.crime_data = risk_scorer.crime_data[
    risk_scorer.crime_data['data_source'] == 'MU_Campus'
]

# Only Como data
risk_scorer.crime_data = risk_scorer.crime_data[
    risk_scorer.crime_data['data_source'] == 'Como_PD'
]
```

### 3. Add More Sources

Extend the integrator for additional data sources:

```python
class DataIntegrator:
    def load_county_data(self, filename):
        # Boone County data
        pass
    
    def load_state_data(self, filename):
        # Missouri State Highway Patrol data
        pass
```

---

## 📝 Como.gov Data Download Checklist

- [ ] Visit https://www.como.gov/police/data-reporting-forms/
- [ ] Download **Crime Statistics** CSV
- [ ] Download **Part 1 Crime Data** (if available separately)
- [ ] Save to `data/crime_data/`
- [ ] Run `python src/data_integrator.py`
- [ ] Verify: Check for `crime_data_integrated.csv`
- [ ] Test: Run route analysis to confirm it's using combined data

---

## 🧪 Testing Integration

```python
from src.data_integrator import DataIntegrator

# Initialize
integrator = DataIntegrator()

# Load both sources
integrator.load_mu_crime_data()
integrator.load_como_pd_data("como_crime_2025.csv")

# Integrate
integrated = integrator.integrate_data()

# Verify
summary = integrator.get_data_summary()

print(f"Total records: {summary['total_records']}")
print(f"Sources: {summary['sources']}")
print(f"Geocoded: {summary['geocoded_percentage']}%")

# Should show both MU_Campus and Como_PD
```

---

## ⚠️ Important Notes

### Data Quality
- **Como.gov data may not have coordinates** - You may need to geocode addresses
- **Different update frequencies** - MU updates daily, Como.gov varies
- **Historical data** - Como.gov may have years of historical data

### Privacy
- Both sources use **public data only**
- No personal information included
- Follow appropriate use guidelines

### Geocoding
If Como.gov data doesn't include lat/lon:

```python
# Option 1: Use a geocoding service
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="mizzou-safe")
location = geolocator.geocode("123 Main St, Columbia MO")
lat, lon = location.latitude, location.longitude

# Option 2: Use Google Geocoding API
# Option 3: Manually map common addresses
```

---

## 🔮 Future Enhancements

- [ ] Automatic Como.gov data updates (if they have an API)
- [ ] Real-time crime data integration
- [ ] Machine learning for crime prediction
- [ ] Heat map visualization
- [ ] Time-series analysis of crime trends

---

## 📞 Data Sources

**MU Crime Log:**
- URL: https://muop-mupdreports.missouri.edu/dclog.php
- Update frequency: Daily
- Coverage: Campus only

**Columbia Police Department:**
- URL: https://www.como.gov/police/data-reporting-forms/
- Update frequency: Varies by dataset (monthly, annually)
- Coverage: City-wide

---

## ✅ Summary

**Yes, you should absolutely use Como.gov data!**

**Benefits:**
- ✅ More comprehensive coverage
- ✅ Off-campus safety insights
- ✅ Better route recommendations
- ✅ Larger dataset = more accurate risk scores

**How to do it:**
1. Download Como.gov crime data CSVs
2. Run `python src/data_integrator.py`
3. System automatically uses integrated data
4. Enjoy enhanced route safety analysis!

---

**Ready to integrate? Download Como.gov data and run the integrator!** 🚀
