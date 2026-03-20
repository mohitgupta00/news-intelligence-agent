#!/usr/bin/env python3
"""Direct test of fetch_news_with_fallback."""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.fetch_news import fetch_news_with_fallback

async def test_direct_fetch():
    """Test fetch_news_with_fallback directly."""
    
    query = "Israel Iran war news"
    preferred_sources = ['gnews', 'newsdata']
    
    print(f"Testing direct fetch with:")
    print(f"  Query: '{query}'")
    print(f"  Sources: {preferred_sources}")
    print("=" * 50)
    
    result, source = await fetch_news_with_fallback(query, n=3, preferred_sources=preferred_sources)
    
    print(f"Result source: {source}")
    print(f"Result length: {len(result)} chars")
    print(f"First 200 chars: {result[:200]}...")
    
    # Check if result contains relevant keywords
    relevant_keywords = ['israel', 'iran', 'war', 'conflict']
    found_keywords = [kw for kw in relevant_keywords if kw.lower() in result.lower()]
    print(f"Relevant keywords found: {found_keywords}")

if __name__ == "__main__":
    asyncio.run(test_direct_fetch())