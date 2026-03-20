#!/usr/bin/env python3
"""Debug the full orchestrator pipeline."""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main_orchestrator import orchestrator

async def test_full_pipeline():
    """Test the full pipeline with Israel-Iran query."""
    query = "latest updates on israel iran war"
    thread_id = "debug-test"
    
    print(f"Testing full pipeline with query: '{query}'")
    print("=" * 60)
    
    try:
        result = await orchestrator.process_query(query, thread_id)
        
        print(f"Routing Decision: {result['routing_decision']}")
        print(f"Reasoning: {result['reasoning']}")
        print(f"Original Query: {result['original_query']}")
        print(f"Resolved Query: {result['resolved_query']}")
        print(f"Processing Time: {result['processing_time']:.2f}s")
        print(f"Fallback Used: {result.get('fallback_used', False)}")
        print()
        print("Response:")
        print("-" * 40)
        print(result['response'])
        
    except Exception as e:
        print(f"Error in full pipeline: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_full_pipeline())