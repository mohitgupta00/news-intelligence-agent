import asyncio, aiohttp, time, logging, re
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from functools import wraps
from config import NEWSAPI_KEY, GNEWS_KEY, NEWSDATA_KEY, CACHE_TTL_SECONDS
logger = logging.getLogger(__name__)

def extract_keywords(query: str) -> List[str]:
    """Extract meaningful keywords from query."""
    # Remove common stop words and extract meaningful terms
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'about', 'how', 'what', 'when', 'where', 'why'}
    words = re.findall(r'\b\w{3,}\b', query.lower())
    return [w for w in words if w not in stop_words][:4]  # Max 4 keywords

def extract_main_entities(query: str) -> str:
    """Extract main entities for broad search."""
    entity_patterns = {
        'countries': ['israel', 'iran', 'india', 'china', 'usa', 'russia', 'ukraine', 'germany', 'france', 'uk'],
        'companies': ['apple', 'google', 'microsoft', 'tesla', 'amazon', 'meta', 'nvidia', 'openai'],
        'people': ['trump', 'biden', 'putin', 'xi', 'musk', 'bezos', 'gates']
    }
    
    query_lower = query.lower()
    found_entities = []
    
    for category, entities in entity_patterns.items():
        for entity in entities:
            if entity in query_lower:
                found_entities.append(entity.title())
    
    return ' '.join(found_entities[:2]) if found_entities else ' '.join(extract_keywords(query)[:2])

def generate_search_variants(query: str) -> List[str]:
    """Generate multiple search variants for triangulation."""
    variants = [query]  # Original query first
    
    # Extract components
    keywords = extract_keywords(query)
    entities = extract_main_entities(query)
    
    # Variant 2: Main entities only (broader search)
    if entities and entities.strip() != query.strip():
        variants.append(entities)
    
    # Variant 3: Keywords combination
    if len(keywords) >= 2:
        variants.append(' '.join(keywords[:3]))
    
    # Variant 4: Topic-focused (remove specific constraints)
    topic_query = re.sub(r'\b(latest|recent|today|yesterday|this\s+week)\b', '', query, flags=re.IGNORECASE).strip()
    if topic_query and topic_query != query:
        variants.append(topic_query)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_variants = []
    for v in variants:
        v_clean = v.strip()
        if v_clean and v_clean not in seen and len(v_clean) > 2:
            seen.add(v_clean)
            unique_variants.append(v_clean)
    
    return unique_variants[:3]  # Max 3 variants

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
    """Enhanced NewsAPI with encoding fix and comprehensive error handling."""
    try:
        # Handle edge cases
        if not query or len(query.strip()) < 2:
            return None
            
        # Sanitize query for API
        clean_query = ' '.join(query.strip().split())[:100]  # Limit length, clean whitespace
        
        # Progressive date range with encoding fix
        for days_back in [1, 2, 3, 7, 14]:  # Extended range for better coverage
            date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
            
            params = {
                "q": clean_query,
                "pageSize": min(n, 20),  # API limit
                "from": date,
                "sortBy": "publishedAt",
                "apiKey": NEWSAPI_KEY,
                "language": "en"
            }
            
            # Fix encoding issue with explicit headers
            headers = {
                'Accept-Encoding': 'gzip, deflate',  # Avoid 'br' encoding
                'User-Agent': 'NewsIQ/1.0'
            }
            
            async with session.get(
                "https://newsapi.org/v2/everything", 
                params=params, 
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=8)
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"NewsAPI HTTP {resp.status} for query: {clean_query}")
                    continue
                    
                try:
                    data = await resp.json(content_type=None)
                except Exception as json_err:
                    logger.warning(f"NewsAPI JSON decode error: {json_err}")
                    continue
                
                articles = data.get("articles", [])
                
                if articles:
                    valid = []
                    for a in articles:
                        title = a.get("title", "").strip()
                        desc = a.get("description", "").strip()
                        content = a.get("content", "").strip()
                        
                        if title and len(title) > 10:  # Quality filter
                            article_text = f"{title}: {desc or content}"
                            if len(article_text) > 50:  # Substantial content
                                valid.append(article_text)
                    
                    if valid:
                        logger.info(f"NewsAPI: Found {len(valid)} articles from {days_back} days ago")
                        return "\n".join(valid[:n])
        
        # Final attempt without date filter
        params = {
            "q": clean_query, 
            "pageSize": min(n, 10), 
            "sortBy": "relevancy", 
            "apiKey": NEWSAPI_KEY,
            "language": "en"
        }
        
        async with session.get(
            "https://newsapi.org/v2/everything", 
            params=params, 
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=8)
        ) as resp:
            if resp.status == 200:
                try:
                    data = await resp.json(content_type=None)
                    articles = data.get("articles", [])
                    if articles:
                        valid = [f"{a.get('title', '')}: {a.get('description', '')}" 
                               for a in articles if a.get('title') and len(a.get('title', '')) > 10]
                        if valid:
                            logger.info(f"NewsAPI: Found {len(valid)} articles (no date filter)")
                            return "\n".join(valid[:n])
                except Exception:
                    pass
        
        return None
        
    except asyncio.TimeoutError:
        logger.warning(f"NewsAPI timeout for query: {query[:50]}")
        return None
    except Exception as e:
        logger.warning(f"NewsAPI error for '{query[:30]}': {str(e)[:100]}")
        return None

async def _call_newsdata_async(session, query, n):
    """Enhanced NewsData with robust error handling and query optimization."""
    try:
        # Handle edge cases
        if not query or len(query.strip()) < 2:
            return None
            
        # Sanitize and optimize query
        clean_query = ' '.join(query.strip().split())[:200]  # NewsData has higher limits
        
        # Basic parameters without premium features
        params = {
            "q": clean_query,
            "apikey": NEWSDATA_KEY,
            "language": "en",
            "size": min(n * 2, 10)  # Free tier limit
        }
        
        async with session.get(
            "https://newsdata.io/api/1/latest", 
            params=params, 
            timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            if resp.status != 200:
                logger.warning(f"NewsData HTTP {resp.status}: {await resp.text()}")
                return None
                
            try:
                data = await resp.json(content_type=None)
            except Exception as json_err:
                logger.warning(f"NewsData JSON decode error: {json_err}")
                return None
            
            results = data.get("results", [])
            if not results:
                return None
                
            valid = []
            for r in results:
                title = r.get("title", "").strip()
                desc = r.get("description", "").strip()
                content = r.get("content", "").strip()
                
                if title and len(title) > 15:  # Quality filter
                    article_text = f"{title}: {desc or content}"
                    if len(article_text) > 60:  # Substantial content
                        valid.append(article_text)
                        
                if len(valid) >= n:  # Got enough results
                    break
            
            if valid:
                logger.info(f"NewsData: Found {len(valid)} quality articles")
                return "\n".join(valid)
            
            return None
            
    except asyncio.TimeoutError:
        logger.warning(f"NewsData timeout for query: {query[:50]}")
        return None
    except Exception as e:
        logger.warning(f"NewsData error for '{query[:30]}': {str(e)[:100]}")
        return None

async def _call_gnews_async(session, query, n):
    """Enhanced GNews with comprehensive error handling and query optimization."""
    try:
        # Handle edge cases
        if not query or len(query.strip()) < 2:
            return None
            
        # Sanitize query for GNews
        clean_query = ' '.join(query.strip().split())[:100]
        
        # Basic parameters for free tier
        params = {
            "q": clean_query,
            "max": min(n * 2, 10),  # Free tier limit
            "lang": "en",
            "token": GNEWS_KEY
        }
        
        async with session.get(
            "https://gnews.io/api/v4/search", 
            params=params, 
            timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            if resp.status != 200:
                logger.warning(f"GNews HTTP {resp.status}: {await resp.text()}")
                return None
                
            try:
                data = await resp.json(content_type=None)
            except Exception as json_err:
                logger.warning(f"GNews JSON decode error: {json_err}")
                return None
            
            articles = data.get("articles", [])
            if not articles:
                return None
                
            valid = []
            for a in articles:
                title = a.get("title", "").strip()
                desc = a.get("description", "").strip()
                content = a.get("content", "").strip()
                
                if title and len(title) > 10:  # Quality filter
                    article_text = f"{title}: {desc or content}"
                    if len(article_text) > 50:  # Substantial content
                        valid.append(article_text)
                        
                if len(valid) >= n:  # Got enough results
                    break
            
            if valid:
                logger.info(f"GNews: Found {len(valid)} quality articles")
                return "\n".join(valid)
            
            return None
            
    except asyncio.TimeoutError:
        logger.warning(f"GNews timeout for query: {query[:50]}")
        return None
    except Exception as e:
        logger.warning(f"GNews error for '{query[:30]}': {str(e)[:100]}")
        return None

async def fetch_news_with_fallback(query: str, n: int = 5, preferred_sources: list = None) -> Tuple[str, str]:
    """Robust news fetching with comprehensive error handling and source diversity."""
    
    # Early validation and sanitization
    if not query or not isinstance(query, str):
        return "Invalid query provided. Please provide a valid search term.", "validation_error"
    
    query = query.strip()
    if len(query) < 2:
        return "Query too short. Please provide at least 2 characters.", "validation_error"
    
    if len(query) > 500:
        query = query[:500]  # Truncate very long queries
        logger.info(f"Truncated long query to 500 characters")
    
    # Generate search variants with better edge case handling
    search_variants = generate_search_variants(query)
    if not search_variants:
        search_variants = [query]  # Fallback to original
    
    logger.info(f"Generated {len(search_variants)} search variants for '{query[:50]}'")
    
    # Enhanced source selection with diversity
    if preferred_sources:
        source_map = {
            'newsapi': _call_newsapi_async,
            'newsdata': _call_newsdata_async,
            'gnews': _call_gnews_async
        }
        sources = [(source_map[src], src) for src in preferred_sources if src in source_map]
        logger.info(f"Using preferred sources: {preferred_sources}")
    else:
        # Intelligent source ordering with diversity
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['breaking', 'latest', 'today', 'recent', 'urgent']):
            # Real-time queries: prioritize fast sources
            sources = [
                (_call_gnews_async, "gnews"),
                (_call_newsdata_async, "newsdata"),
                (_call_newsapi_async, "newsapi")
            ]
        elif any(word in query_lower for word in ['earnings', 'stock', 'financial', 'business', 'market']):
            # Business queries: prioritize business-focused sources
            sources = [
                (_call_newsdata_async, "newsdata"),
                (_call_gnews_async, "gnews"),
                (_call_newsapi_async, "newsapi")
            ]
        elif any(word in query_lower for word in ['global', 'international', 'world', 'country']):
            # International queries: prioritize global sources
            sources = [
                (_call_gnews_async, "gnews"),
                (_call_newsapi_async, "newsapi"),
                (_call_newsdata_async, "newsdata")
            ]
        else:
            # Balanced approach for general queries
            sources = [
                (_call_newsdata_async, "newsdata"),
                (_call_gnews_async, "gnews"),
                (_call_newsapi_async, "newsapi")
            ]
    
    # Track attempts for debugging
    attempts = []
    
    async with aiohttp.ClientSession() as session:
        # Try each variant with all sources
        for i, variant in enumerate(search_variants):
            logger.debug(f"Trying search variant {i+1}/{len(search_variants)}: '{variant}'")
            
            # Try sources in order for this variant
            for source_func, source_name in sources:
                attempt_key = f"{source_name}_{variant[:20]}"
                start_time = time.time()
                
                try:
                    result = await try_source_with_retry(source_func, session, variant, n)
                    response_time = time.time() - start_time
                    
                    attempts.append({
                        'source': source_name,
                        'variant': variant[:30],
                        'success': bool(result),
                        'response_time': response_time,
                        'content_length': len(result) if result else 0
                    })
                    
                    if result and not _is_likely_hallucinated(result):
                        # Enhanced quality check
                        if len(result.strip()) > 30 and not result.startswith('No recent news'):
                            variant_info = f" (variant: {variant})" if variant != query else ""
                            logger.info(f"Success with {source_name}{variant_info} in {response_time:.2f}s")
                            return result, f"{source_name}{variant_info}"
                    
                except Exception as e:
                    attempts.append({
                        'source': source_name,
                        'variant': variant[:30],
                        'success': False,
                        'error': str(e)[:50],
                        'response_time': time.time() - start_time
                    })
                    logger.warning(f"{source_name} failed for '{variant[:30]}': {str(e)[:50]}")
            
            # Small delay between variants to avoid rate limiting
            if i < len(search_variants) - 1:
                await asyncio.sleep(0.3)
    
    # Enhanced fallback with attempt analysis
    total_attempts = len(attempts)
    successful_attempts = sum(1 for a in attempts if a.get('success', False))
    
    logger.warning(f"All sources failed. Attempts: {successful_attempts}/{total_attempts}")
    
    # Generate contextual fallback message
    keywords = extract_keywords(query)
    entities = extract_main_entities(query)
    
    if entities:
        fallback_msg = f"No recent news found for '{query}'. This might be due to:\n" \
                      f"• Very recent events not yet indexed\n" \
                      f"• Specific search terms too narrow\n" \
                      f"• Try broader terms like '{entities}' or related keywords."
    elif keywords:
        fallback_msg = f"No recent news found for '{query}'. Try:\n" \
                      f"• Broader search terms: '{' '.join(keywords[:2])}'\n" \
                      f"• Different keywords or synonyms\n" \
                      f"• Check spelling and try again later."
    else:
        fallback_msg = f"Unable to find news for '{query}'. Please try:\n" \
                      f"• Different search terms\n" \
                      f"• More specific keywords\n" \
                      f"• Check back later for updated results."
    
    return fallback_msg, f"fallback_after_{total_attempts}_attempts"

async def try_source_with_retry(source_func, session, query, n, max_retries=3):
    """Enhanced retry logic with exponential backoff and circuit breaker pattern."""
    for attempt in range(max_retries):
        try:
            # Exponential backoff with jitter
            if attempt > 0:
                delay = (0.5 * (2 ** attempt)) + (0.1 * attempt)  # 0.6s, 1.1s, 2.2s
                await asyncio.sleep(delay)
            
            result = await source_func(session, query, n)
            
            # Enhanced quality validation
            if result and isinstance(result, str):
                result = result.strip()
                if len(result) > 30 and not result.startswith('Error') and ':' in result:
                    return result
            
        except asyncio.TimeoutError:
            logger.warning(f"Timeout on attempt {attempt + 1}/{max_retries} for query: {query[:30]}")
            if attempt == max_retries - 1:
                return None
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)[:50]}")
            if attempt == max_retries - 1:
                return None
    
    return None

# Backward compatibility
async def fetch_news_async(query, n=5, max_retries=2, preferred_sources=None):
    """Backward compatible wrapper."""
    return await fetch_news_with_fallback(query, n, preferred_sources)

def fetch_news(query, n=5):
    """Sync wrapper for backward-compat."""
    try: return asyncio.run(fetch_news_async(query,n))
    except RuntimeError:
        import nest_asyncio; nest_asyncio.apply()
        return asyncio.run(fetch_news_async(query,n))
