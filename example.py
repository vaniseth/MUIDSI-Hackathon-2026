"""
TigerTown Integrated System - Examples
Demonstrates Agent 1 and Agent 2 working together
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from src.orchestrator import TigerTownOrchestrator


def example_1_safety_query():
    """Example 1: General safety query (Agent 1 only)"""
    print("\n" + "="*70)
    print("EXAMPLE 1: General Safety Query")
    print("Uses: Agent 1 (Safety Copilot) - RAG-based")
    print("="*70)

    orchestrator = TigerTownOrchestrator()
    query = "What should I do if I see suspicious activity on campus?"
    context = {'on_campus': True}

    print(f"\n📝 Query: {query}")
    print(f"📍 Context: {context}\n")

    response = orchestrator.handle_query(query_type='safety', query=query, user_context=context)

    print("="*70)
    print("RESPONSE FROM AGENT 1 (Safety Copilot)")
    print("="*70)
    print(f"\n🎯 Urgency Level: {response['urgency']['level'].upper()}")
    print(f"\n🚨 Primary Action:")
    print(f"   {response['primary_action']['name']}")
    print(f"   Contact: {response['primary_action']['contact']}")
    print(f"   {response['primary_action']['description']}")
    print(f"\n📋 AI Guidance:\n{response['llm_guidance']}")
    print(f"\n✅ Safety Checklist:")
    for i, tip in enumerate(response['safety_checklist'], 1):
        print(f"   {i}. {tip}")
    if response.get('relevant_links'):
        print(f"\n🔗 Relevant Links:")
        for link in response['relevant_links']:
            print(f"   - {link['name']}: {link['url']}")
    if response['sources']:
        print(f"\n📖 Sources:")
        for source in response['sources']:
            print(f"   - {source}")


def example_2_route_query():
    """Example 2: Route safety query (Agent 2 depends on Agent 1)"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Route Safety Query")
    print("Uses: Agent 2 (Route Safety) -> Consults Agent 1 (Safety Copilot)")
    print("="*70)

    orchestrator = TigerTownOrchestrator()

    print(f"\n📍 Route: Memorial Union -> Rec Center")
    print(f"⏰ Time: 22:00 (10 PM)")
    print(f"👤 Context: Traveling alone\n")

    response = orchestrator.handle_query(
        query_type='route',
        start_lat=38.9404, start_lon=-92.3277,
        end_lat=38.9389,   end_lon=-92.3301,
        hour=22,
        user_context={'is_alone': True, 'on_campus': True}
    )

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
    print(f"\n🤖 Route-Specific Analysis:\n{response['route_analysis']}")

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

    orchestrator = TigerTownOrchestrator()
    query = "Someone is following me and I feel threatened"
    context = {'immediate_danger': True, 'is_alone': True, 'on_campus': True}

    print(f"\n📝 Query: {query}")
    print(f"⚠️  Context: IMMEDIATE DANGER\n")

    response = orchestrator.handle_query(query_type='safety', query=query, user_context=context)

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
    if response.get('relevant_links'):
        print(f"\n🔗 Report Here:")
        for link in response['relevant_links']:
            print(f"   - {link['name']}: {link['url']}")


def example_4_conversation_flow():
    """
    Example 4: Multi-turn location-aware conversation
    Turn 1: User reports concern -> Agent 1 responds + asks for location
    Turn 2: User gives location -> Agent 2 provides safe route
    """
    print("\n" + "="*70)
    print("EXAMPLE 4: Location-Aware Conversation Flow")
    print("Turn 1: Safety concern  ->  Turn 2: Location  ->  Safe Route")
    print("="*70)

    from src.conversation_handler import ConversationHandler

    orchestrator = TigerTownOrchestrator()
    handler = ConversationHandler(orchestrator)

    # Turn 1: User reports suspicious activity
    user_msg_1 = "Someone is following me and I feel unsafe"
    print(f"\n👤 User: '{user_msg_1}'")
    print("-" * 50)

    response1 = handler.handle(
        user_msg_1,
        user_context={'is_alone': True, 'on_campus': True}
    )
    print(response1['message'])

    # Turn 2: User gives their location
    if response1.get('awaiting_location'):
        user_msg_2 = "I'm near Ellis Library"
        print(f"\n👤 User: '{user_msg_2}'")
        print("-" * 50)

        response2 = handler.handle(user_msg_2)
        print(response2['message'])

        if response2.get('destination'):
            dest = response2['destination']
            print(f"\n✅ Safe destination: {dest['name']}")
            print(f"   Distance: {dest['distance_miles']} miles")
            print(f"   Walk time: ~{dest['walk_minutes']} min")
    else:
        print("\nℹ️  Location prompt not triggered for this query.")


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
    print("\n   3. ConversationHandler - Ties it together")
    print("      - Detects safety concerns")
    print("      - Asks for user location")
    print("      - Routes to nearest safe destination")

    orchestrator = TigerTownOrchestrator()
    orchestrator.demo_full_workflow()

def example_5_full_route_briefing():
    """
    Example 5: Features 1+2+3+5 combined
    - Rich risk breakdown per step (Feature 1)
    - Real OSRM walking steps (Feature 2)
    - Pattern-aware AI narrative (Feature 3)
    - Pre-trip briefing (Feature 5)
    """
    print("\n" + "="*70)
    print("EXAMPLE 5: Full Route Briefing (Features 1+2+3+5)")
    print("="*70)

    from src.orchestrator import TigerTownOrchestrator
    from src.briefing_generator import BriefingGenerator
    from datetime import datetime

    orchestrator = TigerTownOrchestrator()
    briefer = BriefingGenerator()

    hour = datetime.now().hour

    print(f"\n📍 Route: Memorial Union → Rec Center at {hour:02d}:00")
    print(f"👤 Traveling alone, Friday night\n")

    response = orchestrator.handle_query(
        query_type='route',
        start_lat=38.9404, start_lon=-92.3277,
        end_lat=38.9389,   end_lon=-92.3301,
        hour=hour,
        user_context={'is_alone': True, 'on_campus': True, 'day_of_week': 'Friday'}
    )

    # Feature 5: Pre-trip briefing
    print("=" * 60)
    print("📋 PRE-TRIP BRIEFING")
    print("=" * 60)
    briefing = briefer.generate(
        response,
        hour=hour,
        user_context={'is_alone': True, 'day_of_week': 'Friday'}
    )
    print(briefing)

    # Feature 2: Step-by-step narration
    print("\n" + "=" * 60)
    print("🗺️  STEP-BY-STEP DIRECTIONS WITH SAFETY CONTEXT")
    print("=" * 60)
    narration = briefer.format_step_narration(response)
    print(narration)

    # Feature 1: Hotspot breakdown
    hotspot = response.get('hotspot_step')
    if hotspot and hotspot['risk_detail']['risk_score'] > 0:
        rd = hotspot['risk_detail']
        print(f"\n⚠️  HOTSPOT (Step {hotspot['step']} — {hotspot.get('road', 'unnamed')}):")
        print(f"   Risk: {rd['risk_level']} | Score: {rd['risk_score']}/10")
        print(f"   Categories: {rd['category_breakdown']}")
        print(f"   Night incidents: {int(rd['night_ratio']*100)}% | Peak hour: {rd['peak_hour']}")
        print(f"   {rd['pattern_summary']}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-1', action='store_true')
    parser.add_argument('-2', action='store_true')
    parser.add_argument('-3', action='store_true')
    parser.add_argument('-4', action='store_true')
    parser.add_argument('-5', action='store_true')
    parser.add_argument('-a', '--all', action='store_true')
    args = parser.parse_args()

    if getattr(args, '1') or args.all: example_1_safety_query()
    if getattr(args, '2') or args.all: example_2_route_query()
    if getattr(args, '3') or args.all: example_3_emergency()
    if getattr(args, '4') or args.all: example_4_conversation_flow()
    if getattr(args, '5') or args.all: example_5_full_route_briefing()

    if not any([getattr(args, '1'), getattr(args, '2'), getattr(args, '3'),
                getattr(args, '4'), getattr(args, '5'), args.all]):
        print("\nUsage: python example.py [-1] [-2] [-3] [-4] [-5] [-a]")
        print("  -5   Full route briefing (Features 1+2+3+5)  ← NEW")