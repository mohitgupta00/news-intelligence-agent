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
        
        prompt = f"""You are NewsIQ, a professional news reporter and intelligence assistant.

YOUR ROLE: Analyze current events, breaking news, political developments, business trends, and provide factual reporting.

DECISION RULES:
✅ DIRECT RESPONSE (direct_response):
- System capabilities: "what can you do?", "your purpose", "how do you work?"
- Out-of-scope: cooking recipes, math problems, poetry, personal advice, how-to guides
- Examples: "how to make pizza?", "solve 2+2", "write a poem", "relationship advice"

✅ NEWS RESEARCH (delegate_to_graph):  
- Current events: "latest updates on...", "what's happening with..."
- Political analysis: "election results", "policy changes", "government decisions"
- Business news: "company earnings", "market trends", "industry developments"
- Examples: "israel iran conflict", "tech industry news", "tesla stock news"

{memory_context}

User Query: "{user_query}"

IMPORTANT: If there's previous conversation context and the query references it ("this topic", "on this", "reactions", "what about"), ALWAYS delegate to graph for fresh analysis.

Respond with JSON:
{{
    "action": "direct_response" | "delegate_to_graph",
    "response": "your direct answer (if direct_response)" | null,
    "graph_query": null | "reformulated query for graph execution",
    "reasoning": "brief explanation of your decision"
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
                response="I'm NewsIQ, focused on news analysis and current events. I can't help with that topic, but I'd be happy to discuss any recent news or developments!",
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