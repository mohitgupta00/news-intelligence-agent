#!/usr/bin/env python3
"""Debug query optimization for sources."""

import sys
import os
import re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def optimize_query_for_source(query: str, source: str) -> str:
    """Optimize query for specific news source."""
    print(f"Optimizing '{query}' for source '{source}'")
    
    if source == 'newsapi':
        # NewsAPI works better with specific entities and keywords
        result = query
        print(f"  NewsAPI: No changes -> '{result}'")
        return result
    elif source == 'gnews':
        # GNews works better with broader terms
        # Remove very specific constraints
        optimized = re.sub(r'\\b(latest|recent|today|yesterday)\\b', '', query, flags=re.IGNORECASE)
        result = optimized.strip() or query
        print(f"  GNews: Removed temporal words -> '{result}'")
        return result
    elif source == 'newsdata':
        # NewsData works better with business/tech terms
        result = query
        print(f"  NewsData: No changes -> '{result}'")
        return result
    
    print(f"  Unknown source: No changes -> '{query}'")
    return query

def test_query_optimization():
    """Test query optimization."""
    
    test_queries = [
        "Israel Iran war news",
        "Israel Iran war latest news", 
        "latest updates on israel iran war"
    ]
    
    sources = ['gnews', 'newsdata', 'newsapi']
    
    for query in test_queries:
        print(f"\\nTesting query: '{query}'")
        print("-" * 40)
        
        for source in sources:
            optimized = optimize_query_for_source(query, source)
            print()

if __name__ == "__main__":
    test_query_optimization()