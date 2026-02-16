"""
MizzouSafe Integrated System - Examples
Demonstrates Agent 1 and Agent 2 working together
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from src.orchestrator import MizzouSafeOrchestrator


def example_1_safety_query():
    """Example 1: General safety query (Agent 1 only)"""
    print("\n" + "="*70)
    print("EXAMPLE 1: General Safety Query")
    print("Uses: Agent 1 (Safety Copilot) - RAG-based")
    print("="*70)
    
    orchestrator = MizzouSafeOrchestrator()
    
    # Query
    query = "What should I do if I see suspicious activity on campus?"
    context = {'on_campus': True}
    
    print(f"\n📝 Query: {query}")
    print(f"📍 Context: {context}\n")
    
    response = orchestrator.handle_query(
        query_type='safety',
        query=query,
        user_context=context
    )
    
    # Display results
    print("="*70)
    print("RESPONSE FROM AGENT 1 (Safety Copilot)")
    print("="*70)
    
    print(f"\n🎯 Urgency Level: {response['urgency']['level'].upper()}")
    
    print(f"\n🚨 Primary Action:")
    print(f"   {response['primary_action']['name']}")
    print(f"   Contact: {response['primary_action']['contact']}")
    print(f"   {response['primary_action']['description']}")
    
    print(f"\n📋 AI Guidance:")
    print(f"{response['llm_guidance']}")
    
    print(f"\n✅ Safety Checklist:")
    for i, tip in enumerate(response['safety_checklist'], 1):
        print(f"   {i}. {tip}")
    
    if response['sources']:
        print(f"\n📖 Sources:")
        for source in response['sources']:
            print(f"   - {source}")


def example_2_route_query():
    """Example 2: Route safety query (Agent 2 depends on Agent 1)"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Route Safety Query")
    print("Uses: Agent 2 (Route Safety) → Consults Agent 1 (Safety Copilot)")
    print("="*70)
    
    orchestrator = MizzouSafeOrchestrator()
    
    # Route: Memorial Union to Rec Center at night
    print(f"\n📍 Route: Memorial Union → Rec Center")
    print(f"⏰ Time: 22:00 (10 PM)")
    print(f"👤 Context: Traveling alone\n")
    
    response = orchestrator.handle_query(
        query_type='route',
        start_lat=38.9404,  # Memorial Union
        start_lon=-92.3277,
        end_lat=38.9389,    # Rec Center
        end_lon=-92.3301,
        hour=22,
        user_context={'is_alone': True, 'on_campus': True}
    )
    
    # Display results
    print("="*70)
    print("RESPONSE FROM AGENT 2 (Route Safety)")
    print("="*70)
    
    route_risk = response['route_risk']
    print(f"\n📊 Route Risk Assessment:")
    print(f"   Overall Risk: {route_risk['overall_risk']}")
    print(f"   Average Risk Score: {route_risk['avg_risk_score']}/10")
    
    print(f"\n   Starting Point:")
    print(f"     Risk: {route_risk['start']['risk_level']} ({route_risk['start']['risk_score']}/10)")
    print(f"     Historical Incidents: {route_risk['start']['incidents']}")
    
    print(f"\n   Destination:")
    print(f"     Risk: {route_risk['end']['risk_level']} ({route_risk['end']['risk_score']}/10)")
    print(f"     Historical Incidents: {route_risk['end']['incidents']}")
    
    print(f"\n🤖 Route-Specific Analysis:")
    print(f"{response['route_analysis']}")
    
    print(f"\n🔗 Input from Agent 1 (Safety Copilot):")
    copilot = response['safety_copilot_guidance']
    print(f"   Urgency: {copilot['urgency']['level']}")
    print(f"   Recommended Action: {copilot['primary_action']['name']}")
    print(f"   Safety Tips:")
    for i, tip in enumerate(copilot['safety_checklist'], 1):
        print(f"     {i}. {tip}")
    
    print(f"\n💡 Recommendations (Combined from both agents):")
    for i, rec in enumerate(response['recommendations'][:3], 1):
        print(f"   {i}. {rec['title']}")
        print(f"      {rec['description']}")


def example_3_emergency():
    """Example 3: Emergency situation"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Emergency Situation")
    print("="*70)
    
    orchestrator = MizzouSafeOrchestrator()
    
    query = "Someone is following me and I feel threatened"
    context = {'immediate_danger': True, 'is_alone': True, 'on_campus': True}
    
    print(f"\n📝 Query: {query}")
    print(f"⚠️  Context: IMMEDIATE DANGER\n")
    
    response = orchestrator.handle_query(
        query_type='safety',
        query=query,
        user_context=context
    )
    
    print("="*70)
    print("⚠️  EMERGENCY RESPONSE")
    print("="*70)
    
    print(f"\n🚨 URGENCY: {response['urgency']['level'].upper()}")
    
    print(f"\n🚨 IMMEDIATE ACTION:")
    print(f"   {response['primary_action']['name']}")
    print(f"   {response['primary_action']['contact']}")
    print(f"   {response['primary_action']['description']}")
    
    print(f"\n⚠️  SAFETY CHECKLIST:")
    for i, tip in enumerate(response['safety_checklist'], 1):
        print(f"   {i}. {tip}")


def demo_agent_dependency():
    """Demonstrate clear agent dependency"""
    print("\n" + "="*70)
    print("AGENT DEPENDENCY DEMONSTRATION")
    print("="*70)
    
    print("\n🔗 Agent Dependency Chain:")
    print("   1. Agent 1 (Safety Copilot) - Independent RAG agent")
    print("      - Uses MU safety documents")
    print("      - Provides general safety guidance")
    print("      - Can work standalone")
    
    print("\n   2. Agent 2 (Route Safety) - Depends on Agent 1")
    print("      - Uses crime data for route analysis")
    print("      - CONSULTS Agent 1 for safety recommendations")
    print("      - Combines both data sources")
    
    print("\n📊 How it works:")
    print("   Step 1: User asks for route safety")
    print("   Step 2: Agent 2 analyzes route using crime data")
    print("   Step 3: Agent 2 queries Agent 1 for safety guidance")
    print("   Step 4: Agent 1 retrieves relevant MU safety docs")
    print("   Step 5: Agent 1 provides recommendations")
    print("   Step 6: Agent 2 combines route data + Agent 1 guidance")
    print("   Step 7: User gets comprehensive answer")
    
    orchestrator = MizzouSafeOrchestrator()
    orchestrator.demo_full_workflow()


def main():
    """Run all examples"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MizzouSafe Integrated System Examples")
    parser.add_argument('-1', '--example1', action='store_true', help='Safety query example')
    parser.add_argument('-2', '--example2', action='store_true', help='Route query example')
    parser.add_argument('-3', '--example3', action='store_true', help='Emergency example')
    parser.add_argument('-d', '--dependency', action='store_true', help='Show agent dependency')
    parser.add_argument('-a', '--all', action='store_true', help='Run all examples')
    
    args = parser.parse_args()
    
    if args.example1 or args.all:
        example_1_safety_query()
    
    if args.example2 or args.all:
        example_2_route_query()
    
    if args.example3 or args.all:
        example_3_emergency()
    
    if args.dependency or args.all:
        demo_agent_dependency()
    
    if not any(vars(args).values()):
        print("\nUsage:")
        print("  python example.py -1         # Safety query example")
        print("  python example.py -2         # Route query example")
        print("  python example.py -3         # Emergency example")
        print("  python example.py -d         # Show agent dependency")
        print("  python example.py -a         # Run all examples")
        print("\nOr import and use:")
        print("  from src.orchestrator import MizzouSafeOrchestrator")
        print("  orchestrator = MizzouSafeOrchestrator()")
        print("  response = orchestrator.handle_query(...)")


if __name__ == "__main__":
    main()
