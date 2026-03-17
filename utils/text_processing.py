"""Text processing utilities for RAG-based context management."""

import re
from typing import List, Tuple
from sentence_transformers import SentenceTransformer
import numpy as np

# Global embedder instance
_embedder = None

def get_embedder():
    """Get or initialize the sentence transformer model."""
    global _embedder
    if _embedder is None:
        try:
            _embedder = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            _embedder = None
    return _embedder

def estimate_tokens(text: str) -> int:
    """Rough token estimation (1 token ≈ 4 characters)."""
    return len(text) // 4

def chunk_text(text: str, max_chunk_size: int = 500) -> List[str]:
    """Split text into chunks by sentences, respecting max size."""
    sentences = re.split(r'[.!?]+', text)
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        if estimate_tokens(current_chunk + sentence) > max_chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                # Single sentence too long, add anyway
                chunks.append(sentence)
        else:
            current_chunk += " " + sentence if current_chunk else sentence
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

def extract_relevant_chunks(step_outputs: dict, query: str, max_tokens: int = 2000) -> str:
    """
    Extract most relevant text chunks using semantic similarity.
    
    Args:
        step_outputs: Dictionary of step results
        query: User query for relevance scoring
        max_tokens: Maximum tokens to include in final context
        
    Returns:
        Concatenated relevant chunks within token limit
    """
    embedder = get_embedder()
    if not embedder:
        # Fallback to keyword matching
        return _extract_relevant_chunks_fallback(step_outputs, query, max_tokens)
    
    # Collect all text chunks with metadata
    all_chunks = []
    for step_idx, output in step_outputs.items():
        result = output.get('result', '')
        if not result:
            continue
            
        tool = output.get('tool', 'unknown')
        chunks = chunk_text(result)
        
        for chunk in chunks:
            all_chunks.append({
                'text': chunk,
                'step': step_idx,
                'tool': tool,
                'tokens': estimate_tokens(chunk)
            })
    
    if not all_chunks:
        return ""
    
    # Get embeddings
    query_embedding = embedder.encode([query])[0]
    chunk_texts = [chunk['text'] for chunk in all_chunks]
    chunk_embeddings = embedder.encode(chunk_texts)
    
    # Calculate similarities and sort
    for i, chunk in enumerate(all_chunks):
        chunk['similarity'] = cosine_similarity(query_embedding, chunk_embeddings[i])
    
    all_chunks.sort(key=lambda x: x['similarity'], reverse=True)
    
    # Select chunks within token limit
    selected_chunks = []
    total_tokens = 0
    
    for chunk in all_chunks:
        if total_tokens + chunk['tokens'] > max_tokens:
            break
        selected_chunks.append(chunk)
        total_tokens += chunk['tokens']
    
    # Format output
    result_parts = []
    for chunk in selected_chunks:
        result_parts.append(f"[{chunk['tool']}] {chunk['text']}")
    
    return "\n\n".join(result_parts)

def _extract_relevant_chunks_fallback(step_outputs: dict, query: str, max_tokens: int) -> str:
    """Fallback method using keyword matching when embeddings unavailable."""
    query_words = set(re.findall(r'\b\w{3,}\b', query.lower()))
    
    all_chunks = []
    for step_idx, output in step_outputs.items():
        result = output.get('result', '')
        if not result:
            continue
            
        tool = output.get('tool', 'unknown')
        chunks = chunk_text(result)
        
        for chunk in chunks:
            chunk_words = set(re.findall(r'\b\w{3,}\b', chunk.lower()))
            overlap = len(query_words & chunk_words)
            relevance_score = overlap / max(len(query_words), 1)
            
            all_chunks.append({
                'text': chunk,
                'tool': tool,
                'tokens': estimate_tokens(chunk),
                'relevance': relevance_score
            })
    
    # Sort by relevance and select within token limit
    all_chunks.sort(key=lambda x: x['relevance'], reverse=True)
    
    selected_chunks = []
    total_tokens = 0
    
    for chunk in all_chunks:
        if total_tokens + chunk['tokens'] > max_tokens:
            break
        selected_chunks.append(chunk)
        total_tokens += chunk['tokens']
    
    result_parts = []
    for chunk in selected_chunks:
        result_parts.append(f"[{chunk['tool']}] {chunk['text']}")
    
    return "\n\n".join(result_parts)