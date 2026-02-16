"""
Agent Orchestrator
Coordinates Safety Copilot and Route Safety agents
Shows clear dependency chain: Route Safety → Safety Copilot
"""
from typing import Dict, Literal
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from src.agents.safety_copilot import SafetyCopilot
from src.agents.route_safety import RouteSafetyAgent


class MizzouSafeOrchestrator:
    """
    Orchestrates multiple agents with clear dependencies
    
    Agent Flow:
    1. Safety Copilot (Agent 1) - General safety guidance from RAG
    2. Route Safety (Agent 2) - Route-specific analysis, DEPENDS ON Agent 1
    """
    
    def __init__(self):
        # Initialize Agent 1
        print("\n🔧 Initializing Agent 1: Safety Copilot...")
        self.safety_copilot = SafetyCopilot()
        
        # Initialize Agent 2 (which internally depends on Agent 1)
        print("🔧 Initializing Agent 2: Route Safety...")
        self.route_safety = RouteSafetyAgent()
        
        print("\n✅ MizzouSafe Orchestrator ready!")
        print("=" * 60)
        print("AGENT DEPENDENCY CHAIN:")
        print("  Agent 2 (Route Safety) → Agent 1 (Safety Copilot)")
        print("=" * 60 + "\n")
    
    def handle_query(self, query_type: Literal['safety', 'route'], **kwargs) -> Dict:
        """
        Handle user query by routing to appropriate agent(s)
        
        Args:
            query_type: 'safety' or 'route'
            **kwargs: Query-specific parameters
            
        Returns:
            Complete response from agent(s)
        """
        if query_type == 'safety':
            return self._handle_safety_query(**kwargs)
        elif query_type == 'route':
            return self._handle_route_query(**kwargs)
        else:
            raise ValueError(f"Unknown query type: {query_type}")
    
    def _handle_safety_query(self, query: str, user_context: Dict = None) -> Dict:
        """
        Handle general safety query using Agent 1
        
        Args:
            query: Safety question
            user_context: {'on_campus': bool, 'is_alone': bool, 'immediate_danger': bool}
            
        Returns:
            Response from Safety Copilot
        """
        print(f"\n🎯 Processing Safety Query: '{query}'")
        print("📍 Using: Agent 1 (Safety Copilot)\n")
        
        response = self.safety_copilot.process_query(query, user_context)
        
        print("✅ Safety query processed\n")
        return response
    
    def _handle_route_query(self, start_lat: float, start_lon: float,
                           end_lat: float, end_lon: float,
                           hour: int, user_context: Dict = None) -> Dict:
        """
        Handle route safety query using Agent 2 (which depends on Agent 1)
        
        Args:
            start_lat, start_lon: Starting coordinates
            end_lat, end_lon: Destination coordinates
            hour: Hour of travel (0-23)
            user_context: User context
            
        Returns:
            Response from Route Safety Agent (including Safety Copilot guidance)
        """
        print(f"\n🎯 Processing Route Query")
        print(f"📍 Route: ({start_lat}, {start_lon}) → ({end_lat}, {end_lon})")
        print(f"⏰ Time: {hour:02d}:00")
        print("\n🔗 AGENT DEPENDENCY CHAIN:")
        print("   Step 1: Agent 2 (Route Safety) analyzes route")
        print("   Step 2: Agent 2 consults Agent 1 (Safety Copilot) for guidance")
        print("   Step 3: Agent 2 combines both analyses\n")
        
        response = self.route_safety.analyze_route(
            start_lat, start_lon, end_lat, end_lon, hour, user_context
        )
        
        print("✅ Route query processed (with Safety Copilot consultation)\n")
        return response
    
    def demo_safety_query(self):
        """Demo: Show Agent 1 working independently"""
        print("\n" + "="*60)
        print("DEMO 1: Safety Copilot (Agent 1) - Independent Operation")
        print("="*60)
        
        query = "I see someone suspicious following me"
        context = {'is_alone': True, 'on_campus': True}
        
        response = self.handle_query(
            query_type='safety',
            query=query,
            user_context=context
        )
        
        print(f"Query: {query}")
        print(f"Urgency: {response['urgency']['level'].upper()}")
        print(f"\nPrimary Action: {response['primary_action']['name']}")
        print(f"Contact: {response['primary_action']['contact']}")
        
        print(f"\nSafety Checklist:")
        for i, tip in enumerate(response['safety_checklist'], 1):
            print(f"  {i}. {tip}")
        
        print(f"\nAI Guidance:")
        print(f"{response['llm_guidance'][:200]}...")
    
    def demo_route_query(self):
        """Demo: Show Agent 2 depending on Agent 1"""
        print("\n" + "="*60)
        print("DEMO 2: Route Safety (Agent 2) - Depends on Agent 1")
        print("="*60)
        
        # Memorial Union to Rec Center at night
        response = self.handle_query(
            query_type='route',
            start_lat=38.9404,
            start_lon=-92.3277,
            end_lat=38.9389,
            end_lon=-92.3301,
            hour=22,
            user_context={'is_alone': True}
        )
        
        print(f"\nRoute Risk Assessment:")
        print(f"  Overall Risk: {response['route_risk']['overall_risk']}")
        print(f"  Avg Risk Score: {response['route_risk']['avg_risk_score']}/10")
        
        print(f"\n📊 Route Analysis:")
        print(f"{response['route_analysis'][:300]}...")
        
        print(f"\n🔗 Safety Copilot's Input (Agent 1 → Agent 2):")
        copilot_guidance = response['safety_copilot_guidance']
        print(f"  Urgency: {copilot_guidance['urgency']['level']}")
        print(f"  Action: {copilot_guidance['primary_action']['name']}")
        
        print(f"\n💡 Recommendations:")
        for rec in response['recommendations'][:3]:
            print(f"  • {rec['title']}")
            print(f"    {rec['description']}")
    
    def demo_full_workflow(self):
        """Demo: Show complete workflow with both agents"""
        print("\n" + "="*70)
        print("COMPLETE WORKFLOW DEMONSTRATION")
        print("="*70)
        
        self.demo_safety_query()
        print("\n")
        self.demo_route_query()
        
        print("\n" + "="*70)
        print("✅ DEMONSTRATION COMPLETE")
        print("="*70)
        print("\nKey Takeaway:")
        print("  - Agent 1 (Safety Copilot) works independently for safety queries")
        print("  - Agent 2 (Route Safety) DEPENDS ON Agent 1 for comprehensive guidance")
        print("  - Both agents use Archia for LLM access")
        print("  - Clear dependency chain ensures consistent safety recommendations")
        print()
