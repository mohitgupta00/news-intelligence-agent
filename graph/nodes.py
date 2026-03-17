"""
Streamlined nodes module - imports from focused modules.
This file now serves as a clean interface to the modular architecture.
"""

# Query Processing
from graph.modules.query_processing import (
    turn_initializer,
    query_resolver, 
    query_rewriter,
    guard_node
)

# Planning
from graph.modules.planning import (
    planner,
    router,
    step_collector,
    replanner
)

# Execution
from graph.modules.execution import (
    fetch_news_node,
    analyze_text_node,
    compare_entities_node
)

# Synthesis
from graph.modules.synthesis import synthesizer

# Export all nodes for backward compatibility
__all__ = [
    'turn_initializer',
    'query_resolver',
    'query_rewriter', 
    'guard_node',
    'planner',
    'router',
    'step_collector',
    'replanner',
    'fetch_news_node',
    'analyze_text_node',
    'compare_entities_node',
    'synthesizer'
]