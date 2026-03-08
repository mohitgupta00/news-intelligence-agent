import requests
import time
from typing import Optional
from datetime import datetime
from config import (
    NEWSAPI_KEY, GNEWS_KEY, NEWSDATA_KEY, CACHE_TTL_SECONDS
)

_session_cache: dict = {}
_cache_timestamps: dict = {}

def _is_cache_valid(key: str) -> bool:
    if key not in _cache_timestamps:
        return False
    return time.time() - _cache_timestamps[key] < CACHE_TTL_SECONDS

def _get_cache(key: str) -> Optional[str]:
    if key in _session_cache and _is_cache_valid(key):
        return _session_cache[key]
    return None

def _is_likely_hallucinated(text: str) -> bool:
    """Check for patterns that indicate likely hallucinated or stale content."""
    if not text:
        return True
    
    current_year = datetime.now().year
    
    hallucination_indicators = [
        str(current_year + 1),
        str(current_year + 2),
        str(current_year + 3),
        "unknown date",
        "pre-202",
        "note:",
        "this timeline",
        "the timeline only includes",
        "may not be an exhaustive",
    ]
    
    text_lower = text.lower()
    matches = sum(1 for indicator in hallucination_indicators if indicator in text_lower)
    
    if matches >= 2:
        return True
    
    return False

def _set_cache(key: str, value: str) -> None:
    _session_cache[key] = value
    _cache_timestamps[key] = time.time()

def clear_cache() -> None:
    _session_cache.clear()
    _cache_timestamps.clear()

def call_newsapi(query: str, n: int = 5) -> Optional[str]:
    try:
        from datetime import datetime, timedelta
        date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
                "pageSize": n,
                "from": date,
                "sortBy": "publishedAt",
                "apiKey": NEWSAPI_KEY
            },
            timeout=10
        )
        if resp.status_code != 200:
            return None
        articles = resp.json().get("articles", [])
        if not articles:
            return None
        valid_articles = []
        for a in articles:
            title = a.get("title")
            if not title:
                continue
            pub_date = a.get("publishedAt", "")
            if pub_date:
                try:
                    pub_dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                    age_days = (datetime.now(pub_dt.tzinfo) - pub_dt).days
                    if age_days > 7:
                        continue
                except:
                    pass
            desc = a.get("description") or a.get("content", "")
            valid_articles.append(f"{title}: {desc}")
        if not valid_articles:
            return None
        return "\n".join(valid_articles)
    except Exception as e:
        print(f"NewsAPI error: {e}")
        return None

def call_newsdata(query: str, n: int = 5) -> Optional[str]:
    try:
        from datetime import datetime, timedelta
        resp = requests.get(
            "https://newsdata.io/api/1/latest",
            params={
                "q": query,
                "apikey": NEWSDATA_KEY,
                "language": "en",
                "category": "top,technology,business"
            },
            timeout=10
        )
        if resp.status_code != 200:
            return None
        results = resp.json().get("results", [])
        if not results:
            return None
        valid_results = []
        for r in results:
            title = r.get("title")
            if not title:
                continue
            pub_date = r.get("pubDate", "")
            if pub_date:
                try:
                    pub_dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                    age_days = (datetime.now(pub_dt.tzinfo) - pub_dt).days
                    if age_days > 7:
                        continue
                except:
                    pass
            desc = r.get("description") or r.get("content", "")
            valid_results.append(f"{title}: {desc}")
        if not valid_results:
            return None
        return "\n".join(valid_results[:n])
    except Exception as e:
        print(f"NewsData.io error: {e}")
        return None

def call_gnews(query: str, n: int = 5) -> Optional[str]:
    try:
        from datetime import datetime
        resp = requests.get(
            "https://gnews.io/api/v4/search",
            params={"q": query, "max": n, "lang": "en", "token": GNEWS_KEY},
            timeout=10
        )
        if resp.status_code != 200:
            return None
        articles = resp.json().get("articles", [])
        if not articles:
            return None
        valid_articles = []
        for a in articles:
            title = a.get("title")
            if not title:
                continue
            pub_date = a.get("publishedAt", "")
            if pub_date:
                try:
                    pub_dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                    age_days = (datetime.now(pub_dt.tzinfo) - pub_dt).days
                    if age_days > 7:
                        continue
                except:
                    pass
            desc = a.get("description") or a.get("content", "")
            valid_articles.append(f"{title}: {desc}")
        if not valid_articles:
            return None
        return "\n".join(valid_articles)
    except Exception as e:
        print(f"GNews error: {e}")
        return None

def query_gdelt(query: str) -> Optional[str]:
    try:
        resp = requests.get(
            "https://api.gdeltproject.org/api/v2/doc/doc",
            params={
                "query": query,
                "mode": "TimelineVol",
                "format": "json",
                "TIMESPAN": "7d"
            },
            timeout=15
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data or "timeline" not in data:
            return None
        timeline = data.get("timeline", [])
        if not timeline:
            return None
        volume_data = timeline[0].get("data", [])
        formatted = []
        for item in volume_data[:20]:
            formatted.append(f"Date: {item.get('date', 'N/A')}, Volume: {item.get('value', 0)}")
        return "\n".join(formatted)
    except Exception as e:
        print(f"GDELT error: {e}")
        return None

def fetch_news(query: str, n: int = 5, use_cache: bool = True) -> tuple[str, str]:
    cache_key = f"fetch::{query}::{n}"
    
    if use_cache:
        cached = _get_cache(cache_key)
        if cached and not _is_likely_hallucinated(cached):
            return cached, "cache"
    
    # Primary: NewsAPI (best quality)
    result = call_newsapi(query, n)
    if result and not _is_likely_hallucinated(result):
        _set_cache(cache_key, result)
        return result, "newsapi"
    
    # Fallback: NewsData.io
    result = call_newsdata(query, n)
    if result and not _is_likely_hallucinated(result):
        _set_cache(cache_key, result)
        return result, "newsdata"
    
    # Fallback: GNews
    result = call_gnews(query, n)
    if result and not _is_likely_hallucinated(result):
        _set_cache(cache_key, result)
        return result, "gnews"
    
    return "", "empty"
