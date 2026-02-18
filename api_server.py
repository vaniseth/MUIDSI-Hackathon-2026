"""
TigerTown API Server
======================
FastAPI wrapper for the TigerTown multi-agent backend.
Exposes three endpoints for the Streamlit UI to call.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import sys
from pathlib import Path

# Add the backend to the path
sys.path.append(str(Path(__file__).parent))
from src.orchestrator import TigerTownOrchestrator
from src.route_planner import RoutePlanner

app = FastAPI(title="TigerTown API", version="1.0.0")

# Enable CORS for Streamlit Cloud
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the backend once on startup
print("🚀 Initializing TigerTown backend...")
orchestrator = TigerTownOrchestrator()
route_planner = RoutePlanner()
print("✅ TigerTown API ready!\n")


# ── Request/Response Models ───────────────────────────────────────────────────

class RouteCoordinates(BaseModel):
    lats: List[float]
    lons: List[float]


class AnalyzeRouteRequest(BaseModel):
    fast_route: RouteCoordinates
    safe_route: RouteCoordinates
    start: str
    end: str
    hour: int
    day_of_week: Optional[str] = None


class EnrichStepRequest(BaseModel):
    instruction: str
    lat: float
    lon: float
    hour: int
    route_id: str
    step_index: int


class ChatRequest(BaseModel):
    message: str
    session_id: str
    context: Dict


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/")
def root():
    return {
        "name": "TigerTown API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": ["/analyze-route", "/enrich-step", "/chat"]
    }


@app.post("/analyze-route")
def analyze_route(req: AnalyzeRouteRequest):
    """
    Compare two routes and return risk scores + recommendation.
    
    The Route Safety Agent analyzes both routes using crime data,
    then consults the Safety Copilot for contextual guidance.
    """
    try:
        # Analyze the faster route
        fast_response = orchestrator.handle_query(
            query_type='route',
            start_lat=req.fast_route.lats[0],
            start_lon=req.fast_route.lons[0],
            end_lat=req.fast_route.lats[-1],
            end_lon=req.fast_route.lons[-1],
            hour=req.hour,
            user_context={}
        )
        
        # Analyze the safer route
        safe_response = orchestrator.handle_query(
            query_type='route',
            start_lat=req.safe_route.lats[0],
            start_lon=req.safe_route.lons[0],
            end_lat=req.safe_route.lats[-1],
            end_lon=req.safe_route.lons[-1],
            hour=req.hour,
            user_context={}
        )
        
        # Extract risk data
        fast_risk = fast_response['route_risk']['overall_risk']
        fast_score = fast_response['route_risk']['avg_risk_score']
        safe_risk = safe_response['route_risk']['overall_risk']
        safe_score = safe_response['route_risk']['avg_risk_score']
        
        # Generate pre-trip brief and recommendation
        if safe_score < fast_score:
            recommendation = "safer"
            time_saved = 0  # UI calculates from durations
            risk_delta = fast_score - safe_score
            brief = (
                f"At {req.hour:02d}:00, the faster route scores {fast_score:.1f}/10 "
                f"while the safer route scores {safe_score:.1f}/10 — a {risk_delta:.1f} "
                f"point improvement. "
                f"{safe_response['route_analysis'][:150]}..."
            )
        else:
            recommendation = "fastest"
            time_saved = 0
            brief = (
                f"Both routes have similar safety profiles at {req.hour:02d}:00. "
                f"The fastest route is recommended. "
                f"{fast_response['route_analysis'][:150]}..."
            )
        
        return {
            "fast_risk": fast_risk,
            "fast_score": fast_score,
            "fast_explanation": fast_response['route_analysis'][:200],
            "safe_risk": safe_risk,
            "safe_score": safe_score,
            "safe_explanation": safe_response['route_analysis'][:200],
            "recommendation": recommendation,
            "pre_trip_brief": brief,
            "time_saved_fastest": time_saved,
            # Pass through the full route data for step enrichment
            "_fast_route_full": fast_response.get('route', {}),
            "_safe_route_full": safe_response.get('route', {}),
        }
        
    except Exception as e:
        print(f"❌ Error in /analyze-route: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/enrich-step")
def enrich_step(req: EnrichStepRequest):
    """
    Enrich a single navigation step with safety context.
    
    Uses the Risk Scorer to check for nearby crime incidents,
    then adds contextual warnings or safety notes.
    """
    try:
        from src.risk_scorer import RiskScorer
        
        scorer = RiskScorer()
        detail = scorer.get_risk_detail(req.lat, req.lon, req.hour)
        
        # Build enriched instruction
        base_instruction = req.instruction
        enriched = base_instruction
        warning = None
        safety_note = None
        
        # Add safety context if risk is elevated
        if detail['risk_level'] in ('Medium', 'High'):
            pattern = detail.get('pattern_summary', '')
            if pattern:
                # Add inline context to the instruction
                enriched = f"{base_instruction} — {pattern}"
            
            # Generate a warning if incident count is significant
            if detail['incident_count'] >= 3:
                incidents = detail['incident_count']
                category = detail.get('top_category', 'incidents')
                warning = (
                    f"{incidents} {category} reported in this area "
                    f"in the last 90 days, mostly at night"
                )
        
        # Add positive safety notes if available
        if detail['risk_level'] == 'Low' and 'well-lit' in detail.get('notes', '').lower():
            safety_note = "Well-lit area with good visibility"
        
        return {
            "enriched_instruction": enriched,
            "warning": warning,
            "safety_note": safety_note,
            "risk_level": detail['risk_level'],
            "risk_score": detail['risk_score'],
        }
        
    except Exception as e:
        print(f"❌ Error in /enrich-step: {e}")
        # Graceful degradation — return the original instruction
        return {
            "enriched_instruction": req.instruction,
            "warning": None,
            "safety_note": None,
            "risk_level": "Unknown",
            "risk_score": 0.0,
        }


@app.post("/chat")
def chat(req: ChatRequest):
    """
    Chat with the Safety Copilot.
    
    The Safety Copilot uses RAG to answer questions about campus safety,
    policies, and emergency resources, grounded in MU safety documents.
    """
    try:
        # Build user context from the chat context
        user_context = {
            'on_campus': True,
            'is_alone': req.context.get('active_route') is not None,
        }
        
        # Add location context to the query if available
        enhanced_query = req.message
        if req.context.get('location'):
            enhanced_query = (
                f"I'm near {req.context['location']} heading to {req.context.get('destination', 'campus')}. "
                f"{req.message}"
            )
        
        # Call Safety Copilot
        response = orchestrator.handle_query(
            query_type='safety',
            query=enhanced_query,
            user_context=user_context
        )
        
        # Extract the reply and sources
        reply = response.get('llm_guidance', "I'm here to help with campus safety questions.")
        sources = response.get('sources', [])
        
        # Build suggested actions from the primary action
        suggested_actions = []
        if response.get('primary_action'):
            action = response['primary_action']
            suggested_actions.append(f"{action['name']}: {action.get('contact', '')}")
        
        return {
            "reply": reply,
            "sources": sources,
            "suggested_actions": suggested_actions,
            "urgency_level": response.get('urgency', {}).get('level', 'medium'),
        }
        
    except Exception as e:
        print(f"❌ Error in /chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "healthy", "backend": "operational"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
