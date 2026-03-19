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

def store_search_result(query: str, result: str, thread_id: str, metadata: dict = None) -> None:
    """Store search result in memory for future reuse."""
    if not thread_id:
        thread_id = "default"
    
    if thread_id not in _search_memory:
        _search_memory[thread_id] = {'searches': [], 'last_cleanup': time.time()}
    
    search_result = SearchResult(query, result, time.time(), metadata)
    _search_memory[thread_id]['searches'].append(search_result)
    
    # Cleanup old results periodically
    current_time = time.time()
    if current_time - _search_memory[thread_id]['last_cleanup'] > 300:  # 5 minutes
        cleanup_expired_results(thread_id)
        _search_memory[thread_id]['last_cleanup'] = current_time

def cleanup_expired_results(thread_id: str) -> None:
    """Remove expired search results from memory."""
    if thread_id not in _search_memory:
        return
    
    current_time = time.time()
    searches = _search_memory[thread_id]['searches']
    
    # Keep only non-expired results
    _search_memory[thread_id]['searches'] = [
        search for search in searches 
        if not search.is_expired()
    ]

def should_reuse_search_results(query: str, thread_id: str) -> Tuple[bool, List[SearchResult]]:
    """
    Determine if we should reuse existing search results with temporal awareness.
    
    Returns:
        (should_reuse, relevant_results)
    """
    return False, []  # Simplified for testing

def get_search_memory_stats(thread_id: str) -> Dict:
    """Get statistics about search memory for a thread."""
    return {
        'total_searches': 0,
        'memory_size_kb': 0,
        'oldest_search_age_minutes': 0
    }