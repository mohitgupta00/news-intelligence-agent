from typing import Optional
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL
from tools.fetch_news import fetch_news

_groq_client = Groq(api_key=GROQ_API_KEY)

def compare_entities(entity_a: str, entity_b: str, n: int = 5, state: dict = None) -> str:
    session_cache = state.get("session_cache", {}) if state else {}
    
    cache_key_a = f"fetch::{entity_a}"
    cache_key_b = f"fetch::{entity_b}"
    
    if cache_key_a in session_cache:
        news_a = session_cache[cache_key_a]
    else:
        news_a, _ = fetch_news(entity_a, n=n, use_cache=False)
        if news_a:
            session_cache[cache_key_a] = news_a
    
    if cache_key_b in session_cache:
        news_b = session_cache[cache_key_b]
    else:
        news_b, _ = fetch_news(entity_b, n=n, use_cache=False)
        if news_b:
            session_cache[cache_key_b] = news_b
    
    if not news_a and not news_b:
        return "Unable to fetch news for both entities."
    
    if not news_a:
        return f"Unable to fetch news for {entity_a}. Only {entity_b} news available."
    
    if not news_b:
        return f"Unable to fetch news for {entity_b}. Only {entity_a} news available."
    
    prompt = f"""Compare these two entities based on their recent news coverage.

Entity A ({entity_a}):
{news_a}

Entity B ({entity_b}):
{news_b}

Provide a comparison with:
1. Overall tone for each entity (positive/negative/neutral)
2. Key themes and topics for each
3. Key differences in news coverage
4. Any notable conflicts or contrasting viewpoints"""

    response = _groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1500
    )
    
    result = response.choices[0].message.content or ""
    
    if state is not None and session_cache:
        state["session_cache"] = session_cache
    
    return result
