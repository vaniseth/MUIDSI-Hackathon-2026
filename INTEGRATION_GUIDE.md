# MizzouSafe Integrated System - Complete Guide

**Dual-Agent System for Campus Safety**
- Built with Archia API
- Agent dependency architecture
- RAG + Crime Data Analysis

---

## 🎉 What You Got

### Complete Two-Agent System

**Agent 1: Safety Copilot** (Independent)
- RAG-based safety guidance
- Uses MU safety documents
- Provides general safety advice
- Can work standalone

**Agent 2: Route Safety** (Depends on Agent 1)
- Crime data analysis
- Route risk scoring
- **Consults Agent 1** for safety recommendations
- Combines data + policy guidance

### Key Innovation: Agent Dependency

Agent 2 doesn't just work alongside Agent 1 - it **depends on** Agent 1:

```
Route Query → Agent 2
                ↓
            Analyzes crime data (High risk detected)
                ↓
            Builds question: "How should I handle high-risk area?"
                ↓
            Calls Agent 1 (Safety Copilot)
                ↓
            Agent 1 retrieves MU safety docs
                ↓
            Agent 1: "Use Safe Ride service"
                ↓
            Agent 2 combines: Crime data + Agent 1 advice
                ↓
            User gets: "High risk route. Use Safe Ride (from Agent 1)"
```

---

## 📦 File Structure

```
mizzou-integrated/
├── src/
│   ├── config.py                    # Archia + all settings
│   ├── archia_client.py             # Archia API wrapper ⭐
│   ├── document_processor.py         # PDF → chunks
│   ├── vector_index.py              # FAISS index builder
│   ├── retriever.py                 # Vector search
│   ├── risk_scorer.py               # Crime risk analysis
│   ├── orchestrator.py              # Coordinates agents ⭐
│   └── agents/
│       ├── safety_copilot.py        # Agent 1 ⭐
│       └── route_safety.py          # Agent 2 (depends on Agent 1) ⭐
│
├── data/
│   ├── docs/                        # MU safety documents
│   │   └── campus_safety_guide.txt  # Sample included
│   ├── crime_data/
│   │   └── crime_data_clean.csv     # Sample crime data
│   └── index/                       # FAISS index (generated)
│
├── example.py                       # Complete usage examples
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Setup (3 Steps)

### 1. Install
```bash
cd mizzou-integrated
pip install -r requirements.txt
```

### 2. Configure Archia
```bash
cp .env.example .env
# Edit .env:
ARCHIA_TOKEN=your_token_from_console.archia.app
```

### 3. Build Index
```bash
python src/vector_index.py
```

---

## 💻 Code Examples

### Example 1: Direct Agent Usage

```python
from src.agents.safety_copilot import SafetyCopilot

# Agent 1 works independently
copilot = SafetyCopilot()

response = copilot.process_query(
    query="Someone is following me",
    user_context={'is_alone': True, 'on_campus': True}
)

print(response['primary_action'])  # Call MUPD
print(response['llm_guidance'])     # AI advice from RAG
```

### Example 2: Agent Dependency

```python
from src.agents.route_safety import RouteSafetyAgent

# Agent 2 depends on Agent 1 (initialized internally)
route_agent = RouteSafetyAgent()  # ← Automatically creates Agent 1

response = route_agent.analyze_route(
    start_lat=38.9404, start_lon=-92.3277,  # Memorial Union
    end_lat=38.9389, end_lon=-92.3301,      # Rec Center
    hour=22  # 10 PM
)

# Response includes:
print(response['route_risk'])                 # From crime data
print(response['safety_copilot_guidance'])    # From Agent 1
print(response['route_analysis'])             # Combined analysis
```

### Example 3: Orchestrator (Recommended)

```python
from src.orchestrator import MizzouSafeOrchestrator

orchestrator = MizzouSafeOrchestrator()

# Safety query → Agent 1 only
safety_response = orchestrator.handle_query(
    query_type='safety',
    query="What if I see suspicious activity?",
    user_context={'on_campus': True}
)

# Route query → Agent 2 (which calls Agent 1)
route_response = orchestrator.handle_query(
    query_type='route',
    start_lat=38.9404, start_lon=-92.3277,
    end_lat=38.9389, end_lon=-92.3301,
    hour=22,
    user_context={'is_alone': True}
)
```

---

## 🔧 Archia Integration

### How Archia is Used

**In `archia_client.py`:**

```python
from openai import OpenAI
from anthropic import Anthropic

class ArchiaClient:
    def __init__(self):
        # OpenAI-compatible endpoint (for embeddings)
        self.openai_client = OpenAI(
            base_url="https://registry.archia.app/v1",
            default_headers={"Authorization": f"Bearer {ARCHIA_TOKEN}"}
        )
        
        # Anthropic endpoint (for Claude)
        self.anthropic_client = Anthropic(
            api_key=ARCHIA_TOKEN,
            base_url="https://api.archia.io/v1"
        )
    
    def create_embedding(self, text):
        # Uses OpenAI-compatible endpoint
        return self.openai_client.embeddings.create(...)
    
    def chat(self, system_prompt, user_message):
        # Uses Anthropic Claude via Archia
        return self.anthropic_client.messages.create(...)
```

**Models Used:**
- `text-embedding-3-small` - For RAG embeddings
- `claude-sonnet-4-20250514` - For chat (via Archia)

---

## 🔗 Agent Dependency Explained

### Why This Architecture?

**Problem:** Route analysis needs BOTH:
1. Crime data (quantitative risk)
2. Safety policy guidance (what to do)

**Bad Solution:** Put everything in one agent
- Too complex
- Hard to maintain
- Can't reuse safety guidance

**Our Solution:** Two specialized agents
- Agent 1: Safety policy expert (MU docs via RAG)
- Agent 2: Crime analyst (historical data)
- Agent 2 **consults** Agent 1 when needed

### How Dependency Works

**In `route_safety.py`:**

```python
class RouteSafetyAgent:
    def __init__(self):
        self.risk_scorer = RiskScorer()
        # DEPENDENCY: Initialize Agent 1
        self.safety_copilot = SafetyCopilot()  # ← Agent 1
    
    def analyze_route(self, ...):
        # Step 1: Analyze route with crime data
        risk_score = self.risk_scorer.get_risk_score(...)
        
        # Step 2: Build question for Agent 1
        query = self._build_safety_query(risk_score, ...)
        
        # Step 3: CALL Agent 1
        copilot_response = self.safety_copilot.process_query(query)
        
        # Step 4: Combine both analyses
        return {
            'route_risk': risk_score,           # From Agent 2
            'safety_guidance': copilot_response, # From Agent 1
            'recommendations': [combined]
        }
```

**Key Points:**
- Agent 2 creates Agent 1 internally
- Agent 2 calls Agent 1's `process_query()` method
- Agent 1 doesn't know it's being called by Agent 2
- Clean separation of concerns

---

## 📊 Response Flow

### Safety Query (Agent 1 Only)

```
User: "What should I do if I see suspicious activity?"
  ↓
Orchestrator → Agent 1 (Safety Copilot)
  ↓
Agent 1:
  1. Analyzes urgency: "high priority"
  2. Retrieves MU docs about suspicious activity
  3. Calls Claude via Archia
  4. Returns: "Call MUPD immediately"
  ↓
User gets comprehensive safety guidance
```

### Route Query (Agent 2 depends on Agent 1)

```
User: "Is it safe to walk Memorial Union → Rec Center at 10 PM?"
  ↓
Orchestrator → Agent 2 (Route Safety)
  ↓
Agent 2:
  1. Loads crime data
  2. Calculates risk: "High" (8.5/10)
  3. Builds query: "How to handle high-risk area at night alone?"
  4. CALLS Agent 1 ←←← DEPENDENCY
  ↓
Agent 1:
  1. Retrieves MU safety docs
  2. Returns: "Use Safe Ride: 573-882-1010"
  ↓
Agent 2:
  1. Receives Agent 1's guidance
  2. Combines with route analysis
  3. Returns: "High risk + Use Safe Ride (from Agent 1)"
  ↓
User gets route-specific + policy-based guidance
```

---

## 🧪 Testing the System

### Test 1: Agent 1 Standalone
```bash
python example.py -1
```

Output shows:
- RAG retrieval working
- Emergency detection
- Source citations

### Test 2: Agent Dependency
```bash
python example.py -2
```

Output shows:
- Crime data analysis
- **Agent 2 consulting Agent 1** (you'll see the console output)
- Combined recommendations

### Test 3: Show Dependency Chain
```bash
python example.py -d
```

Demonstrates the full workflow step-by-step.

---

## 🎓 Key Concepts

### RAG (Retrieval-Augmented Generation)
1. User asks question
2. System retrieves relevant docs from vector DB
3. Docs + question sent to LLM
4. LLM generates answer with citations
5. More accurate than pure LLM

**Implementation:**
- `document_processor.py` - Chunks docs
- `vector_index.py` - Creates embeddings
- `retriever.py` - Searches vector DB
- `safety_copilot.py` - Uses retrieved context

### Agent Architecture
- **Single Agent:** One agent does everything (complex, hard to maintain)
- **Multi-Agent:** Multiple specialized agents (our approach)
- **Agent Dependency:** Agents call each other (clear separation)

**Our Implementation:**
- Agent 1: Specialist in MU safety policy
- Agent 2: Specialist in crime data analysis
- Agent 2 leverages Agent 1's expertise

### Archia Platform
- Unified API for multiple LLM providers
- Single token → access OpenAI + Anthropic + others
- OpenAI-compatible SDK
- Easy to switch models

---

## 📝 Adding Your Data

### MU Safety Documents

1. Get official documents:
   - Annual Security Report (PDF)
   - MUPD Guidelines (PDF)
   - Title IX Resources (PDF)
   - Emergency Protocols (PDF)

2. Add to project:
```bash
cp your_docs/*.pdf data/docs/
```

3. Rebuild index:
```bash
python src/vector_index.py
```

### Crime Data

1. Format: CSV with these columns:
```csv
date,hour,lat,lon,zone,category,severity
2025-02-01,22,38.9404,-92.3277,campus_center,assault,5
```

2. Add to project:
```bash
cp your_crime_data.csv data/crime_data/crime_data_clean.csv
```

3. No rebuild needed - loaded automatically

---

## 🔮 Extending the System

### Add Agent 3 (Example: Emergency Response)

```python
# In src/agents/emergency_response.py
class EmergencyResponseAgent:
    def __init__(self):
        # DEPEND ON both agents
        self.safety_copilot = SafetyCopilot()  # Agent 1
        self.route_safety = RouteSafetyAgent()  # Agent 2
    
    def handle_emergency(self, location, emergency_type):
        # Get safety guidance from Agent 1
        guidance = self.safety_copilot.process_query(
            query=f"Emergency: {emergency_type}",
            user_context={'immediate_danger': True}
        )
        
        # Get route to nearest help from Agent 2
        route = self.route_safety.analyze_route(...)
        
        # Combine both
        return emergency_response
```

### Add More Data Sources

```python
# Add to route_safety.py
class RouteSafetyAgent:
    def __init__(self):
        self.crime_data = CrimeDataSource()
        self.lighting_data = LightingDataSource()  # NEW
        self.foot_traffic = FootTrafficDataSource()  # NEW
        self.safety_copilot = SafetyCopilot()
```

---

## ⚠️ Important Notes

### Archia Setup
1. Sign up at console.archia.app
2. Create/join workspace
3. Generate API token
4. Token must match workspace

### First Run
1. Will take ~2 minutes to build index
2. Sample data included for testing
3. Add real MU data for production

### Agent Dependency
- Don't instantiate Agent 2 without Agent 1
- Orchestrator handles this correctly
- Direct usage: `RouteSafetyAgent()` creates Agent 1 internally

---

## 📞 Emergency Contacts

**MU Safety Services:**
- 🚨 911 - Emergency
- 📞 573-882-7201 - MUPD
- 👥 573-884-9255 - Friend Walk  
- 🚗 573-882-1010 - Safe Ride
- 📞 573-882-3880 - Title IX

---

## ✅ Checklist

Before deploying:
- [ ] Archia token configured in `.env`
- [ ] MU safety documents added to `data/docs/`
- [ ] Crime data updated in `data/crime_data/`
- [ ] FAISS index built (`python src/vector_index.py`)
- [ ] Tests pass (`python example.py -a`)
- [ ] Emergency contacts verified in `src/config.py`

---

## 🎯 Summary

**What you built:**
- Two-agent system with clear dependency
- Agent 1: RAG-based safety guidance (MU docs)
- Agent 2: Crime-based route analysis (depends on Agent 1)
- Powered by Archia API
- Production-ready code

**Key Innovation:**
- Agent dependency architecture
- Combines document knowledge + data analysis
- Reusable safety guidance across agents
- Clear separation of concerns

**Ready for:**
- Mobile app integration
- Web API deployment
- Further agent additions
- Production use

---

**Built for MUIDSI Hackathon 2026 | Powered by Archia**

**Stay Safe, Tigers! 🐯**
