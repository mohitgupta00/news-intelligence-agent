import json
import re
import hashlib
import time
from typing import Any, Optional
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL
from graph.state import NewsIQState
from tools.fetch_news import fetch_news, clear_cache
from tools.analyze_text import summarize_articles, analyze_sentiment, extract_entities, analyze_timeline
from tools.compare_entities import compare_entities

_groq_client = Groq(api_key=GROQ_API_KEY)

# ============================================
# SMART LLM CACHING - Avoid redundant API calls
# ============================================
_llm_cache: dict = {}
_llm_cache_ttl: int = 600  # 10 minutes TTL

def _get_llm_cache_key(prompt: str, model: str = GROQ_MODEL) -> str:
    """Generate cache key for LLM prompt."""
    content = f"{model}:{prompt}"
    return hashlib.md5(content.encode()).hexdigest()

def _get_from_llm_cache(prompt: str) -> Optional[str]:
    """Get cached LLM response if available and fresh."""
    key = _get_llm_cache_key(prompt)
    if key in _llm_cache:
        cached_time, cached_result = _llm_cache[key]
        if time.time() - cached_time < _llm_cache_ttl:
            return cached_result
    return None

def _set_llm_cache(prompt: str, result: str) -> None:
    """Cache LLM response."""
    key = _get_llm_cache_key(prompt)
    _llm_cache[key] = (time.time(), result)

def clear_llm_cache() -> None:
    """Clear LLM cache."""
    global _llm_cache
    _llm_cache = {}

TEMPORAL_PATTERNS = [
    r'this\s+(week|month|year|day)',
    r'latest\s+news',
    r'recent',
    r'latest',
    r'today',
    r'yesterday',
    r'past\s+\d+\s+(days?|weeks?|months?|years?)',
    r'last\s+\d+\s+(days?|weeks?|months?|years?)',
]

def extract_temporal_constraint(query: str) -> Optional[str]:
    """Extract temporal constraint from query (e.g., 'this week', 'recent')."""
    query_lower = query.lower()
    for pattern in TEMPORAL_PATTERNS:
        match = re.search(pattern, query_lower)
        if match:
            return match.group(0)
    return None

PRONOUN_PATTERNS = [
    r'\b(it|this|that|them|their|these)\b',
    r'\b(one|which)\b',
]

def contains_pronoun_reference(query: str) -> bool:
    """Check if query contains pronouns that need resolution."""
    query_lower = query.lower()
    return any(re.search(p, query_lower) for p in PRONOUN_PATTERNS)

def query_resolver(state: NewsIQState) -> dict:
    em = state["entity_memory"]
    query = state["user_query"]
    messages = state.get("messages", [])
    
    temporal = extract_temporal_constraint(query)
    
    last_entity = em.get("last_entity", "")
    last_entities = em.get("last_entities", [])
    last_task = em.get("last_task", "")
    
    needs_resolution = contains_pronoun_reference(query)
    
    if last_entity and not needs_resolution:
        resolved = query
    elif last_entity and needs_resolution:
        context = f"Previous entities discussed: {', '.join(last_entities) if last_entities else last_entity}"
        prompt = f"""{context}
Last task: {last_task}
Current query: "{query}"
This query contains a pronoun or reference (like "it", "that", "which one", "their").
Rewrite to be fully self-contained by explicitly naming the entity being referenced.
Return only the rewritten query string."""
        # Try cache first
        cached = _get_from_llm_cache(prompt)
        if cached:
            resolved = cached
        else:
            response = _groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            resolved = response.choices[0].message.content
            if resolved:
                resolved = resolved.strip()
                _set_llm_cache(prompt, resolved)
            else:
                resolved = query
    elif len(last_entities) > 1 and needs_resolution:
        context = f"Previous entities discussed: {', '.join(last_entities)}"
        prompt = f"""{context}
Current query: "{query}"
This query references one of the previous entities. Rewrite to explicitly name which entity.
Return only the rewritten query string."""
        # Try cache first
        cached = _get_from_llm_cache(prompt)
        if cached:
            resolved = cached
        else:
            response = _groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            resolved = response.choices[0].message.content
            if resolved:
                resolved = resolved.strip()
                _set_llm_cache(prompt, resolved)
            else:
                resolved = query
    else:
        resolved = query
    
    return {"resolved_query": resolved, "temporal_constraint": temporal}

def query_rewriter(state: NewsIQState) -> dict:
    resolved = state["resolved_query"]

    prompt = f"""
You are a search query optimizer for a news API system.

Analyze the user query and return a JSON object with:
1. "intent": one of ["summarize", "sentiment", "timeline", "compare", "extract_entities"]
2. "api_queries": list of clean 2-5 word keyword queries for the news API

CRITICAL RULE for comparisons:
- If the query compares TWO entities, return EXACTLY 2 separate queries, one per entity
- Never combine two entities into one query string

Examples:
"Compare Google and Microsoft news"
→ {{"intent": "compare", "api_queries": ["Google news", "Microsoft news"]}}

"Summarize latest news about OpenAI"
→ {{"intent": "summarize", "api_queries": ["OpenAI news"]}}

"What is going on in India?"
→ {{"intent": "summarize", "api_queries": ["India current events", "India news today"]}}

"Sentiment around Tesla this week"
→ {{"intent": "sentiment", "api_queries": ["Tesla news this week"]}}

"Timeline of SpaceX events"
→ {{"intent": "timeline", "api_queries": ["SpaceX events"]}}

User query: "{resolved}"
Return only valid JSON, nothing else.
"""
    # Try cache first
    cached = _get_from_llm_cache(prompt)
    if cached:
        raw = cached
    else:
        response = _groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        raw = response.choices[0].message.content.strip()
        _set_llm_cache(prompt, raw)
    
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    
    if raw.startswith("{") and "}" in raw:
        try:
            parsed = json.loads(raw)
            intent = parsed.get("intent", "summarize")
            api_queries = parsed.get("api_queries", [resolved])
            if not api_queries:
                api_queries = [resolved]
        except (json.JSONDecodeError, AttributeError):
            intent = "summarize"
            api_queries = [resolved]
    else:
        intent = "summarize"
        api_queries = [resolved]

    return {"intent": intent, "api_queries": api_queries}

def planner(state: NewsIQState) -> dict:
    if state.get("planning_done", False) and state.get("plan"):
        return {"planning_done": True}
    
    resolved_query = state["resolved_query"]
    api_queries = state.get("api_queries", [resolved_query])
    intent = state.get("intent", "summarize")
    temporal = state.get("temporal_constraint", "")
    
    query_lower = resolved_query.lower()
    out_of_scope_patterns = [
        r'stock\s*(price|value)',
        r'predict.*price',
        r'forecast.*stock',
        r'will.*go\s+(up|down)',
        r'price.*will',
        r'how much.*will.*(cost|be worth)',
        r'investment.*advice',
        r'should\s+I\s+(buy|sell)',
    ]
    
    is_out_of_scope = any(re.search(p, query_lower) for p in out_of_scope_patterns)
    
    if is_out_of_scope:
        return {
            "plan": [],
            "planning_done": True,
            "replan_decision": "out_of_scope"
        }
    
    temporal_suffix = f" {temporal}" if temporal else ""
    
    if intent == "compare" and len(api_queries) == 2:
        plan = [
            {"step": 0, "tool": "compare_entities",
             "params": {"entity_a": api_queries[0], "entity_b": api_queries[1]},
             "depends_on": []}
        ]
    elif intent == "timeline":
        plan = [
            {"step": 0, "tool": "fetch_news",
             "params": {"query": api_queries[0] + temporal_suffix, "n": 7}, "depends_on": []},
            {"step": 1, "tool": "analyze_text",
             "params": {"task": "timeline"}, "depends_on": [0]}
        ]
    elif intent in ["summarize", "sentiment", "extract_entities"]:
        fetch_steps = [
            {"step": i, "tool": "fetch_news",
             "params": {"query": q, "n": 5}, "depends_on": []}
            for i, q in enumerate(api_queries)
        ]
        analyze_step = {
            "step": len(api_queries),
            "tool": "analyze_text",
            "params": {"task": intent},
            "depends_on": list(range(len(api_queries)))
        }
        plan = fetch_steps + [analyze_step]
    else:
        plan = [
            {"step": 0, "tool": "fetch_news",
             "params": {"query": api_queries[0] + temporal_suffix, "n": 5}, "depends_on": []},
            {"step": 1, "tool": "analyze_text",
             "params": {"task": "summarize"}, "depends_on": [0]}
        ]

    return {"plan": plan, "current_step": 0, "replan_count": 0}

def router(state: NewsIQState) -> list[dict]:
    from langgraph.constants import Send
    
    ready_steps = [
        s for s in state["plan"]
        if s["step"] not in state["step_outputs"]
        and all(dep in state["step_outputs"] for dep in s.get("depends_on", []))
    ]
    
    sends = []
    for step in ready_steps:
        tool = step["tool"]
        sends.append(Send(tool, {"step": step, "state": state}))
    
    return sends

def fetch_news_node(state: dict) -> dict:
    if "step" in state:
        step = state["step"]
        state = state["state"]
    else:
        pending = [s for s in state.get("plan", []) if s["step"] not in state.get("step_outputs", {})]
        if not pending:
            return {"step_outputs": {}}
        step = pending[0]
    
    query = step["params"].get("query", "")
    n = step["params"].get("n", 5)
    
    result, source = fetch_news(query, n=n)
    status = "success" if result else "empty"
    
    existing = state.get("step_outputs", {})
    existing[step["step"]] = {
        "step_index": step["step"],
        "tool": "fetch_news",
        "params": step["params"],
        "result": result,
        "status": status
    }
    
    return {"step_outputs": existing}

def analyze_text_node(state: dict) -> dict:
    if "step" in state:
        step = state["step"]
        state = state["state"]
    else:
        pending = [s for s in state.get("plan", []) if s["step"] not in state.get("step_outputs", {})]
        if not pending:
            return {"step_outputs": {}}
        step = pending[0]
    
    task = step["params"].get("task", "summarize")
    
    dep_outputs = []
    for dep in step.get("depends_on", []):
        dep_data = state["step_outputs"].get(dep, {})
        if dep_data.get("result"):
            dep_outputs.append(dep_data["result"])
    
    articles_text = "\n\n".join(dep_outputs)
    
    if task == "timeline":
        query = step["params"].get("query", state.get("resolved_query", ""))
        result = analyze_timeline(query)
    elif task == "summarize":
        result = summarize_articles(articles_text)
    elif task == "sentiment":
        result = analyze_sentiment(articles_text)
    elif task == "extract_entities":
        result = extract_entities(articles_text)
    else:
        result = f"Unknown task: {task}"
    
    existing = state.get("step_outputs", {})
    existing[step["step"]] = {
        "step_index": step["step"],
        "tool": "analyze_text",
        "params": step["params"],
        "result": result,
        "status": "success"
    }
    
    return {"step_outputs": existing}

def compare_entities_node(state: dict) -> dict:
    if "step" in state:
        step = state["step"]
        full_state = state["state"]
    else:
        pending = [s for s in state.get("plan", []) if s["step"] not in state.get("step_outputs", {})]
        if not pending:
            return {"step_outputs": {}}
        step = pending[0]
        full_state = state
    
    entity_a = step["params"].get("entity_a", "")
    entity_b = step["params"].get("entity_b", "")
    
    result = compare_entities(entity_a, entity_b, state=full_state)
    
    existing = full_state.get("step_outputs", {})
    existing[step["step"]] = {
        "step_index": step["step"],
        "tool": "compare_entities",
        "params": step["params"],
        "result": result,
        "status": "success"
    }
    
    return {"step_outputs": existing}

def replanner(state: NewsIQState) -> dict:
    all_done = all(s["step"] in state["step_outputs"] for s in state["plan"])
    any_empty = any(v.get("status") == "empty" for v in state["step_outputs"].values())
    replan_count = state.get("replan_count", 0)
    
    if replan_count >= 2:
        return {"replan_decision": "finish"}
    
    if any_empty and replan_count < 2:
        prompt = f"""Original plan: {state['plan']}
Step outputs so far: {state['step_outputs']}
Some steps returned empty results. Add 1-2 recovery steps with broader queries.
Return only the new steps to append as JSON array with 'step', 'tool', 'params', 'depends_on' fields."""

        response = _groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        
        try:
            content = response.choices[0].message.content
            json_match = re.search(r'\[[\s\S]*\]', content)
            if json_match:
                new_steps = json.loads(json_match.group())
                offset = len(state["plan"])
                for s in new_steps:
                    s["step"] = s.get("step", offset) + offset
                return {
                    "plan": state["plan"] + new_steps,
                    "replan_count": replan_count + 1,
                    "replan_decision": "continue"
                }
        except:
            pass
    
    if all_done:
        return {"replan_decision": "finish"}
    
    return {"replan_decision": "continue"}

def _build_response(final: str, state: NewsIQState) -> dict:
    """Shared response builder — updates entity memory and messages."""
    entities = extract_entities_from_query(state["resolved_query"])
    return {
        "final_answer": final,
        "entity_memory": {
            "last_entity": entities[0] if entities else state["entity_memory"].get("last_entity"),
            "last_entities": entities,
            "last_task": state.get("intent"),
            "last_result": final
        },
        "messages": [{"role": "assistant", "content": final}]
    }


def synthesizer(state: NewsIQState) -> dict:
    resolved_query = state.get("resolved_query", state.get("user_query", ""))
    intent = state.get("intent", "summarize")
    entity_memory = state.get("entity_memory", {})
    step_outputs = state.get("step_outputs", {})
    
    if state.get("replan_decision") == "out_of_scope":
        final_answer = (
            "I'm a news analysis assistant and don't handle prediction questions like stock prices, "
            "financial forecasts, or investment advice. I can help you with news summaries, "
            "sentiment analysis, entity comparisons, and timelines. Would you like to ask about "
            "recent news on a topic instead?"
        )
        return _build_response(final_answer, state)
    
    all_empty = all(v.get("status") == "empty" for v in step_outputs.values()) if step_outputs else True
    
    if all_empty:
        final_answer = (
            "I wasn't able to find news articles specifically about this query. "
            "Try rephrasing or asking about a broader topic."
        )
        return _build_response(final_answer, state)
    
    last_result = entity_memory.get("last_result", "")
    
    if last_result:
        try:
            followup_prompt = f"""Does this query require fetching NEW information, 
or can it be answered using a prior result?
Query: "{resolved_query}"
Prior result available: "{last_result[:300]}"
Answer with only: NEW or PRIOR"""
            
            followup_response = _groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": followup_prompt}],
                temperature=0.1,
                max_tokens=10
            )
            
            is_prior = followup_response.choices[0].message.content.strip().upper()
            
            if is_prior == "PRIOR":
                prior_prompt = f"""Answer this question using only the prior result below.
Question: {resolved_query}
Prior result: {last_result}
Give a direct, concise answer."""
                
                prior_response = _groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": prior_prompt}],
                    temperature=0.3,
                    max_tokens=1000
                )
                
                final_answer = prior_response.choices[0].message.content or "Unable to generate answer."
                return _build_response(final_answer, state)
        except Exception:
            pass
    
    all_results = []
    for k, v in sorted(step_outputs.items()):
        all_results.append(f"Step {k} ({v.get('tool', 'unknown')}): {v.get('result', '')}")
    
    combined = "\n\n".join(all_results)
    
    prior_results = state.get("prior_entity_results", [])
    prior_context = ""
    if prior_results:
        prior_context = "\n\nPrevious entity results:\n"
        for pe in prior_results:
            prior_context += f"- {pe['entity']}: {pe['result'][:500]}\n"
    
    prompt = f"""Original query: {resolved_query}
Research outputs:
{combined}{prior_context}

Write a clear, structured final answer for the user. Be concise but informative."""

    response = _groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=2000
    )
    
    final_answer = response.choices[0].message.content or "Unable to generate answer."
    
    return _build_response(final_answer, state)

def extract_entities_from_query(query: str) -> list[str]:
    words = query.split()
    entities = [w.strip("'\",.") for w in words if len(w) > 2 and w[0].isupper()]
    return entities[:5]

def infer_task(plan: list[dict]) -> str:
    for step in plan:
        tool = step.get("tool", "")
        if tool == "analyze_text":
            return step.get("params", {}).get("task", "unknown")
        elif tool == "compare_entities":
            return "compare"
    return "unknown"

def turn_initializer(state: NewsIQState) -> dict:
    """Clears per-turn data. Preserves entity_memory and prior_entity_results for session continuity."""
    clear_cache()
    return {
        "plan": [],
        "step_outputs": {},
        "current_step": 0,
        "replan_count": 0,
        "replan_decision": None,
        "final_answer": None,
        "planning_done": False,
        "temporal_constraint": None,
        "api_queries": [],
        "intent": "",
    }

def step_collector(state: NewsIQState) -> dict:
    """Fan-in gate: only proceeds when ALL planned steps are complete."""
    total_steps = len(state["plan"])
    completed_steps = len(state["step_outputs"])
    
    if completed_steps < total_steps:
        return {}
    
    return {"all_steps_complete": True}
