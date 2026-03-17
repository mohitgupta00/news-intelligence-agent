"""Execution nodes: news fetching, text analysis, and entity comparison."""

import time
import asyncio
from config import CACHE_TTL_SECONDS
from tools.fetch_news import fetch_news_async, _is_likely_hallucinated
from tools.analyze_text import summarize_articles, analyze_sentiment, extract_entities, analyze_timeline
from tools.compare_entities import compare_entities
from utils.search_memory import store_search_result

async def fetch_news_node(state):
    """Fetch news articles with caching."""
    if "step" in state:
        step, full_state = state["step"], state["state"]
    else:
        pending = [
            s for s in state.get("plan", [])
            if s["step"] not in state.get("step_outputs", {})
        ]
        if not pending:
            return {"step_outputs": {}}
        step, full_state = pending[0], state
    
    query = step["params"].get("query", "")
    n = step["params"].get("n", 5)
    session_cache = dict(full_state.get("session_cache", {}))
    
    cache_key = f"fetch::{query}::{n}"
    
    # Check cache
    if cache_key in session_cache:
        cached_value, cached_timestamp = session_cache[cache_key]
        if (time.time() - cached_timestamp < CACHE_TTL_SECONDS 
            and not _is_likely_hallucinated(cached_value)):
            result, source = cached_value, "cache"
        else:
            result, source = await fetch_news_async(query, n)
    else:
        result, source = await fetch_news_async(query, n)
    
    # Store successful results in persistent memory
    if result and source != "cache":
        thread_id = full_state.get('thread_id', 'default')
        metadata = {
            'tool': 'fetch_news',
            'n_articles': n,
            'source': source
        }
        store_search_result(thread_id, query, result, metadata)
    
    # Build step output
    existing = dict(full_state.get("step_outputs", {}))
    existing[step["step"]] = {
        "step_index": step["step"],
        "tool": "fetch_news",
        "params": step["params"],
        "result": result,
        "status": "success" if result else "empty",
        "source": source,
        "cache_key": cache_key if result else None,
        "cache_value": (result, time.time()) if result else None
    }
    
    return {"step_outputs": existing}

def analyze_text_node(state):
    """Analyze text using various methods."""
    if "step" in state:
        step, full_state = state["step"], state["state"]
    else:
        pending = [
            s for s in state.get("plan", [])
            if s["step"] not in state.get("step_outputs", {})
        ]
        if not pending:
            return {"step_outputs": {}}
        step, full_state = pending[0], state
    
    task = step["params"].get("task", "summarize")
    
    # Get dependent outputs
    dep_outputs = [
        full_state["step_outputs"][dep]["result"]
        for dep in step.get("depends_on", [])
        if full_state["step_outputs"].get(dep, {}).get("result")
    ]
    
    articles_text = "\n\n".join(dep_outputs)
    
    # Execute analysis based on task
    if task == "timeline":
        query = step["params"].get("query", full_state.get("resolved_query", ""))
        result = analyze_timeline(query)
    elif task == "summarize":
        result = summarize_articles(articles_text)
    elif task == "sentiment":
        result = analyze_sentiment(articles_text)
    elif task == "extract_entities":
        result = extract_entities(articles_text)
    else:
        result = f"Unknown task: {task}"
    
    # Build step output
    existing = dict(full_state.get("step_outputs", {}))
    existing[step["step"]] = {
        "step_index": step["step"],
        "tool": "analyze_text",
        "params": step["params"],
        "result": result,
        "status": "success"
    }
    
    return {"step_outputs": existing}

def compare_entities_node(state):
    """Compare two entities."""
    if "step" in state:
        step, full_state = state["step"], state["state"]
    else:
        pending = [
            s for s in state.get("plan", [])
            if s["step"] not in state.get("step_outputs", {})
        ]
        if not pending:
            return {"step_outputs": {}}
        step, full_state = pending[0], state
    
    entity_a = step["params"].get("entity_a", "")
    entity_b = step["params"].get("entity_b", "")
    
    result = compare_entities(entity_a, entity_b, state=full_state)
    
    # Build step output
    existing = dict(full_state.get("step_outputs", {}))
    existing[step["step"]] = {
        "step_index": step["step"],
        "tool": "compare_entities",
        "params": step["params"],
        "result": result,
        "status": "success"
    }
    
    return {"step_outputs": existing}