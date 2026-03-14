import asyncio, aiohttp, time, logging
from typing import Optional
from datetime import datetime, timedelta
from functools import wraps
from config import NEWSAPI_KEY, GNEWS_KEY, NEWSDATA_KEY, CACHE_TTL_SECONDS
logger = logging.getLogger(__name__)

def retry_on_error(max_retries=3, delay=1.0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try: return func(*args, **kwargs)
                except Exception as e:
                    time.sleep(delay*(2**attempt))
            return None
        return wrapper
    return decorator

def _is_likely_hallucinated(text):
    if not text: return True
    cy = datetime.now().year
    flags = [str(cy+i) for i in range(1,4)]+["unknown date","pre-202","note:","this timeline","the timeline only includes","may not be an exhaustive"]
    return sum(1 for i in flags if i in text.lower()) >= 2

async def _call_newsapi_async(session, query, n):
    try:
        date=(datetime.now()-timedelta(days=2)).strftime("%Y-%m-%d")
        async with session.get("https://newsapi.org/v2/everything",params={"q":query,"pageSize":n,"from":date,"sortBy":"publishedAt","apiKey":NEWSAPI_KEY},timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status!=200: return None
            data=await resp.json(content_type=None)
            valid=[]
            for a in data.get("articles",[]):
                t=a.get("title")
                if not t: continue
                valid.append(f"{t}: {a.get('description') or a.get('content','')}")
            return "\n".join(valid) if valid else None
    except Exception as e:
        logger.warning(f"NewsAPI err: {e}"); return None

async def _call_newsdata_async(session, query, n):
    try:
        async with session.get("https://newsdata.io/api/1/latest",params={"q":query,"apikey":NEWSDATA_KEY,"language":"en","category":"top,technology,business"},timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status!=200: return None
            data=await resp.json(content_type=None)
            valid=[]
            for r in data.get("results",[]):
                t=r.get("title")
                if not t: continue
                valid.append(f"{t}: {r.get('description') or r.get('content','')}")
            return "\n".join(valid[:n]) if valid else None
    except Exception as e:
        logger.warning(f"NewsData err: {e}"); return None

async def _call_gnews_async(session, query, n):
    try:
        async with session.get("https://gnews.io/api/v4/search",params={"q":query,"max":n,"lang":"en","token":GNEWS_KEY},timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status!=200: return None
            data=await resp.json(content_type=None)
            valid=[]
            for a in data.get("articles",[]):
                t=a.get("title")
                if not t: continue
                valid.append(f"{t}: {a.get('description') or a.get('content','')}")
            return "\n".join(valid) if valid else None
    except Exception as e:
        logger.warning(f"GNews err: {e}"); return None

async def fetch_news_async(query, n=5):
    """Concurrent fetch from all 3 sources via aiohttp."""
    async with aiohttp.ClientSession() as session:
        results=await asyncio.gather(
            _call_newsapi_async(session,query,n),
            _call_newsdata_async(session,query,n),
            _call_gnews_async(session,query,n),
            return_exceptions=True)
    for result,source in zip(results,["newsapi","newsdata","gnews"]):
        if isinstance(result,str) and result and not _is_likely_hallucinated(result):
            return result,source
    return "","empty"

def fetch_news(query, n=5):
    """Sync wrapper for backward-compat."""
    try: return asyncio.run(fetch_news_async(query,n))
    except RuntimeError:
        import nest_asyncio; nest_asyncio.apply()
        return asyncio.run(fetch_news_async(query,n))
