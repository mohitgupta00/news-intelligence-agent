#!/usr/bin/env python3
"""Debug the planning step."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from graph.modules.planning import planner, select_optimal_sources, optimize_query_for_source

def test_planning():
    """Test the planning step."""
    
    # Simulate state after query resolution and rewriting
    state = {
        "resolved_query": "Israel Iran war latest news",
        "api_queries": ["Israel Iran war news"],  # From query rewriter
        "intent": "summarize",
        "temporal_constraint": None,
        "context_hints": {},
        "planning_done": False,
        "plan": []
    }
    
    print("Input state:")
    print(f"  resolved_query: '{state['resolved_query']}'")
    print(f"  api_queries: {state['api_queries']}")
    print(f"  intent: {state['intent']}")
    print()
    
    # Test planning
    result = planner(state)
    
    print("Planning result:")
    print(f"  plan: {result['plan']}")
    print()
    
    # Check each step in the plan
    for i, step in enumerate(result['plan']):
        print(f"Step {i}:")
        print(f"  tool: {step['tool']}")
        print(f"  params: {step['params']}")
        
        if step['tool'] == 'fetch_news':
            query = step['params']['query']
            sources = step['params'].get('preferred_sources', [])
            print(f"  -> Will fetch news for: '{query}' using sources: {sources}")

if __name__ == "__main__":
    test_planning()