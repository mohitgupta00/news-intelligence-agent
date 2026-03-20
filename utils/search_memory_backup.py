"""Persistent search memory for preserving search results across conversation turns."""

import time
import hashlib
import re
from typing import Dict, List, Optional, Tuple
from utils.text_processing import get_embedder, cosine_similarity

# Global search memory
_search_memory: Dict[str, Dict] = {}  # thread_id -> search_data
_SEARCH_MEMORY_TTL = 3600  # 1 hour (default)
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
    
    def is_expired(self, query: str = None) -> bool:
        """Check if search result has expired based on query context."""
        current_time = time.time()
        
        if query:
            # Use dynamic TTL based on query type
            ttl = get_temporal_ttl(query)
        else:
            # Use default TTL
            ttl = _SEARCH_MEMORY_TTL
        
        return current_time - self.timestamp > ttl
    
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

def is_time_sensitive_query(query: str) -> bool:
    """Check if query requires fresh/recent results."""
    time_sensitive_patterns = [
        r'\b(latest|recent|breaking|today|yesterday|now|current)\b',
        r'\b(this\s+(week|month|day|morning|afternoon))\b',
        r'\b(just\s+(happened|announced|released))\b',
        r'\b(updates?|developments?)\b'
    ]
    
    query_lower = query.lower()
    return any(re.search(pattern, query_lower) for pattern in time_sensitive_patterns)

def get_temporal_ttl(query: str) -> int:
    """Get appropriate TTL based on query temporal sensitivity."""
    if is_time_sensitive_query(query):
        # Time-sensitive queries: 30 minutes TTL
        return 1800
    else:
        # General queries: 1 hour TTL
        return 3600

def should_use_cached_result(query: str, cached_result: SearchResult, similarity: float) -> bool:
    """Determine if cached result should be used based on temporal and similarity factors."""
    current_time = time.time()
    time_diff = current_time - cached_result.timestamp
    
    # Get appropriate TTL for this query type
    ttl = get_temporal_ttl(query)
    
    # For time-sensitive queries, be more strict about freshness
    if is_time_sensitive_query(query):
        # Require very high similarity and recent results
        if time_diff > ttl:  # Expired
            return False
        return similarity >= 0.90  # Higher similarity threshold
    else:
        # For general queries, allow older results with high similarity
        if time_diff > ttl * 2:  # Double TTL for general queries
            return False
        return similarity >= 0.80  # Standard similarity threshold

def calculate_temporal_similarity_score(query: str, cached_result: SearchResult, base_similarity: float) -> float:
    """Calculate similarity score adjusted for temporal factors."""
    time_diff = time.time() - cached_result.timestamp
    ttl = get_temporal_ttl(query)
    
    # Time decay factor (0.5 to 1.0)
    time_factor = max(0.5, 1.0 - (time_diff / (ttl * 2)))
    
    # Adjust similarity based on time decay
    adjusted_similarity = base_similarity * time_factor
    
    return adjusted_similarity

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
    
    def is_expired(self, query: str = None) -> bool:
        """Check if search result has expired based on query context."""
        current_time = time.time()
        
        if query:
            # Use dynamic TTL based on query type
            ttl = get_temporal_ttl(query)
        else:
            # Use default TTL
            ttl = _SEARCH_MEMORY_TTL
        
        return current_time - self.timestamp > ttl
    
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
    """Find similar cached search using temporal-aware similarity."""
    searches = thread_memory.get('searches', [])
    if not searches:
        return None
    
    embedder = get_embedder()
    best_match = None
    best_score = 0.0
    
    if embedder:
        # Use semantic similarity with temporal adjustment
        try:
            query_embedding = embedder.encode([query])[0]
            
            for search_data in searches:
                cached_result = SearchResult.from_dict(search_data)
                
                # Skip expired results
                if cached_result.is_expired(query):
                    continue
                
                cached_embedding = embedder.encode([cached_result.query])[0]
                base_similarity = cosine_similarity(query_embedding, cached_embedding)
                
                # Check if this result should be used based on temporal factors
                if should_use_cached_result(query, cached_result, base_similarity):
                    # Calculate temporal-adjusted score
                    adjusted_score = calculate_temporal_similarity_score(query, cached_result, base_similarity)
                    
                    if adjusted_score > best_score:
                        best_score = adjusted_score
                        best_match = cached_result
            
            if best_match and best_score >= _SIMILARITY_THRESHOLD:
                return best_match
                
        except Exception:
            pass
    
    # Fallback to keyword matching with temporal awareness
    query_words = set(query.lower().split())
    
    for search_data in searches:
        cached_result = SearchResult.from_dict(search_data)
        
        # Skip expired results
        if cached_result.is_expired(query):
            continue
        
        cached_words = set(cached_result.query.lower().split())
        if query_words and cached_words:
            overlap = len(query_words & cached_words)
            base_similarity = overlap / max(len(query_words), len(cached_words))
            
            if should_use_cached_result(query, cached_result, base_similarity):
                adjusted_score = calculate_temporal_similarity_score(query, cached_result, base_similarity)
                
                if adjusted_score > best_score:
                    best_score = adjusted_score
                    best_match = cached_result
    
    return best_match if best_score >= 0.6 else None

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
    Determine if we should reuse existing search results with temporal awareness.
    
    Returns:
        (should_reuse, relevant_results)
    """
    relevant_results = get_relevant_search_results(thread_id, query)
    
    if not relevant_results:
        return False, []
    
    # Check if the most relevant result should be reused
    most_relevant = relevant_results[0]
    
    # Use embeddings for precise similarity check
    embedder = get_embedder()
    if embedder:
        try:
            embeddings = embedder.encode([query, most_relevant.query])
            base_similarity = cosine_similarity(embeddings[0], embeddings[1])
            
            # Apply temporal-aware logic
            if should_use_cached_result(query, most_relevant, base_similarity):
                adjusted_score = calculate_temporal_similarity_score(query, most_relevant, base_similarity)
                return adjusted_score >= 0.8, relevant_results
            else:
                return False, relevant_results
        except Exception:
            pass
    
    # Fallback to keyword similarity with temporal awareness
    query_words = set(query.lower().split())
    result_words = set(most_relevant.query.lower().split())
    
    if query_words and result_words:
        overlap = len(query_words & result_words)
        base_similarity = overlap / max(len(query_words), len(result_words))
        
        if should_use_cached_result(query, most_relevant, base_similarity):
            adjusted_score = calculate_temporal_similarity_score(query, most_relevant, base_similarity)
            return adjusted_score >= 0.7, relevant_results
    
    return False, relevant_results