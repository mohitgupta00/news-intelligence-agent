from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from graph.state import NewsIQState
from graph.nodes import (
    query_resolver, query_rewriter, planner, router,
    fetch_news_node, analyze_text_node, compare_entities_node,
    replanner, synthesizer, turn_initializer, step_collector
)
from graph.edges import after_replanner

def build_graph() -> StateGraph:
    builder = StateGraph(NewsIQState)
    
    builder.add_node("turn_initializer", turn_initializer)
    builder.add_node("query_resolver", query_resolver)
    builder.add_node("query_rewriter", query_rewriter)
    builder.add_node("planner", planner)
    builder.add_node("step_collector", step_collector)
    builder.add_node("fetch_news", fetch_news_node)
    builder.add_node("analyze_text", analyze_text_node)
    builder.add_node("compare_entities", compare_entities_node)
    builder.add_node("replanner", replanner)
    builder.add_node("synthesizer", synthesizer)
    
    builder.add_edge(START, "turn_initializer")
    builder.add_edge("turn_initializer", "query_resolver")
    builder.add_edge("query_resolver", "query_rewriter")
    builder.add_edge("query_rewriter", "planner")
    
    builder.add_conditional_edges("planner", router)
    
    builder.add_edge("fetch_news", "step_collector")
    builder.add_edge("analyze_text", "step_collector")
    builder.add_edge("compare_entities", "step_collector")
    
    builder.add_edge("step_collector", "replanner")
    
    builder.add_conditional_edges("replanner", after_replanner, ["planner", "synthesizer"])
    
    builder.add_edge("synthesizer", END)
    
    return builder

def compile_graph() -> StateGraph:
    builder = build_graph()
    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)

graph = compile_graph()
