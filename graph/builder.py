import os
from langgraph.graph import StateGraph, START, END
from graph.state import NewsIQState
from graph.nodes import turn_initializer, query_resolver, query_rewriter, guard_node, planner, router, fetch_news_node, analyze_text_node, compare_entities_node, replanner, synthesizer, step_collector
from graph.edges import after_guard, after_replanner

def build_graph():
    builder=StateGraph(NewsIQState)
    builder.add_node("turn_initializer",turn_initializer)
    builder.add_node("query_resolver",query_resolver)
    builder.add_node("query_rewriter",query_rewriter)
    builder.add_node("guard_node",guard_node)
    builder.add_node("planner",planner)
    builder.add_node("step_collector",step_collector)
    builder.add_node("fetch_news",fetch_news_node)
    builder.add_node("analyze_text",analyze_text_node)
    builder.add_node("compare_entities",compare_entities_node)
    builder.add_node("replanner",replanner)
    builder.add_node("synthesizer",synthesizer)
    builder.add_edge(START,"turn_initializer")
    builder.add_edge("turn_initializer","query_resolver")
    builder.add_edge("query_resolver","query_rewriter")
    builder.add_edge("query_rewriter","guard_node")
    builder.add_conditional_edges("guard_node",after_guard,["planner","synthesizer"])
    builder.add_conditional_edges("planner",router)
    builder.add_edge("fetch_news","step_collector")
    builder.add_edge("analyze_text","step_collector")
    builder.add_edge("compare_entities","step_collector")
    builder.add_edge("step_collector","replanner")
    builder.add_conditional_edges("replanner",after_replanner,["planner","synthesizer"])
    builder.add_edge("synthesizer",END)
    return builder

def compile_graph():
    builder=build_graph()
    db_path=os.environ.get("CHECKPOINT_DB","newsiq_checkpoints.db")
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
        checkpointer=SqliteSaver.from_conn_string(db_path)
    except Exception:
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer=MemorySaver()
    return builder.compile(checkpointer=checkpointer)

graph=compile_graph()
