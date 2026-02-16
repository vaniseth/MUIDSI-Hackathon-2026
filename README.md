# MizzouSafe Integrated System

**Two-Agent System powered by Archia**
- Agent 1: Safety Copilot (RAG-based safety guidance)
- Agent 2: Route Safety (Crime data analysis) → **DEPENDS ON Agent 1**

---

## 🎯 What This System Does

### Agent 1: Safety Copilot
- **Purpose:** General campus safety guidance
- **Data Source:** MU safety documents (RAG)
- **Capabilities:**
  - Answers "What should I do?" questions
  - Emergency detection & triage
  - Retrieves relevant MU safety policies
  - Recommends appropriate contacts
- **Can work:** Independently

### Agent 2: Route Safety
- **Purpose:** Route-specific safety analysis
- **Data Source:** Historical crime data
- **Capabilities:**
  - Analyzes route safety scores
  - Identifies high-risk areas/times
  - Recommends transport alternatives
  - **CONSULTS Agent 1** for safety guidance
- **Dependency:** **REQUIRES Agent 1**

### Agent Dependency Chain
```
User Query → Agent 2 (Route Safety)
                ↓
            Analyzes crime data
                ↓
            Consults Agent 1 (Safety Copilot)
                ↓
            Agent 1 retrieves MU safety docs
                ↓
            Agent 1 provides guidance
                ↓
            Agent 2 combines both analyses
                ↓
            Complete response to user
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Archia
```bash
# Copy example env
cp .env.example .env

# Edit .env and add your Archia token:
ARCHIA_TOKEN=your_token_from_archia_console
```

Get your token from: https://console.archia.app

### 3. Build RAG Index
```bash
python src/vector_index.py
```

This processes MU safety documents and creates the FAISS index.

### 4. Run Examples
```bash
# Show all examples
python example.py -a

# Individual examples
python example.py -1  # Safety query (Agent 1)
python example.py -2  # Route query (Agent 2 → Agent 1)
python example.py -d  # Show agent dependency
```

---

## 💡 Usage Examples

### Example 1: Safety Query (Agent 1 Only)
```python
from src.orchestrator import MizzouSafeOrchestrator

orchestrator = MizzouSafeOrchestrator()

response = orchestrator.handle_query(
    query_type='safety',
    query="I see suspicious activity near my dorm",
    user_context={'is_alone': True, 'on_campus': True}
)

print(response['primary_action'])  # {'name': '📞 Call MUPD', ...}
print(response['llm_guidance'])     # AI-generated advice
print(response['safety_checklist']) # Safety tips
```

### Example 2: Route Query (Agent 2 depends on Agent 1)
```python
response = orchestrator.handle_query(
    query_type='route',
    start_lat=38.9404,  # Memorial Union
    start_lon=-92.3277,
    end_lat=38.9389,    # Rec Center
    end_lon=-92.3301,
    hour=22,  # 10 PM
    user_context={'is_alone': True}
)

# Route-specific analysis
print(response['route_risk'])
print(response['route_analysis'])

# Safety Copilot's input (Agent 1 → Agent 2)
print(response['safety_copilot_guidance'])

# Combined recommendations
print(response['recommendations'])
```

---

## 📁 Project Structure

```
mizzou-integrated/
├── src/
│   ├── config.py              # Configuration (Archia, models, keywords)
│   ├── archia_client.py       # Archia API wrapper
│   ├── document_processor.py  # PDF/TXT → chunks
│   ├── vector_index.py        # Build FAISS index
│   ├── retriever.py           # Vector similarity search
│   ├── risk_scorer.py         # Crime data risk analysis
│   ├── orchestrator.py        # Coordinates both agents ⭐
│   └── agents/
│       ├── safety_copilot.py  # Agent 1: RAG safety guidance
│       └── route_safety.py    # Agent 2: Route analysis (depends on Agent 1)
│
├── data/
│   ├── docs/                  # MU safety PDFs/documents
│   ├── crime_data/            # Crime CSV data
│   │   └── crime_data_clean.csv (sample included)
│   └── index/                 # FAISS index (generated)
│
├── example.py                 # Usage examples
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🔧 How It Works

### Agent 1: Safety Copilot (RAG Pipeline)

1. **Document Ingestion** (`document_processor.py`)
   - Loads PDFs/TXT from `data/docs/`
   - Chunks into ~500 words
   - Saves to `docstore.jsonl`

2. **Index Building** (`vector_index.py`)
   - Creates embeddings via Archia
   - Builds FAISS vector index
   - Saves to `data/index/`

3. **Query Processing** (`safety_copilot.py`)
   - Analyzes urgency (emergency/high/medium/low)
   - Retrieves top-3 relevant docs
   - Calls Claude via Archia
   - Returns structured response

### Agent 2: Route Safety (Crime Analysis + Agent 1)

1. **Risk Scoring** (`risk_scorer.py`)
   - Loads crime data CSV
   - Calculates risk scores based on:
     - Distance to historical crimes
     - Time of day weighting
     - Crime severity
   - Returns risk level (High/Medium/Low)

2. **Agent Consultation** (`route_safety.py`)
   - Analyzes route using crime data
   - **Builds query for Agent 1** based on risk
   - **Calls Agent 1** (`safety_copilot.process_query()`)
   - Receives safety guidance from Agent 1
   - Combines route analysis + Agent 1 guidance
   - Returns comprehensive response

---

## 🔗 Agent Dependency

### Why Agent 2 Depends on Agent 1

**Problem:** Route analysis needs both crime data AND safety guidance

**Solution:** Two-agent architecture
- Agent 1: Expert in MU safety policies (via RAG)
- Agent 2: Expert in route risk (via crime data)
- Agent 2 **consults** Agent 1 for policy-based guidance

### Dependency Flow

```python
# User asks Agent 2 about a route
route_query = "Memorial Union → Rec Center at 10 PM"

# Agent 2 analyzes crime data
risk_score = analyze_crime_data(route)  # → High risk

# Agent 2 builds question for Agent 1
safety_query = "I need to walk alone at night in a high-risk area. What should I do?"

# Agent 2 calls Agent 1
safety_guidance = safety_copilot.process_query(safety_query)

# Agent 1 returns: "Call Safe Ride: 573-882-1010"

# Agent 2 combines both
final_response = {
    'route_risk': 'High (crime data)',
    'safety_guidance': 'Call Safe Ride (from Agent 1)',
    'recommendations': [combined from both]
}
```

---

## ⚙️ Configuration

### Archia Settings
Edit `.env`:
```bash
ARCHIA_TOKEN=your_token_here
ARCHIA_BASE_URL=https://registry.archia.app/v1
```

### Emergency Keywords
Edit `src/config.py`:
```python
EMERGENCY_KEYWORDS = [
    "assault", "weapon", "danger", ...
]
```

### RAG Parameters
```python
CHUNK_SIZE = 500         # Words per chunk
TOP_K_DOCUMENTS = 3      # Docs to retrieve
```

### Risk Analysis
```python
RISK_RADIUS_MILES = 0.1  # Search radius for crimes
HIGH_RISK_THRESHOLD = 8  # Risk score threshold
```

---

## 📚 Adding Your Data

### MU Safety Documents
```bash
# Add PDFs to:
data/docs/

# Rebuild index:
python src/vector_index.py
```

**Recommended documents:**
- Annual Security Report
- MUPD Reporting Guidelines
- Safe Ride/Friend Walk Info
- Title IX Resources
- Emergency Protocols

### Crime Data
```bash
# Format: CSV with columns:
# date, hour, lat, lon, zone, category, severity

# Place in:
data/crime_data/crime_data_clean.csv
```

**Required columns:**
- `lat`, `lon` - Coordinates
- `hour` - Hour of day (0-23)
- `category` - Crime type
- `severity` - Severity score (1-5)
- `zone` - Campus zone

---

## 🧪 Testing

### Test Agent 1 (Safety Copilot)
```bash
python example.py -1
```

### Test Agent 2 (Route Safety with Agent 1 dependency)
```bash
python example.py -2
```

### Show Dependency Chain
```bash
python example.py -d
```

---

## 🎓 Key Concepts

### RAG (Retrieval-Augmented Generation)
- Retrieves relevant documents from knowledge base
- Augments LLM prompt with retrieved context
- Provides source citations
- More accurate than pure LLM

### Agent Dependency
- Agent 2 doesn't just call Agent 1
- Agent 2 **depends on** Agent 1's expertise
- Clear separation of concerns:
  - Agent 1: Policy expert (MU docs)
  - Agent 2: Data analyst (crime stats)
- Combined = comprehensive safety guidance

### Archia Integration
- Single API for multiple LLM providers
- Uses OpenAI SDK (embeddings) + Anthropic SDK (Claude)
- Configured via environment variables
- No separate API keys needed

---

## 📊 Response Structure

### From Agent 1 (Safety Copilot)
```python
{
    'agent': 'safety_copilot',
    'urgency': {
        'level': 'high',
        'keywords': ['suspicious', 'following'],
        'action': 'call_mupd'
    },
    'primary_action': {
        'name': '📞 Call MUPD',
        'contact': '573-882-7201',
        'description': '...'
    },
    'safety_checklist': [...],
    'llm_guidance': 'AI-generated advice...',
    'sources': ['campus_safety_guide.txt']
}
```

### From Agent 2 (Route Safety)
```python
{
    'agent': 'route_safety',
    'route_risk': {
        'overall_risk': 'High',
        'avg_risk_score': 8.5,
        'start': {...},
        'end': {...}
    },
    'route_analysis': 'AI analysis of route...',
    'safety_copilot_guidance': {  # ← From Agent 1
        'urgency': {...},
        'primary_action': {...},
        'safety_checklist': [...]
    },
    'recommendations': [...]  # ← Combined from both agents
}
```

---

## ⚠️ Important Notes

### Archia Setup
1. Get token from https://console.archia.app
2. Make sure you're in correct workspace
3. API key must match workspace

### Data Requirements
- **For Agent 1:** At least 1 MU safety document in `data/docs/`
- **For Agent 2:** Crime data CSV in `data/crime_data/`
- Sample files included for testing

### Agent Dependency
- Agent 1 can work independently
- Agent 2 **REQUIRES** Agent 1
- Don't skip Agent 1 initialization

---

## 🔮 Future Enhancements

- [ ] Web UI (Streamlit)
- [ ] Real-time crime data integration
- [ ] Mobile app API
- [ ] More sophisticated route algorithms
- [ ] Multi-language support
- [ ] Voice interface

---

## 📞 Emergency Contacts

**University of Missouri - Columbia:**
- 🚨 911 (Emergency)
- 📞 573-882-7201 (MUPD 24/7)
- 👥 573-884-9255 (Friend Walk)
- 🚗 573-882-1010 (Safe Ride)
- 📞 573-882-3880 (Title IX)

---

## 📝 License

Educational use for MUIDSI Hackathon 2026

---

**Built with Archia | Two-Agent Architecture | RAG + Crime Data**

**Stay Safe, Tigers! 🐯**
