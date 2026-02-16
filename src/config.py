"""
Configuration for MizzouSafe Integrated System
Uses Archia for LLM access
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent
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
EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "claude-sonnet-4-20250514"  # Using Claude via Archia

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
    "911": {"name": "Emergency Services", "number": "911"},
    "MUPD": {"name": "MU Police", "number": "573-882-7201"},
    "Safe_Ride": {"name": "Safe Ride", "number": "573-882-1010"},
    "Friend_Walk": {"name": "Friend Walk", "number": "573-884-9255"},
    "Title_IX": {"name": "Title IX", "number": "573-882-3880"},
}

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
