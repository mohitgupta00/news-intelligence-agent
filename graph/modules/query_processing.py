"""Query processing nodes: turn initialization, resolution, rewriting, and guarding."""

import re
import time
from typing import Optional
from groq import Groq
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from typing import Literal

from config import GROQ_API_KEY, GROQ_MODEL
from utils.query_cache import get_cached_resolution, cache_query_resolution
from utils.search_memory import should_reuse_search_results, get_search_memory_stats

# Initialize clients
_groq_client = Groq(api_key=GROQ_API_KEY)
_chat_groq = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL, temperature=0.1)

# LLM cache
_llm_cache = {}
_LLM_CACHE_TTL = 600

def _llm_cache_key(prompt): 
    import hashlib
    return hashlib.md5(f"{GROQ_MODEL}:{prompt}".encode()).hexdigest()

def _get_llm_cache(prompt):
    key = _llm_cache_key(prompt)
    if key in _llm_cache:
        timestamp, value = _llm_cache[key]
        if time.time() - timestamp < _LLM_CACHE_TTL:
            return value
    return None

def _set_llm_cache(prompt, value):
    _llm_cache[_llm_cache_key(prompt)] = (time.time(), value)

# Temporal and pronoun patterns
TEMPORAL_PATTERNS = [
    r'this\s+(week|month|year|day)', r'latest\s+news', r'recent', r'latest',
    r'today', r'yesterday', r'past\s+\d+\s+(days?|weeks?|months?|years?)',
    r'last\s+\d+\s+(days?|weeks?|months?|years?)'
]

PRONOUN_PATTERNS = [
    r'\b(he|his|him|she|her|it|its|they|them|their|this|that|these|those)\b',
    r'\b(one|which)\b',
    r'\b(this\s+war|that\s+conflict|the\s+situation)\b'
]

OOS_PATTERNS = [
    r'stock\s*(price|value)', r'predict.*price', r'forecast.*stock',
    r'will.*go\s+(up|down)', r'price.*will', r'how much.*will.*(cost|be worth)',
    r'investment.*advice', r'should\s+I\s+(buy|sell)'
]

class QueryAnalysis(BaseModel):
    intent: Literal["summarize", "sentiment", "timeline", "compare", "extract_entities"]
    api_queries: list[str] = Field(min_items=1, max_items=3)

def extract_temporal_constraint(query: str) -> Optional[str]:
    """Extract temporal constraints from query."""
    for pattern in TEMPORAL_PATTERNS:
        match = re.search(pattern, query.lower())
        if match:
            return match.group(0)
    return None

def contains_pronoun_reference(query: str) -> bool:
    """Check if query contains pronoun references."""
    return any(re.search(pattern, query.lower()) for pattern in PRONOUN_PATTERNS)

def turn_initializer(state):
    """Reset per-turn state while preserving session memory and search history."""
    # Input validation
    if not isinstance(state, dict):
        raise ValueError("State must be a dictionary")
    
    user_query = state.get('user_query', '')
    if not user_query or not isinstance(user_query, str):
        raise ValueError("user_query must be a non-empty string")
    
    thread_id = state.get('thread_id', 'default')
    if not isinstance(thread_id, str):
        raise ValueError("thread_id must be a string")
    
    # Check if we can reuse previous search results
    should_reuse, relevant_results = should_reuse_search_results(user_query, thread_id)
    
    # Get search memory stats for debugging
    memory_stats = get_search_memory_stats(thread_id)
    
    base_reset = {
        "plan": [],
        "current_step": 0,
        "replan_count": 0,
        "replan_decision": None,
        "final_answer": None,
        "planning_done": False,
        "temporal_constraint": None,
        "api_queries": [],
        "intent": ""
    }
    
    if should_reuse and relevant_results:
        # Reuse previous search results instead of starting fresh
        reused_step_outputs = {}
        for i, result in enumerate(relevant_results[:3]):  # Max 3 results
            reused_step_outputs[i] = {
                "step_index": i,
                "tool": "fetch_news",
                "params": {"query": result.query, "n": 5},
                "result": result.result,
                "status": "success",
                "source": "memory_reuse",
                "reused_from": result.query
            }
        
        base_reset["step_outputs"] = reused_step_outputs
        base_reset["search_memory_reused"] = True
        base_reset["search_memory_stats"] = memory_stats
    else:
        base_reset["search_memory_reused"] = False
        base_reset["search_memory_stats"] = memory_stats
    
    return base_reset

def extract_entities_from_text(text: str) -> list:
    """Extract key entities from text using simple keyword matching."""
    if not text:
        return []
    
    # Common entities that appear in news
    entity_patterns = {
        'countries': ['israel', 'iran', 'india', 'china', 'usa', 'russia', 'ukraine', 'germany', 'france', 'uk'],
        'companies': ['apple', 'google', 'microsoft', 'tesla', 'amazon', 'meta', 'nvidia', 'openai'],
        'people': ['trump', 'biden', 'putin', 'xi', 'musk', 'bezos', 'gates'],
        'topics': ['war', 'conflict', 'election', 'economy', 'ai', 'climate']
    }
    
    text_lower = text.lower()
    found_entities = []
    
    for category, entities in entity_patterns.items():
        for entity in entities:
            if entity in text_lower:
                found_entities.append(entity.title())
    
    return list(set(found_entities))  # Remove duplicates

def needs_context_resolution(query: str) -> bool:
    """Determine if query needs context resolution."""
    query_lower = query.lower().strip()
    
    # Direct context indicators
    context_indicators = [
        # Pronouns and references
        r'\b(it|they|them|their|this|that|these|those)\b',
        # Implicit references
        r'\b(the\s+)?(war|conflict|situation|crisis|issue|problem)\b',
        # Follow-up patterns
        r'^(what|how)\s+about\b', r'^any\s+(updates?|news)\b', r'^latest\s+on\b',
        # Comparative/relational
        r'\b(other|another|also|too|as\s+well)\b',
        # Vague queries
        r'^(updates?|news|latest)$'
    ]
    
    return any(re.search(pattern, query_lower) for pattern in context_indicators)

def resolve_contextual_query(query: str, entity_memory: dict, conversation_history: list = None) -> str:
    """Robust contextual query resolution with multiple fallback strategies."""
    
    # Strategy 1: Check if resolution is actually needed
    if not needs_context_resolution(query):
        return query
    
    # Strategy 2: Extract available context
    context_entities = []
    context_topics = []
    
    # From entity memory (most reliable)
    if entity_memory:
        if entity_memory.get('last_entities'):
            context_entities.extend(entity_memory['last_entities'])
        if entity_memory.get('last_entity'):
            context_entities.append(entity_memory['last_entity'])
        if entity_memory.get('last_task'):
            context_topics.append(entity_memory['last_task'])
    
    # From conversation history (backup)
    if conversation_history:
        for item in conversation_history[-5:]:  # Look back further
            if isinstance(item, dict):
                if item.get('entities'):
                    context_entities.extend(item['entities'])
                if item.get('query'):
                    context_topics.append(item['query'])
    
    # Remove duplicates and clean
    context_entities = list(set([e for e in context_entities if e]))
    context_topics = [t for t in context_topics if t][:2]  # Keep recent topics
    
    # Strategy 3: Rule-based resolution for common patterns
    query_lower = query.lower()
    
    # Handle specific patterns with entity substitution
    if context_entities:
        # "What about X?" patterns
        if re.match(r'^(what|how)\s+about\b', query_lower):
            if len(context_entities) == 1:
                return f"What about {context_entities[0]} {query[query.lower().find('about')+5:].strip()}"
            elif len(context_entities) > 1:
                return f"What about {' and '.join(context_entities[:2])} {query[query.lower().find('about')+5:].strip()}"
        
        # "Any updates/latest" patterns
        if re.match(r'^(any\s+)?(updates?|latest|news)\b', query_lower):
            main_entity = context_entities[0]
            return f"Latest news about {main_entity}"
        
        # "This/that war/conflict" patterns
        if re.search(r'\b(this|that)\s+(war|conflict|situation)\b', query_lower):
            if len(context_entities) >= 2:
                return re.sub(r'\b(this|that)\s+(war|conflict|situation)\b', 
                            f"{context_entities[0]}-{context_entities[1]} \\2", query, flags=re.IGNORECASE)
    
    # Strategy 4: LLM-based resolution (most expensive, use as last resort)
    if context_entities or context_topics:
        context_info = []
        if context_entities:
            context_info.append(f"Entities: {', '.join(context_entities[:3])}")
        if context_topics:
            context_info.append(f"Recent topic: {context_topics[0][:100]}")
        
        context = "\n".join(context_info)
        cache_key = f"{query}|{context}"
        cached = _get_llm_cache(cache_key)
        
        if cached:
            return cached
        
        prompt = f"""{context}

Query: "{query}"

Rewrite to be standalone by replacing vague references with specific entities. Keep it concise.

Examples:
- "What about their response?" + Entities: Israel, Iran → "What about Iran's response to Israel?"
- "Any updates?" + Entities: Tesla → "Latest Tesla news"
- "This war affecting India?" + Entities: Israel, Iran → "Israel-Iran conflict impact on India"

Rewritten query:"""
        
        try:
            resp = _groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=50
            )
            resolved = (resp.choices[0].message.content or query).strip()
            # Clean up common LLM artifacts
            resolved = re.sub(r'^(rewritten query:?|query:?)\s*', '', resolved, flags=re.IGNORECASE)
            _set_llm_cache(cache_key, resolved)
            return resolved
        except Exception:
            pass  # Fall through to fallback
    
    # Strategy 5: Fallback - return original query
    return query

def query_resolver(state):
    """Resolve query with router hints optimization."""
    # Input validation
    if not isinstance(state, dict):
        raise ValueError("State must be a dictionary")
    
    if "entity_memory" not in state or not isinstance(state["entity_memory"], dict):
        raise ValueError("entity_memory must be a dictionary")
    
    if "user_query" not in state or not isinstance(state["user_query"], str):
        raise ValueError("user_query must be a string")
    
    query = state["user_query"].strip()
    if not query:
        raise ValueError("user_query cannot be empty")
    
    em = state["entity_memory"]
    conversation_history = state.get('conversation_history', [])
    context_hints = state.get('context_hints', {})
    temporal = extract_temporal_constraint(query)
    
    # OPTIMIZATION: Use router insights if available (eliminates double-think)
    if context_hints and context_hints.get('resolved_entities'):
        # Router already analyzed context - use its insights
        resolved = query  # Query already processed by router
        current_entities = context_hints['resolved_entities']
        resolution_method = "router_hints"
        confidence = context_hints.get('routing_confidence', 0.9)
        entities_used = current_entities
    else:
        # Fallback to full contextual resolution
        resolution_method = "none"
        entities_used = []
        confidence = 1.0
        
        if needs_context_resolution(query):
            if em.get('last_entities') or conversation_history:
                resolution_method = "entity_memory" if em.get('last_entities') else "conversation_history"
                entities_used = em.get('last_entities', [])
                confidence = 0.8
            resolved = resolve_contextual_query(query, em, conversation_history)
            if resolved != query:
                resolution_method = "rule_based" if "llm" not in resolution_method else "llm"
        else:
            resolved = query
        
        # Extract entities if not from router
        current_entities = extract_entities_from_text(resolved)
    
    # Update entity memory
    if current_entities:
        em['current_entities'] = current_entities
    
    # Create query resolution tracking
    query_resolution = {
        "original_query": query,
        "resolved_query": resolved,
        "resolution_method": resolution_method,
        "entities_used": entities_used,
        "confidence": confidence
    }
    
    return {
        "resolved_query": resolved, 
        "temporal_constraint": temporal,
        "extracted_entities": current_entities,
        "query_resolution": query_resolution,
        "active_entities": current_entities
    }

def query_rewriter(state):
    """Analyze query intent and generate API queries."""
    resolved = state["resolved_query"]
    structured = _chat_groq.with_structured_output(QueryAnalysis)
    
    prompt = f"""Analyze user query and determine:
1. intent: summarize|sentiment|timeline|compare|extract_entities
   - Use 'summarize' for ALL informational, factual, multi-part, or mixed queries (DEFAULT)
   - Use 'sentiment' ONLY when user uses words like: sentiment, opinion, reception, how is X perceived, what do people think
   - NEVER use 'sentiment' for 'what happened', 'what is X doing', 'tell me about' queries
2. api_queries: 1-3 clean 2-5 word keyword strings
   - Each query MUST include the main entity name (e.g. 'Trump Epstein files' not 'Epstein connection')
   - For multi-part queries, generate one focused query per sub-topic

CRITICAL: for compare queries with 2 entities, produce EXACTLY 2 separate queries.

Examples:
  'Compare Google and Microsoft' -> intent=compare, api_queries=['Google news','Microsoft news']
  'Summarize latest OpenAI news' -> intent=summarize, api_queries=['OpenAI news']
  'What is Trump doing? What about his Epstein connection?' -> intent=summarize, api_queries=['Trump latest news','Trump Epstein files']

User query: "{resolved}\""""
    
    try:
        result = structured.invoke(prompt)
        return {"intent": result.intent, "api_queries": result.api_queries or [resolved]}
    except Exception:
        return {"intent": "summarize", "api_queries": [resolved]}

def guard_node(state):
    """Check for out-of-scope queries."""
    query_lower = state["resolved_query"].lower()
    if any(re.search(pattern, query_lower) for pattern in OOS_PATTERNS):
        return {"replan_decision": "out_of_scope"}
    return {"replan_decision": None}