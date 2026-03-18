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
        
        prompt = f"""You are NewsIQ, an AI news intelligence assistant. Analyze this query and decide how to handle it.

HANDLE DIRECTLY if:
- System capability questions ("what can you do?", "how do you work?")
- Greetings, thanks, or casual conversation
- Out-of-scope requests (investment advice, stock predictions, personal questions)

DELEGATE TO GRAPH if:
- News analysis needed (summaries, sentiment, timelines, comparisons)
- Current events or information requests
- Follow-up questions that need fresh news data
- Questions about reactions, opinions, or responses to current events
- Any query that references "this topic", "on this", "about this" when there's previous context

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
            # Fallback: delegate to graph for safety
            return RouterDecision(
                action="delegate_to_graph",
                graph_query=user_query,
                reasoning=f"Router error, defaulting to graph: {str(e)}"
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