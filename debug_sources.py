#!/usr/bin/env python3
"""Debug source selection logic."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from graph.modules.planning import select_optimal_sources

def test_source_selection():
    """Test source selection for Israel-Iran query."""
    
    test_queries = [
        "latest updates on israel iran war",
        "Israel Iran war latest news", 
        "israel iran conflict",
        "breaking news israel iran"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 40)
        
        # Test with summarize intent (default)
        sources = select_optimal_sources(query, "summarize")
        print(f"Selected sources: {sources}")
        
        # Show scoring breakdown
        query_lower = query.lower()
        
        source_patterns = {
            'gnews': {
                'patterns': ['breaking', 'latest', 'today', 'recent', 'global', 'international', 'worldwide'],
                'entities': ['china', 'europe', 'asia', 'russia', 'ukraine', 'israel', 'iran'],
                'topics': ['war', 'conflict', 'climate', 'economy']
            },
            'newsdata': {
                'patterns': ['business', 'market', 'stock', 'earnings', 'financial', 'technology'],
                'entities': ['apple', 'google', 'microsoft', 'tesla', 'amazon', 'meta'],
                'topics': ['tech', 'innovation', 'ai', 'startup', 'company']
            },
            'newsapi': {
                'patterns': ['update', 'report', 'analysis', 'policy'],
                'entities': ['usa', 'america', 'us', 'trump', 'biden'],
                'topics': ['politics', 'election', 'government']
            }
        }
        
        source_scores = {}
        for source, criteria in source_patterns.items():
            score = 0
            matches = []
            
            # Pattern matching
            for pattern in criteria['patterns']:
                if pattern in query_lower:
                    score += 3
                    matches.append(f"pattern:{pattern}")
            
            # Entity matching  
            for entity in criteria['entities']:
                if entity in query_lower:
                    score += 2
                    matches.append(f"entity:{entity}")
            
            # Topic matching
            for topic in criteria['topics']:
                if topic in query_lower:
                    score += 1
                    matches.append(f"topic:{topic}")
            
            # Real-time boost
            if any(word in query_lower for word in ['breaking', 'latest', 'today', 'recent']):
                if source == 'gnews':
                    score += 2
                    matches.append("realtime_boost:+2")
                elif source == 'newsdata':
                    score += 1
                    matches.append("realtime_boost:+1")
                elif source == 'newsapi':
                    score -= 1
                    matches.append("realtime_penalty:-1")
            
            source_scores[source] = score
            print(f"  {source}: {score} points - {matches}")

if __name__ == "__main__":
    test_source_selection()