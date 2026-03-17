"""Query caching utilities for fast query resolution."""

import time
import hashlib
from typing import Optional, Dict, Tuple
from utils.text_processing import get_embedder, cosine_similarity

# Global query cache
_query_cache: Dict[str, Tuple[str, float]] = {}  # hash -> (resolved_query, timestamp)
_CACHE_TTL = 3600  # 1 hour
_SIMILARITY_THRESHOLD = 0.85

def _hash_query(query: str) -> str:
    """Create a hash for the query."""
    return hashlib.md5(query.lower().strip().encode()).hexdigest()

def _clean_expired_cache():
    """Remove expired entries from cache."""
    current_time = time.time()
    expired_keys = [
        key for key, (_, timestamp) in _query_cache.items()
        if current_time - timestamp > _CACHE_TTL
    ]
    for key in expired_keys:
        del _query_cache[key]

def _find_similar_cached_query(query: str) -> Optional[str]:
    """Find a similar cached query using embeddings or keyword matching."""
    embedder = get_embedder()
    
    if embedder and _query_cache:
        # Use semantic similarity
        query_embedding = embedder.encode([query])[0]
        cached_queries = list(_query_cache.keys())
        
        if cached_queries:
            cached_embeddings = embedder.encode(cached_queries)
            
            for i, cached_query in enumerate(cached_queries):
                similarity = cosine_similarity(query_embedding, cached_embeddings[i])
                if similarity >= _SIMILARITY_THRESHOLD:
                    return cached_query
    else:
        # Fallback to keyword matching
        query_words = set(query.lower().split())
        
        for cached_query in _query_cache.keys():
            cached_words = set(cached_query.lower().split())
            if query_words and cached_words:
                overlap = len(query_words & cached_words)
                similarity = overlap / max(len(query_words), len(cached_words))
                if similarity >= 0.7:  # Lower threshold for keyword matching
                    return cached_query
    
    return None

def get_cached_resolution(query: str) -> Optional[str]:
    """
    Get cached query resolution if available and similar.
    
    Args:
        query: The query to resolve
        
    Returns:
        Cached resolved query if found, None otherwise
    """
    _clean_expired_cache()
    
    # Check exact match first
    query_hash = _hash_query(query)
    if query_hash in _query_cache:
        resolved_query, _ = _query_cache[query_hash]
        return resolved_query
    
    # Check for similar queries
    similar_query = _find_similar_cached_query(query)
    if similar_query:
        resolved_query, _ = _query_cache[_hash_query(similar_query)]
        return resolved_query
    
    return None

def cache_query_resolution(original_query: str, resolved_query: str):
    """
    Cache a query resolution.
    
    Args:
        original_query: The original user query
        resolved_query: The resolved/rewritten query
    """
    query_hash = _hash_query(original_query)
    _query_cache[query_hash] = (resolved_query, time.time())

def clear_query_cache():
    """Clear the entire query cache."""
    global _query_cache
    _query_cache = {}

def get_cache_stats() -> Dict[str, int]:
    """Get cache statistics."""
    _clean_expired_cache()
    return {
        "total_entries": len(_query_cache),
        "cache_size_kb": len(str(_query_cache)) // 1024
    }