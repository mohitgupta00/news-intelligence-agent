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
    r'\b(one|which)\b'
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
    # Check if we can reuse previous search results
    thread_id = state.get('thread_id', 'default')
    user_query = state.get('user_query', '')
    
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

def query_resolver(state):
    """Resolve query with context and caching."""
    em = state["entity_memory"]
    query = state["user_query"]
    temporal = extract_temporal_constraint(query)
    
    last_entity = em.get("last_entity", "")
    last_entities = em.get("last_entities", [])
    last_task = em.get("last_task", "")
    last_result = em.get("last_result", "")
    
    needs_resolution = contains_pronoun_reference(query)
    
    # Detect follow-up patterns
    follow_up_patterns = [
        r'^what about', r'^how about', r'^and (what|how)',
        r'connection', r'stance', r'position', r'view', r'opinion'
    ]
    is_follow_up = any(re.search(p, query.lower()) for p in follow_up_patterns)
    
    if not last_entity or (not needs_resolution and not is_follow_up):
        resolved = query
    else:
        # Check cache first
        context_query = f"{query} context:{last_entity} task:{last_task}"
        cached_resolution = get_cached_resolution(context_query)
        
        if cached_resolution:
            resolved = cached_resolution
        else:
            # Build context for LLM resolution
            context_parts = []
            if last_entities:
                context_parts.append(f"Previous topic: {', '.join(last_entities)}")
            elif last_entity:
                context_parts.append(f"Previous topic: {last_entity}")
            if last_task:
                context_parts.append(f"Previous task: {last_task}")
            if last_result:
                context_parts.append(f"Previous answer snippet: {last_result[:200]}...")
            
            context = "\n".join(context_parts)
            prompt = f"{context}\n\nCurrent query: \"{query}\"\n\nRewrite the query to be fully self-contained by incorporating the previous context. Include all necessary entity names. Return ONLY the rewritten query string."
            
            cached = _get_llm_cache(prompt)
            if cached:
                resolved = cached
            else:
                resp = _groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1
                )
                resolved = (resp.choices[0].message.content or query).strip()
                _set_llm_cache(prompt, resolved)
            
            cache_query_resolution(context_query, resolved)
    
    return {"resolved_query": resolved, "temporal_constraint": temporal}

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