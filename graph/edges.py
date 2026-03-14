from graph.state import NewsIQState

def after_guard(state):
    """Route OOS queries to synthesizer; all others to planner."""
    return "synthesizer" if state.get("replan_decision")=="out_of_scope" else "planner"

def after_replanner(state):
    decision=state.get("replan_decision","finish")
    if decision in ("finish","out_of_scope"): return "synthesizer"
    return "planner"
