"""Planning nodes: plan creation, routing, step collection, and replanning."""

import json
import re
import logging
from groq import Groq
from langgraph.constants import Send

from config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)
_groq_client = Groq(api_key=GROQ_API_KEY)

def select_optimal_sources(query: str, intent: str, context_hints: dict = None) -> list:
    """Select optimal news sources based on query characteristics."""
    query_lower = query.lower()
    suggested_sources = []
    
    # Use router hints if available
    if context_hints and context_hints.get('suggested_sources'):
        return context_hints['suggested_sources']
    
    # Source selection logic based on query patterns and API capabilities
    source_patterns = {
        'gnews': {  # Best for real-time and international news
            'patterns': ['breaking', 'latest', 'today', 'recent', 'global', 'international', 'worldwide'],
            'entities': ['china', 'europe', 'asia', 'russia', 'ukraine', 'israel', 'iran'],
            'topics': ['war', 'conflict', 'climate', 'economy']
        },
        'newsdata': {  # Best for business and tech news
            'patterns': ['business', 'market', 'stock', 'earnings', 'financial', 'technology'],
            'entities': ['apple', 'google', 'microsoft', 'tesla', 'amazon', 'meta'],
            'topics': ['tech', 'innovation', 'ai', 'startup', 'company']
        },
        'newsapi': {  # Good for general news but has free tier delays
            'patterns': ['update', 'report', 'analysis', 'policy'],
            'entities': ['usa', 'america', 'us', 'trump', 'biden'],
            'topics': ['politics', 'election', 'government']
        }
    }
    
    # Score each source
    source_scores = {}
    
    for source, criteria in source_patterns.items():
        score = 0
        
        # Pattern matching
        for pattern in criteria['patterns']:
            if pattern in query_lower:
                score += 3
        
        # Entity matching
        for entity in criteria['entities']:
            if entity in query_lower:
                score += 2
        
        # Topic matching
        for topic in criteria['topics']:
            if topic in query_lower:
                score += 1
        
        source_scores[source] = score
    
    # Intent-based adjustments (considering API capabilities)
    if intent == 'compare':
        source_scores['newsdata'] += 3  # Best for business comparisons
    elif intent == 'sentiment':
        source_scores['gnews'] += 3  # Best global coverage and real-time
    elif intent == 'timeline':
        source_scores['gnews'] += 2  # Better for recent events
        source_scores['newsdata'] += 1
    
    # Real-time query boost (NewsAPI free tier has delays)
    if any(word in query_lower for word in ['breaking', 'latest', 'today', 'recent']):
        source_scores['gnews'] += 2
        source_scores['newsdata'] += 1
        source_scores['newsapi'] -= 1  # Penalize NewsAPI for real-time queries
    
    # Sort sources by score and return top 2-3 for better coverage
    sorted_sources = sorted(source_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Include top sources with positive scores
    suggested_sources = [source for source, score in sorted_sources if score > 0][:2]
    
    # Fallback strategy: ensure we always have working sources
    if not suggested_sources:
        # Default to most reliable sources
        suggested_sources = ['gnews', 'newsdata']
    elif len(suggested_sources) == 1:
        # Add a backup source
        remaining = [s for s in ['gnews', 'newsdata', 'newsapi'] if s not in suggested_sources]
        if remaining:
            suggested_sources.append(remaining[0])
    
    return suggested_sources

def optimize_query_for_source(query: str, source: str) -> str:
    """Optimize query for specific news source."""
    if source == 'newsapi':
        # NewsAPI works better with specific entities and keywords
        return query
    elif source == 'gnews':
        # GNews works better with broader terms
        # Remove very specific constraints
        optimized = re.sub(r'\b(latest|recent|today|yesterday)\b', '', query, flags=re.IGNORECASE)
        return optimized.strip() or query
    elif source == 'newsdata':
        # NewsData works better with business/tech terms
        return query
    
    return query

def planner(state):
    """Create execution plan with intelligent source routing."""
    if state.get("planning_done") and state.get("plan"):
        return {"planning_done": True}
    
    resolved = state["resolved_query"]
    api_queries = state.get("api_queries", [resolved])
    intent = state.get("intent", "summarize")
    temporal = state.get("temporal_constraint", "") or ""
    context_hints = state.get("context_hints", {})
    
    temporal_suffix = f" {temporal}" if temporal else ""
    
    if intent == "compare" and len(api_queries) == 2:
        plan = [{
            "step": 0,
            "tool": "compare_entities",
            "params": {"entity_a": api_queries[0], "entity_b": api_queries[1]},
            "depends_on": []
        }]
    elif intent == "timeline":
        if any(word in query_lower for word in ['breaking', 'latest', 'today', 'recent']):
            # For breaking/recent news: prioritize sources without free tier delays
            optimal_sources = ['gnews', 'newsdata']
        else:
            optimal_sources = select_optimal_sources(api_queries[0], intent, context_hints)
        
        plan = [
            {
                "step": 0,
                "tool": "fetch_news",
                "params": {
                    "query": api_queries[0] + temporal_suffix, 
                    "n": 7,
                    "preferred_sources": optimal_sources
                },
                "depends_on": []
            },
            {
                "step": 1,
                "tool": "analyze_text",
                "params": {"task": "timeline"},
                "depends_on": [0]
            }
        ]
    elif intent in ("summarize", "sentiment", "extract_entities"):
        # Intelligent source routing for each query
        plan = []
        
        for i, query in enumerate(api_queries):
            optimal_sources = select_optimal_sources(query, intent, context_hints)
            optimized_query = optimize_query_for_source(query, optimal_sources[0] if optimal_sources else 'newsapi')
            
            plan.append({
                "step": i,
                "tool": "fetch_news",
                "params": {
                    "query": optimized_query,
                    "n": 5,
                    "preferred_sources": optimal_sources
                },
                "depends_on": []
            })
        
        # Add analysis step that depends on all fetch steps
        plan.append({
            "step": len(api_queries),
            "tool": "analyze_text",
            "params": {"task": intent},
            "depends_on": list(range(len(api_queries)))
        })
    else:
        # Default plan with source optimization
        optimal_sources = select_optimal_sources(api_queries[0], intent, context_hints)
        optimized_query = optimize_query_for_source(api_queries[0], optimal_sources[0] if optimal_sources else 'newsapi')
        
        plan = [
            {
                "step": 0,
                "tool": "fetch_news",
                "params": {
                    "query": optimized_query + temporal_suffix,
                    "n": 5,
                    "preferred_sources": optimal_sources
                },
                "depends_on": []
            },
            {
                "step": 1,
                "tool": "analyze_text",
                "params": {"task": "summarize"},
                "depends_on": [0]
            }
        ]
    
    return {"plan": plan, "current_step": 0, "replan_count": 0}

def router(state):
    """Route ready steps for execution."""
    step_outputs = state.get("step_outputs", {})
    ready_steps = [
        step for step in state["plan"]
        if step["step"] not in step_outputs
        and all(dep in step_outputs for dep in step.get("depends_on", []))
    ]
    
    return [
        Send(step["tool"], {"step": step, "state": state})
        for step in ready_steps
    ]

def step_collector(state):
    """Collect completed steps (LangGraph handles merging)."""
    return {"all_steps_complete": True}

def replanner(state):
    """Handle failed steps and create recovery plans."""
    step_outputs = state.get("step_outputs", {})
    any_empty = any(
        output.get("status") == "empty" 
        for output in step_outputs.values()
    )
    
    replan_count = state.get("replan_count", 0)
    max_retries = 2
    
    if replan_count >= max_retries:
        return {"replan_decision": "finish"}
    
    if any_empty and replan_count < max_retries:
        failed_queries = [
            step["params"].get("query", "")
            for step in state["plan"]
        ]
        original = state.get("resolved_query", state.get("user_query", ""))
        
        prompt = f"""You are a query recovery specialist.
ORIGINAL: "{original}"
FAILED: {json.dumps(failed_queries)}
Provide 2-3 recovery strategies. Return ONLY JSON array: [{{"step":1,"tool":"fetch_news","params":{{"query":"..."}}}}]"""
        
        try:
            resp = _groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            content = resp.choices[0].message.content
            match = re.search(r'\[[\s\S]*\]', content)
            
            if not match:
                return {"replan_decision": "finish"}
            
            new_steps = json.loads(match.group())
            
            # Filter out already attempted queries
            attempted = {
                step["params"].get("query", "").lower()
                for step in state["plan"]
            }
            filtered_steps = [
                step for step in new_steps
                if step.get("params", {}).get("query", "").lower() not in attempted
            ]
            
            if not filtered_steps:
                return {"replan_decision": "finish"}
            
            # Add new steps with proper indexing
            offset = len(state["plan"])
            for i, step in enumerate(filtered_steps):
                step["step"] = offset + i
            
            return {
                "plan": state["plan"] + filtered_steps,
                "replan_count": replan_count + 1,
                "replan_decision": "continue"
            }
            
        except Exception as e:
            logger.error(f"Replanner error: {e}")
    
    return {"replan_decision": "finish"}