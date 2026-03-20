#!/usr/bin/env python3
"""Debug script to test news fetching APIs directly."""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.fetch_news import fetch_news_with_fallback

async def test_news_apis():
    """Test news APIs with Israel-Iran query."""
    query = "Israel Iran war latest news"
    print(f"Testing query: '{query}'")
    print("=" * 50)
    
    # Test with different source preferences
    sources_to_test = [
        ['newsapi'],
        ['gnews'], 
        ['newsdata'],
        ['gnews', 'newsdata'],  # Default preference
    ]
    
    for i, preferred_sources in enumerate(sources_to_test):
        print(f"\n{i+1}. Testing with sources: {preferred_sources}")
        print("-" * 30)
        
        try:
            result, source = await fetch_news_with_fallback(
                query, 
                n=3, 
                preferred_sources=preferred_sources
            )
            
            print(f"Source: {source}")
            print(f"Result length: {len(result)} chars")
            print(f"First 200 chars: {result[:200]}...")
            
            # Check if result contains relevant keywords
            relevant_keywords = ['israel', 'iran', 'war', 'conflict', 'middle east']
            found_keywords = [kw for kw in relevant_keywords if kw.lower() in result.lower()]
            print(f"Relevant keywords found: {found_keywords}")
            
        except Exception as e:
            print(f"Error: {e}")
        
        print()

if __name__ == "__main__":
    asyncio.run(test_news_apis())