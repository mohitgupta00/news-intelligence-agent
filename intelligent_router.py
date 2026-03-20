"""
LLM-First Router: Single-pass intelligent dispatcher with context resolution.
Decides whether to handle queries directly or delegate to graph pipeline.
"""

import json
import logging
from groq import Groq
from pydantic import BaseModel, Field
from typing import Literal, Optional, List
from config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

# Single-pass routing schema
class RoutingLogic(BaseModel):
    routing: Literal["direct_response", "delegate_to_graph"] = Field(
        description="delegate_to_graph if query requires news/facts/current events. direct_response for greetings/capabilities/out-of-scope."
    )
    is_contextual_follow_up: bool = Field(
        description="True if user refers to previous topics using pronouns like 'he', 'this', 'that', 'the war'."
    )
    resolved_query: str = Field(
        description="Standalone version of user query. Replace pronouns with specific nouns from context. Example: 'What about him?' -> 'Donald Trump stance on Israel-Iran war'."
    )
    updated_summary: str = Field(
        description="Concise 1-sentence summary of conversation's active topic and key entities."
    )
    confidence: float = Field(
        description="Confidence in resolution accuracy (0-1). Use 0.6 if uncertain about pronoun resolution.",
        ge=0.0, le=1.0
    )

# Legacy compatibility
class RouterDecision(BaseModel):
    action: Literal["direct_response", "delegate_to_graph"]
    response: Optional[str] = None
    graph_query: Optional[str] = None
    reasoning: str
    resolved_entities: Optional[List[str]] = None
    resolved_topic: Optional[str] = None
    routing_confidence: Optional[float] = None
    suggested_sources: Optional[List[str]] = None

class IntelligentRouter:
    def __init__(self):
        self.groq_client = Groq(api_key=GROQ_API_KEY)
    
    async def resolve_intent_and_context(self, user_query: str, context_summary: str = "") -> RoutingLogic:
        """Single-pass intent resolution with context management."""
        
        system_prompt = f"""You are the NewsIQ Intelligence Router. Analyze user intent and maintain neural context.

CURRENT CONTEXT SUMMARY: "{context_summary}"

Your task: Return a JSON object with these EXACT fields:
{{
  "routing": "direct_response" or "delegate_to_graph",
  "is_contextual_follow_up": true or false,
  "resolved_query": "standalone version of user query",
  "updated_summary": "1-sentence conversation summary",
  "confidence": 0.8
}}

ROUTING RULES:
- Use "direct_response" for: greetings, capabilities, weather, recipes, math
- Use "delegate_to_graph" for: news, current events, politics, business

CONTEXT RESOLUTION:
- If user query has pronouns (he, him, this, that) AND context summary exists: resolve using context
- If no context or new topic: create fresh standalone query
- Set is_contextual_follow_up to true only if using context to resolve pronouns

CONFIDENCE SCORING:
- 0.9: Clear context, obvious resolution
- 0.7: Good context, likely correct  
- 0.5: Uncertain, multiple interpretations
- 0.3: Poor context, fallback needed

EXAMPLES:
User: "What is Trump doing?" Context: "" 
→ {{"routing": "delegate_to_graph", "is_contextual_follow_up": false, "resolved_query": "Donald Trump latest news", "updated_summary": "Discussing Donald Trump activities", "confidence": 0.8}}

User: "What about him?" Context: "Discussing Donald Trump activities"
→ {{"routing": "delegate_to_graph", "is_contextual_follow_up": true, "resolved_query": "Donald Trump latest news", "updated_summary": "Discussing Donald Trump activities", "confidence": 0.9}}

User: "What can you do?" Context: "anything"
→ {{"routing": "direct_response", "is_contextual_follow_up": false, "resolved_query": "What can you do?", "updated_summary": "System capabilities inquiry", "confidence": 0.95}}

Return ONLY the JSON object, no other text."""
        
        max_retries = 2
        for attempt in range(max_retries):
            try:
                logger.debug(f"Single-pass resolution attempt {attempt + 1} for: '{user_query}'")
                
                response = self.groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"User Query: {user_query}"}
                    ],
                    model=GROQ_MODEL,
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    timeout=10,
                    max_tokens=300
                )
                
                content = response.choices[0].message.content
                if not content or content.strip() == "":
                    raise ValueError("Empty response from LLM")
                
                # Parse and validate JSON
                try:
                    result_json = json.loads(content)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parsing failed: {e}. Content: {content[:100]}")
                    if attempt == max_retries - 1:
                        raise
                    continue
                
                # Validate required fields
                required_fields = ['routing', 'resolved_query', 'updated_summary', 'confidence']
                missing_fields = [f for f in required_fields if f not in result_json]
                if missing_fields:
                    logger.error(f"Missing required fields: {missing_fields}")
                    if attempt == max_retries - 1:
                        raise ValueError(f"Missing fields: {missing_fields}")
                    continue
                
                # Create and validate Pydantic model
                result = RoutingLogic(**result_json)
                
                # Sanity checks
                if not result.resolved_query or result.resolved_query.strip() == "":
                    logger.warning("Empty resolved_query, using original")
                    result.resolved_query = user_query
                    result.confidence = min(result.confidence, 0.6)
                
                logger.info(f"Single-pass resolution successful (confidence: {result.confidence:.2f})")
                return result
                
            except Exception as e:
                error_type = type(e).__name__
                logger.error(f"Single-pass resolution attempt {attempt + 1} failed ({error_type}): {e}")
                
                if attempt == max_retries - 1:
                    # Final attempt failed, use fallback
                    logger.warning("All resolution attempts failed, using fallback")
                    return self._fallback_resolution(user_query, context_summary)
                
                # Wait before retry for rate limit errors
                if "rate" in str(e).lower():
                    import asyncio
                    await asyncio.sleep(1)
        
        # Should never reach here, but safety fallback
        return self._fallback_resolution(user_query, context_summary)
    
    def _fallback_resolution(self, user_query: str, context_summary: str) -> RoutingLogic:
        """Fallback when LLM resolution fails."""
        query_lower = user_query.lower().strip()
        
        # Direct response patterns
        if any(pattern in query_lower for pattern in [
            'what can you do', 'capabilities', 'help', 'recipe', 'cook', 'math', 'weather'
        ]):
            return RoutingLogic(
                routing="direct_response",
                is_contextual_follow_up=False,
                resolved_query=user_query,
                updated_summary="System capabilities or out-of-scope query",
                confidence=0.8
            )
        
        # Basic pronoun detection
        has_pronouns = any(word in query_lower for word in [
            'he', 'him', 'his', 'she', 'her', 'it', 'they', 'them', 'this', 'that'
        ])
        
        # Simple context resolution
        resolved = user_query
        if has_pronouns and context_summary:
            # Extract entities from context summary
            entities = self._extract_entities_from_summary(context_summary)
            if entities:
                # Simple replacement (not sophisticated but safe)
                for pronoun in ['this', 'that', 'it']:
                    if pronoun in query_lower:
                        resolved = f"{entities[0]} {user_query.replace(pronoun, '').strip()}"
                        break
        
        return RoutingLogic(
            routing="delegate_to_graph",
            is_contextual_follow_up=has_pronouns,
            resolved_query=resolved,
            updated_summary=context_summary or f"Discussing {user_query[:50]}",
            confidence=0.6  # Low confidence triggers fallback in orchestrator
        )
    
    def _extract_entities_from_summary(self, summary: str) -> List[str]:
        """Extract entities from context summary for fallback."""
        entities = []
        summary_lower = summary.lower()
        
        # Common entities
        entity_patterns = {
            'trump': 'Trump', 'biden': 'Biden', 'putin': 'Putin',
            'israel': 'Israel', 'iran': 'Iran', 'ukraine': 'Ukraine',
            'russia': 'Russia', 'china': 'China', 'india': 'India',
            'apple': 'Apple', 'google': 'Google', 'tesla': 'Tesla'
        }
        
        for pattern, entity in entity_patterns.items():
            if pattern in summary_lower:
                entities.append(entity)
        
        return entities[:2]  # Limit to avoid confusion
    
    def route_query(self, user_query: str, conversation_memory: dict = None) -> RouterDecision:
        """Legacy compatibility method."""
        # Extract context summary from memory
        context_summary = ""
        if conversation_memory:
            context_summary = conversation_memory.get('context_summary', '')
            if not context_summary and conversation_memory.get('last_entities'):
                # Fallback: create summary from entities
                entities = conversation_memory['last_entities'][:2]
                context_summary = f"Discussing {' and '.join(entities)}"
        
        # Use synchronous version for compatibility
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(
                self.resolve_intent_and_context(user_query, context_summary)
            )
        except:
            result = self._fallback_resolution(user_query, context_summary)
        
        # Convert to legacy format
        return RouterDecision(
            action=result.routing,
            graph_query=result.resolved_query,
            reasoning=f"Single-pass resolution (confidence: {result.confidence:.2f})",
            routing_confidence=result.confidence
        )
    
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