"""
Configuration for MizzouSafe Integrated System
Uses Archia for LLM access
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project paths
PROJECT_ROOT = Path.cwd()
DATA_DIR = PROJECT_ROOT / "data"
DOCS_DIR = DATA_DIR / "docs"
CRIME_DATA_DIR = DATA_DIR / "crime_data"
INDEX_DIR = DATA_DIR / "index"

# Create directories
for dir_path in [DOCS_DIR, CRIME_DATA_DIR, INDEX_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Archia API Configuration
ARCHIA_TOKEN = os.getenv("ARCHIA_TOKEN", "")
ARCHIA_BASE_URL = os.getenv("ARCHIA_BASE_URL", "https://registry.archia.app/v1")

# Models (Archia provides access to multiple models)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHAT_MODEL = "gpt-4.1" 
EMBEDDING_DIMENSION = 384  # all-MiniLM-L6-v2

# RAG Parameters
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K_DOCUMENTS = 3

# Emergency Keywords
EMERGENCY_KEYWORDS = [
    "assault", "attack", "rape", "danger", "threatened", "weapon",
    "gun", "knife", "bleeding", "stalker", "stalking", "emergency",
    "scared", "violence", "fire", "help"
]

HIGH_PRIORITY_KEYWORDS = [
    "suspicious", "uncomfortable", "unsafe", "worried", "harass",
    "alone", "lost", "stranded", "dark", "following"
]

# MU Emergency Contacts
EMERGENCY_CONTACTS = {
    "911":            {"name": "Emergency Services",       "number": "911"},
    "MUPD":           {"name": "MU Police (24/7)",         "number": "573-882-7201"},
    "Safe_Ride":      {"name": "Safe Ride",                "number": "573-882-1010"},
    "Friend_Walk":    {"name": "Friend Walk",              "number": "573-884-9255"},
    "RSVP":           {"name": "RSVP Center (confidential)","number": "573-882-6638"},
    "Title_IX":       {"name": "Title IX / OIE",           "number": "573-882-3880"},
    "Counseling":     {"name": "Counseling Center",        "number": "573-882-6601"},
    "Dean_Students":  {"name": "Dean of Students",         "number": "573-882-5397"},
    "True_North":     {"name": "True North (DV/SA)",       "number": "573-875-1369"},
    "Crime_Stoppers": {"name": "Crime Stoppers (anon)",    "number": "573-875-8477"},
    "Crisis_Line":    {"name": "Suicide & Crisis Lifeline","number": "988"},
}

# Official MU Reporting Forms & Links
MU_REPORTING_LINKS = {
    "csa_report": {
        "name": "Campus Security Authority (CSA) Incident Report",
        "url": "https://missouri.qualtrics.com/jfe/form/SV_1THwCQ2fvSs1SzH",
        "use_for": "CSAs reporting a Clery Act crime they witnessed or were told about"
    },
    "online_crime_report": {
        "name": "MUPD Online Crime Report",
        "url": "https://mupolice.missouri.edu/report-crime/",
        "use_for": "Lost property, theft, vandalism (non-emergency)"
    },
    "silent_witness": {
        "name": "Silent Witness (Anonymous)",
        "url": "https://mupolice.missouri.edu/about/units/investigations/",
        "use_for": "Anonymously reporting crimes or suspicious activity"
    },
    "oie_report": {
        "name": "Office of Institutional Equity (OIE) Report",
        "url": "https://equity.missouri.edu/reporting-and-policies/",
        "use_for": "Sexual assault, harassment, discrimination, Title IX, stalking, retaliation"
    },
    "student_at_risk": {
        "name": "Student At Risk / Care Team Report",
        "url": "https://studentaffairs.missouri.edu/concerned-about-a-student/",
        "use_for": "Concern about a student's well-being, distress, or threatening behavior"
    },
    "rsvp_center": {
        "name": "RSVP Center (Confidential Support)",
        "url": "https://rsvp.missouri.edu/",
        "use_for": "Confidential support for sexual assault, relationship violence, stalking"
    },
    "mu_alert": {
        "name": "MU Alert Signup",
        "url": "https://mupolice.missouri.edu/services/mu-alert/",
        "use_for": "Sign up for emergency alerts and notifications"
    },
    "victim_assistance": {
        "name": "MUPD Victim Assistance",
        "url": "https://mupolice.missouri.edu/services/vrights/",
        "use_for": "Victim rights information and resource referrals"
    },
    "annual_security_report": {
        "name": "2025 Annual Security & Fire Safety Report",
        "url": "https://mupolice.missouri.edu/about/annual-security-report/",
        "use_for": "Campus crime statistics and safety policies"
    },
    "true_north": {
        "name": "True North (Domestic & Sexual Violence)",
        "url": "https://www.truenorthcolumbia.org/",
        "use_for": "Comprehensive DV/SA support services in Columbia"
    },
}

SAFE_DESTINATIONS = {
    "MUPD": {
        "name": "MU Police Department",
        "lat": 38.9456, "lon": -92.3264,
        "address": "901 Virginia Ave",
        "phone": "573-882-7201",
        "available": "24/7"
    },
    "Memorial_Union": {
        "name": "Memorial Union",
        "lat": 38.9404, "lon": -92.3277,
        "available": "Until midnight"
    },
    "Student_Center": {
        "name": "MU Student Center",
        "lat": 38.9423, "lon": -92.3268,
        "available": "Until 11pm"
    },
    "Ellis_Library": {
        "name": "Ellis Library",
        "lat": 38.9445, "lon": -92.3263,
        "available": "Until midnight"
    },
    "University_Hospital": {
        "name": "University Hospital",
        "lat": 38.9403, "lon": -92.3245,
        "phone": "573-882-4141",
        "available": "24/7"
    },
}

LOCATION_TRIGGER_KEYWORDS = [
    "suspicious", "following", "scared", "unsafe", "danger",
    "threatened", "stalker", "uncomfortable", "worried", "help",
    "assault", "attack", "lost", "stranded", "dark", "alone",
    "harass", "weapon", "gun", "knife"
]

# Route Analysis Configuration
RISK_RADIUS_MILES = 0.1  # Search radius for crime risk
HIGH_RISK_THRESHOLD = 8
MEDIUM_RISK_THRESHOLD = 4

# Agent Configuration
AGENT_NAMES = {
    "safety_copilot": "agent:mizzou_safety_copilot",  # RAG agent
    "route_safety": "agent:mizzou_route_safety"       # Route analysis agent
}

# File paths
FAISS_INDEX_PATH = INDEX_DIR / "faiss.index"
METADATA_PATH = INDEX_DIR / "metadata.pkl"
DOCSTORE_PATH = INDEX_DIR / "docstore.jsonl"
CRIME_DATA_PATH = CRIME_DATA_DIR / "crime_data_clean.csv"
