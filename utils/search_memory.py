"""Persistent search memory for preserving search results across conversation turns."""

import time
import hashlib
from typing import Dict, List, Optional, Tuple
from utils.text_processing import get_embedder, cosine_similarity

# Global search memory
_search_memory: Dict[str, Dict] = {}  # thread_id -> search_data
_SEARCH_MEMORY_TTL = 3600  # 1 hour
_SIMILARITY_THRESHOLD = 0.75

class SearchResult:
    """Represents a cached search result."""
    def __init__(self, query: str, result: str, timestamp: float, metadata: dict = None):
        self.query = query
        self.result = result
        self.timestamp = timestamp
        self.metadata = metadata or {}
        self.hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute hash for the search result."""
        content = f"{self.query}:{self.result[:200]}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def is_expired(self) -> bool:
        """Check if search result has expired."""
        return time.time() - self.timestamp > _SEARCH_MEMORY_TTL
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            'query': self.query,
            'result': self.result,
            'timestamp': self.timestamp,
            'metadata': self.metadata,
            'hash': self.hash
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create SearchResult from dictionary."""
        return cls(
            query=data['query'],
            result=data['result'], 
            timestamp=data['timestamp'],
            metadata=data.get('metadata', {})
        )

def _get_thread_memory(thread_id: str) -> Dict:
    """Get or create memory for a thread."""
    if thread_id not in _search_memory:
        _search_memory[thread_id] = {
            'searches': [],
            'last_cleanup': time.time()
        }
    return _search_memory[thread_id]

def _cleanup_expired_searches(thread_memory: Dict):
    """Remove expired searches from memory."""
    current_time = time.time()
    
    # Only cleanup every 5 minutes
    if current_time - thread_memory.get('last_cleanup', 0) < 300:
        return
    
    thread_memory['searches'] = [
        search for search in thread_memory['searches']
        if not SearchResult(**search).is_expired()
    ]
    thread_memory['last_cleanup'] = current_time

def _find_similar_search(query: str, thread_memory: Dict) -> Optional[SearchResult]:
    """Find similar cached search using embeddings or keyword matching."""
    searches = thread_memory.get('searches', [])
    if not searches:
        return None
    
    embedder = get_embedder()
    
    if embedder:
        # Use semantic similarity
        try:
            query_embedding = embedder.encode([query])[0]
            cached_queries = [search['query'] for search in searches]
            cached_embeddings = embedder.encode(cached_queries)
            
            for i, search_data in enumerate(searches):
                similarity = cosine_similarity(query_embedding, cached_embeddings[i])
                if similarity >= _SIMILARITY_THRESHOLD:
                    return SearchResult.from_dict(search_data)
        except:
            pass
    
    # Fallback to keyword matching
    query_words = set(query.lower().split())
    
    for search_data in searches:
        cached_words = set(search_data['query'].lower().split())
        if query_words and cached_words:
            overlap = len(query_words & cached_words)
            similarity = overlap / max(len(query_words), len(cached_words))
            if similarity >= 0.6:  # Lower threshold for keyword matching
                return SearchResult.from_dict(search_data)
    
    return None

def store_search_result(thread_id: str, query: str, result: str, metadata: dict = None):
    """Store a search result in persistent memory."""
    if not result:  # Don't store empty results
        return
    
    thread_memory = _get_thread_memory(thread_id)
    _cleanup_expired_searches(thread_memory)
    
    search_result = SearchResult(query, result, time.time(), metadata)
    
    # Check if we already have this exact search
    existing_hashes = {search.get('hash', '') for search in thread_memory['searches']}
    if search_result.hash in existing_hashes:
        return
    
    # Add new search result
    thread_memory['searches'].append(search_result.to_dict())
    
    # Keep only last 20 searches per thread to prevent memory bloat
    if len(thread_memory['searches']) > 20:
        thread_memory['searches'] = thread_memory['searches'][-20:]

def get_relevant_search_results(thread_id: str, query: str, max_results: int = 3) -> List[SearchResult]:
    """Get relevant cached search results for a query."""
    thread_memory = _get_thread_memory(thread_id)
    _cleanup_expired_searches(thread_memory)
    
    # Find similar search
    similar_search = _find_similar_search(query, thread_memory)
    if similar_search:
        return [similar_search]
    
    # If no similar search, return recent relevant searches
    searches = thread_memory.get('searches', [])
    if not searches:
        return []
    
    # Simple relevance scoring based on keyword overlap
    query_words = set(query.lower().split())
    scored_searches = []
    
    for search_data in searches[-10:]:  # Only consider recent searches
        search_words = set(search_data['query'].lower().split())
        overlap = len(query_words & search_words)
        if overlap > 0:
            score = overlap / max(len(query_words), len(search_words))
            scored_searches.append((score, SearchResult.from_dict(search_data)))
    
    # Sort by relevance and return top results
    scored_searches.sort(key=lambda x: x[0], reverse=True)
    return [search for _, search in scored_searches[:max_results]]

def get_search_memory_stats(thread_id: str) -> Dict:
    """Get statistics about search memory for a thread."""
    thread_memory = _get_thread_memory(thread_id)
    _cleanup_expired_searches(thread_memory)
    
    searches = thread_memory.get('searches', [])
    
    return {
        'total_searches': len(searches),
        'memory_size_kb': len(str(searches)) // 1024,
        'oldest_search_age_minutes': (
            int((time.time() - min(s['timestamp'] for s in searches)) / 60)
            if searches else 0
        )
    }

def clear_search_memory(thread_id: str):
    """Clear all search memory for a thread."""
    if thread_id in _search_memory:
        del _search_memory[thread_id]

def should_reuse_search_results(query: str, thread_id: str) -> Tuple[bool, List[SearchResult]]:
    """
    Determine if we should reuse existing search results.
    
    Returns:
        (should_reuse, relevant_results)
    """
    relevant_results = get_relevant_search_results(thread_id, query)
    
    if not relevant_results:
        return False, []
    
    # Check if the most relevant result is very similar
    most_relevant = relevant_results[0]
    
    # Use embeddings for precise similarity check
    embedder = get_embedder()
    if embedder:
        try:
            embeddings = embedder.encode([query, most_relevant.query])
            similarity = cosine_similarity(embeddings[0], embeddings[1])
            return similarity >= 0.8, relevant_results
        except:
            pass
    
    # Fallback to keyword similarity
    query_words = set(query.lower().split())
    result_words = set(most_relevant.query.lower().split())
    
    if query_words and result_words:
        overlap = len(query_words & result_words)
        similarity = overlap / max(len(query_words), len(result_words))
        return similarity >= 0.7, relevant_results
    
    return False, relevant_results