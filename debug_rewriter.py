#!/usr/bin/env python3
"""Debug the query rewriter."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from typing import Literal
from config import GROQ_API_KEY, GROQ_MODEL

class QueryAnalysis(BaseModel):
    intent: Literal["summarize", "sentiment", "timeline", "compare", "extract_entities"]
    api_queries: list[str] = Field(min_items=1, max_items=3)

def test_query_rewriter():
    """Test the query rewriter with Israel-Iran query."""
    
    _chat_groq = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL, temperature=0.1)
    structured = _chat_groq.with_structured_output(QueryAnalysis)
    
    resolved = "Israel Iran war latest news"
    
    prompt = f"""Analyze user query and determine:
1. intent: summarize|sentiment|timeline|compare|extract_entities
   - Use 'summarize' for ALL informational, factual, multi-part, or mixed queries (DEFAULT)
   - Use 'sentiment' ONLY when user uses words like: sentiment, opinion, reception, how is X perceived, what do people think
   - NEVER use 'sentiment' for 'what happened', 'what is X doing', 'tell me about' queries
2. api_queries: 1-3 clean 2-5 word keyword strings
   - Each query MUST include the main entity name (e.g. 'Trump Epstein files' not 'Epstein connection')
   - For multi-part queries, generate one focused query per sub-topic

CRITICAL: for compare queries with 2 entities, produce EXACTLY 2 separate queries.

Examples:
  'Compare Google and Microsoft' -> intent=compare, api_queries=['Google news','Microsoft news']
  'Summarize latest OpenAI news' -> intent=summarize, api_queries=['OpenAI news']
  'What is Trump doing? What about his Epstein connection?' -> intent=summarize, api_queries=['Trump latest news','Trump Epstein files']

User query: "{resolved}\""""
    
    print(f"Testing query rewriter with: '{resolved}'")
    print("=" * 50)
    print("Prompt:")
    print(prompt)
    print("\n" + "=" * 50)
    
    try:
        result = structured.invoke(prompt)
        print(f"Intent: {result.intent}")
        print(f"API Queries: {result.api_queries}")
        
        # Check if the API queries are reasonable
        for i, query in enumerate(result.api_queries):
            print(f"  Query {i+1}: '{query}' (length: {len(query)} chars)")
            
            # Check if it contains key entities
            key_entities = ['israel', 'iran', 'war', 'conflict']
            found_entities = [e for e in key_entities if e.lower() in query.lower()]
            print(f"    Contains entities: {found_entities}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_query_rewriter()