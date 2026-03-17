"""Planning nodes: plan creation, routing, step collection, and replanning."""

import json
import re
import logging
from groq import Groq
from langgraph.constants import Send

from config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)
_groq_client = Groq(api_key=GROQ_API_KEY)

def planner(state):
    """Create execution plan based on intent and queries."""
    if state.get("planning_done") and state.get("plan"):
        return {"planning_done": True}
    
    resolved = state["resolved_query"]
    api_queries = state.get("api_queries", [resolved])
    intent = state.get("intent", "summarize")
    temporal = state.get("temporal_constraint", "") or ""
    
    temporal_suffix = f" {temporal}" if temporal else ""
    
    if intent == "compare" and len(api_queries) == 2:
        plan = [{
            "step": 0,
            "tool": "compare_entities",
            "params": {"entity_a": api_queries[0], "entity_b": api_queries[1]},
            "depends_on": []
        }]
    elif intent == "timeline":
        plan = [
            {
                "step": 0,
                "tool": "fetch_news",
                "params": {"query": api_queries[0] + temporal_suffix, "n": 7},
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
        # Fetch news for each query
        plan = [
            {
                "step": i,
                "tool": "fetch_news",
                "params": {"query": query, "n": 5},
                "depends_on": []
            }
            for i, query in enumerate(api_queries)
        ]
        # Add analysis step that depends on all fetch steps
        plan.append({
            "step": len(api_queries),
            "tool": "analyze_text",
            "params": {"task": intent},
            "depends_on": list(range(len(api_queries)))
        })
    else:
        # Default plan
        plan = [
            {
                "step": 0,
                "tool": "fetch_news",
                "params": {"query": api_queries[0] + temporal_suffix, "n": 5},
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