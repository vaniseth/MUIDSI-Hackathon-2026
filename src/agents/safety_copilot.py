"""
Agent 1: Safety Copilot
RAG-powered safety guidance using MU safety documents
"""
from typing import Dict, List
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from src.config import EMERGENCY_KEYWORDS, HIGH_PRIORITY_KEYWORDS, EMERGENCY_CONTACTS
from src.retriever import DocumentRetriever
from src.archia_client import ArchiaClient


SAFETY_COPILOT_SYSTEM_PROMPT = """You are MizzouSafe Safety Copilot, an AI safety assistant for University of Missouri students.

Your role:
1. Assess safety situations
2. Provide immediate, actionable guidance
3. Cite relevant MU safety resources
4. Recommend appropriate emergency contacts

Guidelines:
- Be empathetic, clear, and concise
- Prioritize student safety above all
- Provide specific actions to take NOW
- Cite sources from MU safety documents when available
- If serious (danger, assault, threats, weapons), ALWAYS recommend calling 911 first

Response format:
1. **Immediate Action** - What to do right now
2. **Why** - Brief explanation (1-2 sentences)
3. **Safety Checklist** - 3-4 quick tips
4. **Additional Resources** - Other contacts/resources

CRITICAL: If query mentions danger, assault, threats, or weapons → recommend calling 911 first.
"""


class SafetyCopilot:
    """
    Agent 1: Safety Copilot
    Uses RAG to provide safety guidance based on MU documents
    """
    
    def __init__(self):
        self.client = ArchiaClient()
        self.retriever = DocumentRetriever()
        self.emergency_keywords = [kw.lower() for kw in EMERGENCY_KEYWORDS]
        self.high_priority_keywords = [kw.lower() for kw in HIGH_PRIORITY_KEYWORDS]
        print("✅ Safety Copilot initialized")
    
    def analyze_urgency(self, query: str, context: Dict = None) -> Dict:
        """Analyze urgency level"""
        query_lower = query.lower()
        
        detected_emergency = [kw for kw in self.emergency_keywords if kw in query_lower]
        detected_high = [kw for kw in self.high_priority_keywords if kw in query_lower]
        
        immediate_danger = context.get('immediate_danger', False) if context else False
        is_alone = context.get('is_alone', False) if context else False
        
        if detected_emergency or immediate_danger:
            return {'level': 'emergency', 'keywords': detected_emergency, 'action': 'call_911'}
        elif detected_high or is_alone:
            return {'level': 'high', 'keywords': detected_high, 'action': 'call_mupd'}
        elif is_alone:
            return {'level': 'medium', 'keywords': [], 'action': 'friend_walk'}
        else:
            return {'level': 'low', 'keywords': [], 'action': 'report_online'}
    
    def get_recommended_action(self, urgency: Dict) -> Dict:
        """Get primary recommended action"""
        actions = {
            'call_911': {
                'name': '🚨 CALL 911',
                'contact': '911',
                'description': 'Emergency services - immediate danger'
            },
            'call_mupd': {
                'name': '📞 Call MUPD',
                'contact': '573-882-7201',
                'description': 'Campus police for safety concerns'
            },
            'friend_walk': {
                'name': '👥 Request Friend Walk',
                'contact': '573-884-9255',
                'description': 'Walking escort service (7 PM - 3 AM)'
            },
            'report_online': {
                'name': '📝 Report Online',
                'contact': 'https://mupolice.missouri.edu/report-crime/',
                'description': 'Submit non-emergency crime report'
            }
        }
        return actions.get(urgency['action'], actions['report_online'])

    def get_relevant_links(self, query: str, urgency: Dict) -> List[Dict]:
        """
        Return relevant official MU reporting links based on query context
        """
        from src.config import MU_REPORTING_LINKS
        query_lower = query.lower()
        links = []

        # Always include MUPD online report for crimes
        if any(kw in query_lower for kw in ['crime', 'theft', 'vandal', 'report', 'stolen', 'broke']):
            links.append(MU_REPORTING_LINKS['online_crime_report'])

        # Sexual assault, harassment, stalking, discrimination → OIE + RSVP
        if any(kw in query_lower for kw in ['assault', 'harass', 'stalk', 'rape', 'discriminat', 'title ix', 'violence', 'relationship']):
            links.append(MU_REPORTING_LINKS['oie_report'])
            links.append(MU_REPORTING_LINKS['rsvp_center'])

        # Anonymous reporting
        if any(kw in query_lower for kw in ['anonymous', 'anonymous', 'don\'t want my name', 'silent']):
            links.append(MU_REPORTING_LINKS['silent_witness'])

        # Concerned about a student
        if any(kw in query_lower for kw in ['student', 'friend', 'concern', 'distress', 'mental', 'suicid', 'self-harm']):
            links.append(MU_REPORTING_LINKS['student_at_risk'])

        # CSA reporting
        if any(kw in query_lower for kw in ['csa', 'campus security authority', 'clery']):
            links.append(MU_REPORTING_LINKS['csa_report'])

        # Emergency level → add MU Alert signup
        if urgency['level'] in ['emergency', 'high']:
            links.append(MU_REPORTING_LINKS['mu_alert'])

        # Default: always add online crime report if no other links matched
        if not links:
            links.append(MU_REPORTING_LINKS['online_crime_report'])

        # Deduplicate
        seen = set()
        unique = []
        for link in links:
            if link['url'] not in seen:
                seen.add(link['url'])
                unique.append(link)

        return unique[:3]  # Return top 3 most relevant
    
    def get_safety_checklist(self, urgency: Dict) -> List[str]:
        """Generate contextual safety checklist"""
        level = urgency['level']
        
        if level == 'emergency':
            return [
                "Get to a safe location immediately",
                "Call 911 if in immediate danger",
                "Stay on the line with dispatcher",
                "Note suspect description if safe"
            ]
        elif level == 'high':
            return [
                "Move to well-lit, populated area",
                "Stay aware of surroundings",
                "Keep phone accessible",
                "Trust your instincts"
            ]
        else:
            return [
                "Note details while fresh",
                "Save any evidence (texts, photos)",
                "Walk with friends when possible",
                "Report to MUPD within 24 hours"
            ]
    
    def process_query(self, query: str, user_context: Dict = None) -> Dict:
        """
        Main processing pipeline
        
        Args:
            query: User's safety question
            user_context: {'on_campus': bool, 'is_alone': bool, 'immediate_danger': bool}
            
        Returns:
            Complete response with actions and guidance
        """
        # 1. Analyze urgency
        urgency = self.analyze_urgency(query, user_context)
        
        # 2. Retrieve relevant documents
        results, context_str = self.retriever.retrieve_with_context(query, top_k=3)
        sources = self.retriever.get_sources(results)
        
        # 3. Get recommended action
        primary_action = self.get_recommended_action(urgency)
        
        # 4. Generate safety checklist
        safety_checklist = self.get_safety_checklist(urgency)
        
        # 5. Get relevant official MU links
        relevant_links = self.get_relevant_links(query, urgency)
        
        # 6. Create prompt for LLM
        prompt = self._create_prompt(query, context_str, user_context)
        
        # 7. Get LLM response
        llm_response = self.client.chat(
            system_prompt=SAFETY_COPILOT_SYSTEM_PROMPT,
            user_message=prompt,
            temperature=0.3
        )
        
        # 8. Compile response
        return {
            'agent': 'safety_copilot',
            'urgency': urgency,
            'primary_action': primary_action,
            'safety_checklist': safety_checklist,
            'relevant_links': relevant_links,
            'llm_guidance': llm_response,
            'sources': sources,
            'retrieved_docs': results
        }
    
    def _create_prompt(self, query: str, context_str: str, user_context: Dict = None) -> str:
        """Create prompt for LLM"""
        parts = []
        
        if user_context:
            info = []
            if user_context.get('on_campus'):
                info.append("I am on campus")
            if user_context.get('is_alone'):
                info.append("I am alone")
            if user_context.get('immediate_danger'):
                info.append("⚠️ I feel I'm in immediate danger")
            
            if info:
                parts.append("**Situation:** " + ", ".join(info))
        
        parts.append(f"**What's happening:** {query}")
        
        if context_str:
            parts.append(f"\n**Relevant MU Safety Information:**\n{context_str}")
        
        parts.append("\n**Provide:**")
        parts.append("1. ONE most important action right now")
        parts.append("2. Why this action (1-2 sentences)")
        parts.append("3. Safety checklist (3-4 tips)")
        parts.append("4. Other resources/contacts")
        
        return "\n".join(parts)
