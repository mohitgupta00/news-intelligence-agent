"""
Semantic Context Manager - Neural approach to conversation context tracking
Uses sentence transformers and attention mechanisms for intelligent context management
"""
import numpy as np
import time
from typing import List, Dict, Tuple, Optional
from collections import deque
from dataclasses import dataclass
import logging

# Lightweight imports for production
try:
    from sentence_transformers import SentenceTransformer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logging.warning("sentence-transformers not available, using fallback embeddings")

@dataclass
class ContextState:
    """Represents current conversation context state"""
    entities: List[str]
    topic_embedding: np.ndarray
    query_embedding: np.ndarray
    confidence: float
    turn_count: int
    timestamp: float

@dataclass
class ContextSwitchResult:
    """Result of context switch detection"""
    switch_detected: bool
    switch_probability: float
    switch_type: str  # 'explicit', 'semantic_drift', 'entity_change'
    confidence: float

class SemanticContextManager:
    """Neural context management with semantic understanding"""
    
    def __init__(self):
        self.encoder = self._initialize_encoder()
        self.working_memory = deque(maxlen=3)  # Last 3 conversation turns
        self.current_context = None
        self.switch_threshold = 0.7
        self.semantic_drift_threshold = 0.4
        
        # Entity relationship tracking
        self.entity_embeddings = {}
        self.entity_relationships = {}
        
    def _initialize_encoder(self):
        """Initialize sentence transformer or fallback"""
        if TRANSFORMERS_AVAILABLE:
            try:
                # Lightweight model for production
                return SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                logging.warning(f"Failed to load transformer model: {e}")
        
        # Fallback to simple embeddings
        return None
    
    def _encode_text(self, text: str) -> np.ndarray:
        """Encode text to vector representation"""
        if self.encoder is not None:
            return self.encoder.encode([text])[0]
        else:
            # Simple fallback: TF-IDF-like representation
            return self._simple_embedding(text)
    
    def _simple_embedding(self, text: str) -> np.ndarray:
        """Fallback embedding using word frequency"""
        words = text.lower().split()
        # Create simple 100-dim embedding based on word hashes
        embedding = np.zeros(100)
        for word in words:
            hash_val = hash(word) % 100
            embedding[hash_val] += 1
        return embedding / (np.linalg.norm(embedding) + 1e-8)
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between vectors"""
        dot_product = np.dot(vec1, vec2)
        norm_product = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        return dot_product / (norm_product + 1e-8)
    
    def _extract_entities_neural(self, query: str) -> List[str]:
        """Extract entities using neural approach with fallback"""
        # Simple entity extraction - can be enhanced with spaCy
        words = query.split()
        entities = []
        
        # Capitalized words (simple NER)
        for word in words:
            if (len(word) > 2 and 
                word[0].isupper() and 
                word not in {'The', 'This', 'That', 'What', 'How', 'When', 'Where', 'Why'}):
                entities.append(word.strip('.,!?'))
        
        # Known entity patterns
        entity_patterns = {
            'companies': ['Tesla', 'Apple', 'Google', 'Microsoft', 'Amazon', 'Meta'],
            'countries': ['USA', 'China', 'Russia', 'Ukraine', 'Israel', 'Iran'],
            'people': ['Biden', 'Trump', 'Musk', 'Cook']
        }
        
        query_lower = query.lower()
        for category, entity_list in entity_patterns.items():
            for entity in entity_list:
                if entity.lower() in query_lower:
                    entities.append(entity)
        
        return list(set(entities))  # Remove duplicates
    
    def _detect_explicit_switches(self, query: str) -> Tuple[bool, float]:
        """Detect explicit context switch signals"""
        explicit_signals = [
            "now tell me about", "switch to", "what about", "instead",
            "moving on to", "let's discuss", "different topic", "change subject"
        ]
        
        query_lower = query.lower()
        for signal in explicit_signals:
            if signal in query_lower:
                return True, 0.95
        
        return False, 0.0
    
    def _compute_semantic_drift(self, current_embedding: np.ndarray) -> float:
        """Compute semantic drift from previous context"""
        if self.current_context is None or len(self.working_memory) == 0:
            return 0.0
        
        # Compare with recent context embeddings
        recent_similarities = []
        for context_state in self.working_memory:
            similarity = self._cosine_similarity(current_embedding, context_state.query_embedding)
            recent_similarities.append(similarity)
        
        # Average similarity with recent context
        avg_similarity = np.mean(recent_similarities)
        semantic_drift = 1.0 - avg_similarity
        
        return semantic_drift
    
    def _compute_entity_overlap(self, current_entities: List[str]) -> float:
        """Compute entity overlap with previous context"""
        if self.current_context is None:
            return 0.0
        
        previous_entities = set(self.current_context.entities)
        current_entities_set = set(current_entities)
        
        if not previous_entities:
            return 0.0
        
        overlap = len(previous_entities & current_entities_set)
        overlap_ratio = overlap / len(previous_entities)
        
        return overlap_ratio
    
    def detect_context_switch(self, query: str, entities: List[str]) -> ContextSwitchResult:
        """Multi-signal context switch detection"""
        
        # 1. Explicit switch detection
        explicit_switch, explicit_confidence = self._detect_explicit_switches(query)
        if explicit_switch:
            return ContextSwitchResult(
                switch_detected=True,
                switch_probability=explicit_confidence,
                switch_type='explicit',
                confidence=explicit_confidence
            )
        
        # 2. Semantic drift analysis
        query_embedding = self._encode_text(query)
        semantic_drift = self._compute_semantic_drift(query_embedding)
        
        # 3. Entity overlap analysis
        entity_overlap = self._compute_entity_overlap(entities)
        
        # 4. Ensemble decision
        # High semantic drift + low entity overlap = likely switch
        semantic_switch_score = semantic_drift if semantic_drift > self.semantic_drift_threshold else 0
        entity_switch_score = (1.0 - entity_overlap) if entity_overlap < 0.3 else 0
        
        # Weighted combination
        switch_probability = (semantic_switch_score * 0.6 + entity_switch_score * 0.4)
        
        switch_detected = switch_probability > self.switch_threshold
        switch_type = 'semantic_drift' if semantic_switch_score > entity_switch_score else 'entity_change'
        
        return ContextSwitchResult(
            switch_detected=switch_detected,
            switch_probability=switch_probability,
            switch_type=switch_type,
            confidence=min(switch_probability, 0.95)
        )
    
    def update_context(self, query: str, entities: List[str] = None) -> ContextSwitchResult:
        """Update conversation context with neural analysis"""
        
        # Extract entities if not provided
        if entities is None:
            entities = self._extract_entities_neural(query)
        
        # Detect context switch
        switch_result = self.detect_context_switch(query, entities)
        
        # Create new context state
        query_embedding = self._encode_text(query)
        topic_embedding = self._encode_text(' '.join(entities + [query]))
        
        new_context = ContextState(
            entities=entities,
            topic_embedding=topic_embedding,
            query_embedding=query_embedding,
            confidence=0.9 if not switch_result.switch_detected else 0.7,
            turn_count=1 if switch_result.switch_detected else (self.current_context.turn_count + 1 if self.current_context else 1),
            timestamp=time.time()
        )
        
        # Update memory
        if self.current_context:
            self.working_memory.append(self.current_context)
        
        self.current_context = new_context
        
        # Update entity embeddings for future reference
        for entity in entities:
            if entity not in self.entity_embeddings:
                self.entity_embeddings[entity] = self._encode_text(entity)
        
        return switch_result
    
    def get_relevant_context(self, query: str, max_context_turns: int = 2) -> Dict:
        """Retrieve most relevant context using attention mechanism"""
        if not self.working_memory:
            return {}
        
        query_embedding = self._encode_text(query)
        
        # Compute attention weights for each context in memory
        context_scores = []
        for context_state in self.working_memory:
            # Semantic similarity
            semantic_score = self._cosine_similarity(query_embedding, context_state.topic_embedding)
            
            # Temporal decay (recent contexts are more relevant)
            time_decay = np.exp(-(time.time() - context_state.timestamp) / 3600)  # 1-hour decay
            
            # Combined score
            combined_score = semantic_score * 0.7 + time_decay * 0.3
            context_scores.append((context_state, combined_score))
        
        # Sort by relevance and return top contexts
        context_scores.sort(key=lambda x: x[1], reverse=True)
        relevant_contexts = context_scores[:max_context_turns]
        
        # Build context summary
        context_summary = {
            'relevant_entities': [],
            'context_confidence': 0.0,
            'temporal_relevance': 0.0
        }
        
        for context_state, score in relevant_contexts:
            context_summary['relevant_entities'].extend(context_state.entities)
            context_summary['context_confidence'] += score * context_state.confidence
            context_summary['temporal_relevance'] += score
        
        # Normalize and deduplicate
        context_summary['relevant_entities'] = list(set(context_summary['relevant_entities']))
        context_summary['context_confidence'] /= len(relevant_contexts) if relevant_contexts else 1
        context_summary['temporal_relevance'] /= len(relevant_contexts) if relevant_contexts else 1
        
        return context_summary
    
    def get_context_state(self) -> Dict:
        """Get current context state for external use"""
        if not self.current_context:
            return {}
        
        return {
            'entities': self.current_context.entities,
            'confidence': self.current_context.confidence,
            'turn_count': self.current_context.turn_count,
            'timestamp': self.current_context.timestamp
        }
    
    def reset_context(self):
        """Reset conversation context"""
        self.current_context = None
        self.working_memory.clear()
        self.entity_embeddings.clear()
        self.entity_relationships.clear()

# Global context manager instance
_context_manager = None

def get_context_manager() -> SemanticContextManager:
    """Get global context manager instance"""
    global _context_manager
    if _context_manager is None:
        _context_manager = SemanticContextManager()
    return _context_manager