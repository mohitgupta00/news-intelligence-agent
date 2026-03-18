"""
LLM-First Router: Intelligent dispatcher for NewsIQ system.
Decides whether to handle queries directly or delegate to graph pipeline.
"""

import json
from groq import Groq
from pydantic import BaseModel
from typing import Literal, Optional
from config import GROQ_API_KEY, GROQ_MODEL

class RouterDecision(BaseModel):
    action: Literal["direct_response", "delegate_to_graph"]
    response: Optional[str] = None
    graph_query: Optional[str] = None
    reasoning: str

class IntelligentRouter:
    def __init__(self):
        self.groq_client = Groq(api_key=GROQ_API_KEY)
    
    def route_query(self, user_query: str, conversation_memory: dict = None) -> RouterDecision:
        """Main routing logic - decides how to handle the query."""
        
        memory_context = self._format_memory(conversation_memory or {})
        
        prompt = f"""You are NewsIQ Router - a specialized news intelligence reporter.

CORE FUNCTION: Route queries to news research OR decline non-news requests.

STRICT RULES:
✅ DELEGATE TO RESEARCH (delegate_to_graph):
- Specific news topics: "Tesla earnings", "Ukraine conflict updates"
- Named entities + news context: "Biden policy changes", "Apple stock news"
- Current events: "election results", "market crash", "breaking news about X"

✅ HANDLE DIRECTLY (direct_response):
- System queries: "what can you do", "who are you", "your capabilities"
- Decline ALL non-news: math, recipes, creative writing, general knowledge, health advice
- Clarify vague queries: "what happened", "latest news" (without specific topic)

DO NOT:
- Route general knowledge questions to research
- Handle math, recipes, creative tasks, or personal advice
- Accept vague queries without specific news topics
- Provide opinions or speculation

AMBIGUITY RULE: If query lacks specific news topic/entity, ask for clarification.

EXAMPLES:
"how to make pizza?" → direct_response (decline: recipe)
"Tesla stock news" → delegate_to_graph (specific news topic)
"what happened yesterday?" → direct_response (clarify: too vague)
"who are you?" → direct_response (system query)

{memory_context}

User Query: "{user_query}"

IMPORTANT: If there's previous conversation context and the query references it ("this topic", "on this", "reactions", "what about"), ALWAYS delegate to graph for fresh analysis.

Respond with valid JSON:
{{
    "action": "direct_response" | "delegate_to_graph",
    "response": "your response text" | null,
    "graph_query": "reformulated query" | null,
    "reasoning": "brief explanation"
}}"""

        try:
            response = self.groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            # Extract JSON from response
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            json_str = content[json_start:json_end]
            
            decision_data = json.loads(json_str)
            return RouterDecision(**decision_data)
            
        except Exception as e:
            # Enhanced fallback: intelligent rule-based classification
            return self._fallback_routing(user_query, str(e))
    
    def _fallback_routing(self, query: str, error: str) -> RouterDecision:
        """Intelligent rule-based fallback when LLM routing fails."""
        query_lower = query.lower().strip()
        
        # Out-of-scope patterns
        out_of_scope_patterns = [
            'recipe', 'cook', 'bake', 'ingredient', 'food preparation',
            'math', 'calculate', 'solve', 'equation', 'arithmetic',
            'poem', 'story', 'creative writing', 'fiction', 'lyrics',
            'personal advice', 'relationship', 'dating', 'health advice',
            'how to', 'tutorial', 'guide', 'instructions', 'diy'
        ]
        
        # System capability patterns  
        capability_patterns = [
            'what can you do', 'what are you', 'your purpose', 'your role',
            'capabilities', 'help with', 'supposed to do', 'designed for'
        ]
        
        # News patterns
        news_patterns = [
            'news', 'latest', 'update', 'happening', 'current', 'recent',
            'politics', 'political', 'election', 'government', 'policy',
            'war', 'conflict', 'crisis', 'economy', 'economic', 'market',
            'business', 'company', 'industry', 'technology', 'tech'
        ]
        
        # Check patterns in order of specificity
        if any(pattern in query_lower for pattern in capability_patterns):
            return RouterDecision(
                action="direct_response",
                response=None,  # Will trigger system capabilities
                reasoning="System capability question detected (fallback)"
            )
        
        if any(pattern in query_lower for pattern in out_of_scope_patterns):
            return RouterDecision(
                action="direct_response", 
                response="I'm a news intelligence reporter, focused on news analysis and current events. I can't help with that topic, but I'd be happy to discuss any recent news or developments!",
                reasoning="Out-of-scope query detected (fallback)"
            )
        
        if any(pattern in query_lower for pattern in news_patterns):
            return RouterDecision(
                action="delegate_to_graph",
                graph_query=query,
                reasoning="News-related query detected (fallback)"
            )
        
        # Default: delegate to graph for safety (but indicate uncertainty)
        return RouterDecision(
            action="delegate_to_graph",
            graph_query=query,
            reasoning=f"Uncertain classification, defaulting to graph. Router error: {error}"
        )
    
    def _format_memory(self, memory: dict) -> str:
        """Format conversation memory for prompt context."""
        if not memory:
            return "Memory: No previous conversation context."
        
        parts = []
        if memory.get("last_entities"):
            parts.append(f"Previous entities: {', '.join(memory['last_entities'])}")
        if memory.get("last_topic"):
            parts.append(f"Last topic: {memory['last_topic']}")
        if memory.get("conversation_context"):
            parts.append(f"Context: {memory['conversation_context']}")
            
        return f"Memory: {' | '.join(parts)}" if parts else "Memory: No context available."
    
    def get_system_capabilities(self) -> str:
        """Standard capability response for direct handling."""
        return """Hi! I'm NewsIQ, your AI news intelligence assistant. Here's what I can help you with:

📰 **News Analysis**
• Summarize latest news on any topic
• Analyze sentiment and public opinion  
• Create timelines of events
• Compare entities (companies, countries, leaders)
• Extract key information and entities

🧠 **Smart Features**  
• Multi-source news aggregation (NewsAPI, GNews, NewsData)
• Context-aware follow-up questions
• Real-time search with semantic caching
• Cross-conversation memory

📋 **Example Queries**
• "Latest updates on climate summit"
• "Compare Apple vs Google AI strategies" 
• "Timeline of recent banking crisis"
• "Public sentiment on new policy"
• "What's happening with Tesla stock?" (I'll find news, not give investment advice)

❌ **What I Don't Do**
• Stock price predictions or investment advice
• Personal questions unrelated to news

Try asking about any current event or news topic!"""