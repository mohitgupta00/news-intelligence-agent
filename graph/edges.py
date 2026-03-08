from typing import Union
from graph.state import NewsIQState

def should_route_to_tools(state: NewsIQState) -> str:
    if state.get("replan_decision") == "out_of_scope":
        return "synthesizer"
    
    pending_steps = [s for s in state.get("plan", []) if s["step"] not in state.get("step_outputs", {})]
    if not pending_steps:
        return "replanner"
    
    next_step = pending_steps[0]
    tool = next_step.get("tool", "")
    
    if tool == "fetch_news":
        return "fetch_news"
    elif tool == "analyze_text":
        return "analyze_text"
    elif tool == "compare_entities":
        return "compare_entities"
    else:
        return "replanner"

def after_replanner(state: NewsIQState) -> str:
    decision = state.get("replan_decision", "finish")
    if decision == "finish":
        return "synthesizer"
    if decision == "out_of_scope":
        return "synthesizer"
    return "planner"
