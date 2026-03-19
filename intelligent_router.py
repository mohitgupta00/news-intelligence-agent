"""
LLM-First Router: Intelligent dispatcher for NewsIQ system.
Decides whether to handle queries directly or delegate to graph pipeline.
"""

import json
from groq import Groq
from pydantic import BaseModel
from typing import Literal, Optional, List
from config import GROQ_API_KEY, GROQ_MODEL

class RouterDecision(BaseModel):
    action: Literal["direct_response", "delegate_to_graph"]
    response: Optional[str] = None
    graph_query: Optional[str] = None
    reasoning: str
    # Enhanced context passing
    resolved_entities: Optional[List[str]] = None
    resolved_topic: Optional[str] = None
    routing_confidence: Optional[float] = None
    suggested_sources: Optional[List[str]] = None
    # Neural context fields
    context_switch_detected: Optional[bool] = None
    coreference_resolution: Optional[dict] = None

from utils.semantic_context import get_context_manager
from utils.entity_resolution import get_entity_resolver

class IntelligentRouter:
    def __init__(self):
        self.groq_client = Groq(api_key=GROQ_API_KEY)
        self.context_manager = get_context_manager()
        self.entity_resolver = get_entity_resolver()
    
    def route_query(self, user_query: str, conversation_memory: dict = None) -> RouterDecision:
        """Enhanced routing with neural context management."""
        
        # Step 1: Advanced entity resolution with coreference
        conversation_history = self._extract_conversation_history(conversation_memory or {})
        entity_resolution = self.entity_resolver.resolve_entities(user_query, conversation_history)
        
        # Step 2: Neural context switch detection
        context_switch_result = self.context_manager.update_context(
            user_query, 
            [entity.text for entity in entity_resolution.entities]
        )
        
        # Step 3: Get relevant context using attention mechanism
        relevant_context = self.context_manager.get_relevant_context(user_query)
        
        # Step 4: Enhanced routing decision
        if self._should_handle_directly(user_query):
            return self._create_direct_response(user_query)
        
        # Step 5: Build enhanced graph query with neural context
        enhanced_query = self._build_contextual_query(
            user_query, 
            entity_resolution, 
            context_switch_result,
            relevant_context
        )
        
        # Step 6: Create router decision with neural insights
        return RouterDecision(
            action="delegate_to_graph",
            reasoning=f"Neural analysis: {len(entity_resolution.entities)} entities detected, "
                     f"context switch: {context_switch_result.switch_type}, "
                     f"confidence: {entity_resolution.confidence:.2f}",
            graph_query=enhanced_query,
            resolved_entities=[entity.text for entity in entity_resolution.entities],
            resolved_topic=self._infer_topic_from_entities(entity_resolution.entities),
            routing_confidence=min(entity_resolution.confidence, context_switch_result.confidence),
            suggested_sources=self._suggest_sources_neural(entity_resolution.entities)
        )
    
    def _fallback_routing(self, query: str, error: str) -> RouterDecision:
        """Intelligent fallback with basic entity extraction."""
        query_lower = query.lower().strip()
        
        # Extract entities using simple patterns
        entities = self._extract_basic_entities(query)
        topic = self._extract_basic_topic(query)
        
        # Out-of-scope patterns
        out_of_scope_patterns = [
            'recipe', 'cook', 'bake', 'math', 'calculate', 'poem', 'story',
            'personal advice', 'relationship', 'how to', 'tutorial'
        ]
        
        # System capability patterns  
        capability_patterns = [
            'what can you do', 'what are you', 'your purpose', 'capabilities'
        ]
        
        # News patterns
        news_patterns = [
            'news', 'latest', 'update', 'politics', 'war', 'economy', 'business'
        ]
        
        if any(pattern in query_lower for pattern in capability_patterns):
            return RouterDecision(
                action="direct_response",
                response=None,
                reasoning="System capability question (fallback)",
                routing_confidence=0.8
            )
        
        if any(pattern in query_lower for pattern in out_of_scope_patterns):
            return RouterDecision(
                action="direct_response", 
                response="I'm a news intelligence reporter focused on current events. I can't help with that, but I'd be happy to discuss recent news!",
                reasoning="Out-of-scope query (fallback)",
                routing_confidence=0.9
            )
        
        # Intelligent source selection for fallback
        suggested_sources = self._get_fallback_sources(query)
        
        # Default to graph with extracted context
        return RouterDecision(
            action="delegate_to_graph",
            graph_query=query,
            reasoning=f"Fallback routing. Error: {error}",
            resolved_entities=entities if entities else None,
            resolved_topic=topic,
            routing_confidence=0.6,
            suggested_sources=suggested_sources
        )
    
    def _get_fallback_sources(self, query: str) -> List[str]:
        """Intelligent source selection for fallback scenarios."""
        query_lower = query.lower()
        
        # Breaking/real-time news patterns
        if any(word in query_lower for word in ['breaking', 'latest', 'today', 'recent', 'update']):
            return ['gnews', 'newsdata']
        
        # Business/tech patterns
        if any(word in query_lower for word in ['earnings', 'stock', 'market', 'business', 'company']):
            return ['newsdata']
        
        # International/global patterns
        if any(word in query_lower for word in ['global', 'international', 'worldwide', 'conflict', 'war']):
            return ['gnews']
        
        # US politics patterns
        if any(word in query_lower for word in ['trump', 'biden', 'election', 'politics', 'government']):
            return ['newsapi']
        
        # Tech companies
        if any(word in query_lower for word in ['apple', 'google', 'microsoft', 'tesla', 'amazon', 'meta']):
            return ['newsdata']
        
        # Default: prioritize sources without free tier delays
        return ['gnews', 'newsdata']
    
    def _extract_basic_entities(self, query: str) -> List[str]:
        """Basic entity extraction for fallback."""
        entities = []
        query_lower = query.lower()
        
        # Common entities
        entity_map = {
            'apple': 'Apple', 'google': 'Google', 'microsoft': 'Microsoft',
            'tesla': 'Tesla', 'amazon': 'Amazon', 'meta': 'Meta',
            'trump': 'Trump', 'biden': 'Biden', 'putin': 'Putin',
            'israel': 'Israel', 'iran': 'Iran', 'ukraine': 'Ukraine',
            'russia': 'Russia', 'china': 'China', 'india': 'India'
        }
        
        for key, entity in entity_map.items():
            if key in query_lower:
                entities.append(entity)
        
        return entities[:3]  # Limit to 3 entities
    
    def _extract_basic_topic(self, query: str) -> Optional[str]:
        """Basic topic extraction for fallback."""
        query_lower = query.lower()
        
        topic_map = {
            'war': 'War', 'conflict': 'Conflict', 'election': 'Election',
            'economy': 'Economy', 'market': 'Market', 'stock': 'Stock',
            'ai': 'AI', 'technology': 'Technology', 'climate': 'Climate'
        }
        
        for key, topic in topic_map.items():
            if key in query_lower:
                return topic
        
        return None
    
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
    def _extract_conversation_history(self, memory: dict) -> List[str]:
        """Extract conversation history for entity resolution"""
        history = []
        if memory.get('last_query'):
            history.append(memory['last_query'])
        if memory.get('conversation_history'):
            for turn in memory['conversation_history'][-3:]:  # Last 3 turns
                if isinstance(turn, dict) and 'query' in turn:
                    history.append(turn['query'])
                elif isinstance(turn, str):
                    history.append(turn)
        return history
    
    def _should_handle_directly(self, query: str) -> bool:
        """Determine if query should be handled directly"""
        query_lower = query.lower().strip()
        
        # System capability patterns  
        capability_patterns = [
            'what can you do', 'what are you', 'your purpose', 'capabilities',
            'help me', 'how do you work'
        ]
        
        # Out-of-scope patterns
        out_of_scope_patterns = [
            'recipe', 'cook', 'bake', 'math', 'calculate', 'poem', 'story',
            'personal advice', 'relationship', 'how to', 'tutorial', 'weather'
        ]
        
        return (any(pattern in query_lower for pattern in capability_patterns) or
                any(pattern in query_lower for pattern in out_of_scope_patterns))
    
    def _create_direct_response(self, query: str) -> RouterDecision:
        """Create direct response for system queries"""
        query_lower = query.lower()
        
        if any(pattern in query_lower for pattern in ['what can you do', 'capabilities', 'help']):
            return RouterDecision(
                action="direct_response",
                response=None,  # Will use get_system_capabilities()
                reasoning="System capability inquiry",
                routing_confidence=0.95
            )
        else:
            return RouterDecision(
                action="direct_response",
                response="I'm a news intelligence assistant focused on current events. I can't help with that, but I'd be happy to discuss recent news!",
                reasoning="Out-of-scope query",
                routing_confidence=0.9
            )
    
    def _build_contextual_query(self, original_query: str, entity_resolution, context_switch_result, relevant_context) -> str:
        """Build enhanced query with neural context"""
        # If no context switch and we have relevant context, enhance the query
        if not context_switch_result.switch_detected and relevant_context.get('relevant_entities'):
            # Add relevant entities from context
            context_entities = relevant_context['relevant_entities']
            current_entities = [entity.text for entity in entity_resolution.entities]
            
            # Find entities from context not in current query
            additional_entities = [e for e in context_entities if e not in current_entities]
            
            if additional_entities:
                # Enhance query with context
                enhanced_query = f"{original_query} (context: {', '.join(additional_entities[:2])})"
                return enhanced_query
        
        # Apply coreference resolution
        enhanced_query = original_query
        for pronoun, entity in entity_resolution.coreferences.items():
            enhanced_query = enhanced_query.replace(pronoun, entity)
        
        return enhanced_query
    
    def _infer_topic_from_entities(self, entities) -> Optional[str]:
        """Infer topic from resolved entities"""
        if not entities:
            return None
        
        # Get entity context
        entity_context = self.entity_resolver.get_entity_context([entity.text for entity in entities])
        
        # Infer topic from sectors/regions
        if entity_context['sectors']:
            return entity_context['sectors'][0].replace('_', ' ').title()
        
        if entity_context['regions']:
            return f"{entity_context['regions'][0]} Affairs"
        
        # Fallback to entity types
        entity_types = list(entity_context['entity_types'].values())
        if 'company' in entity_types:
            return 'Business'
        elif 'person' in entity_types:
            return 'Politics'
        elif 'country' in entity_types:
            return 'International'
        
        return 'General News'
    
    def _suggest_sources_neural(self, entities) -> List[str]:
        """Suggest sources based on entity analysis"""
        if not entities:
            return ['gnews', 'newsdata']
        
        entity_context = self.entity_resolver.get_entity_context([entity.text for entity in entities])
        
        # Business/tech entities -> newsdata
        if any(sector in ['technology', 'automotive_tech'] for sector in entity_context['sectors']):
            return ['newsdata', 'gnews']
        
        # International entities -> gnews
        if any(entity_type == 'country' for entity_type in entity_context['entity_types'].values()):
            return ['gnews', 'newsapi']
        
        # Political figures -> newsapi
        if any(entity_type == 'person' for entity_type in entity_context['entity_types'].values()):
            return ['newsapi', 'gnews']
        
        # Default
        return ['gnews', 'newsdata']