"""
Advanced Entity Resolution Engine
Handles coreference resolution, entity linking, and relationship inference
"""
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging

@dataclass
class ResolvedEntity:
    """Represents a resolved entity with metadata"""
    text: str
    entity_type: str
    confidence: float
    aliases: List[str]
    relationships: Dict[str, List[str]]

@dataclass
class EntityResolution:
    """Complete entity resolution result"""
    entities: List[ResolvedEntity]
    coreferences: Dict[str, str]  # pronoun -> entity mapping
    confidence: float

class EntityResolutionEngine:
    """Advanced entity resolution with coreference and linking"""
    
    def __init__(self):
        self.entity_knowledge_base = self._build_knowledge_base()
        self.coreference_patterns = self._build_coreference_patterns()
        
    def _build_knowledge_base(self) -> Dict[str, Dict]:
        """Build entity knowledge base with relationships"""
        return {
            # Technology Companies
            'Tesla': {
                'type': 'company',
                'sector': 'automotive_tech',
                'aliases': ['TSLA', 'Tesla Inc', 'Tesla Motors'],
                'relationships': {
                    'competitors': ['Ford', 'GM', 'Rivian'],
                    'leaders': ['Elon Musk'],
                    'sectors': ['electric_vehicles', 'autonomous_driving', 'energy']
                }
            },
            'Apple': {
                'type': 'company',
                'sector': 'technology',
                'aliases': ['AAPL', 'Apple Inc'],
                'relationships': {
                    'competitors': ['Google', 'Microsoft', 'Samsung'],
                    'leaders': ['Tim Cook'],
                    'sectors': ['smartphones', 'computers', 'services']
                }
            },
            'Google': {
                'type': 'company',
                'sector': 'technology',
                'aliases': ['GOOGL', 'Alphabet', 'Alphabet Inc'],
                'relationships': {
                    'competitors': ['Apple', 'Microsoft', 'Meta'],
                    'leaders': ['Sundar Pichai'],
                    'sectors': ['search', 'advertising', 'cloud', 'AI']
                }
            },
            'Microsoft': {
                'type': 'company',
                'sector': 'technology',
                'aliases': ['MSFT', 'Microsoft Corp'],
                'relationships': {
                    'competitors': ['Apple', 'Google', 'Amazon'],
                    'leaders': ['Satya Nadella'],
                    'sectors': ['software', 'cloud', 'gaming', 'AI']
                }
            },
            
            # Political Figures
            'Biden': {
                'type': 'person',
                'role': 'political_leader',
                'aliases': ['Joe Biden', 'President Biden', 'Joseph Biden'],
                'relationships': {
                    'opponents': ['Trump'],
                    'party': ['Democratic Party'],
                    'position': ['US President']
                }
            },
            'Trump': {
                'type': 'person',
                'role': 'political_leader',
                'aliases': ['Donald Trump', 'President Trump', 'Donald J Trump'],
                'relationships': {
                    'opponents': ['Biden'],
                    'party': ['Republican Party'],
                    'position': ['Former US President']
                }
            },
            
            # Countries/Regions
            'Ukraine': {
                'type': 'country',
                'region': 'Eastern Europe',
                'aliases': ['Ukrainian'],
                'relationships': {
                    'conflicts': ['Russia'],
                    'allies': ['NATO', 'EU', 'USA'],
                    'regions': ['Eastern Europe']
                }
            },
            'Russia': {
                'type': 'country',
                'region': 'Eastern Europe/Asia',
                'aliases': ['Russian Federation', 'Russian'],
                'relationships': {
                    'conflicts': ['Ukraine'],
                    'allies': ['China', 'Iran'],
                    'leaders': ['Putin']
                }
            },
            'China': {
                'type': 'country',
                'region': 'Asia',
                'aliases': ['Chinese', 'PRC', 'Peoples Republic of China'],
                'relationships': {
                    'competitors': ['USA'],
                    'allies': ['Russia'],
                    'regions': ['Asia']
                }
            }
        }
    
    def _build_coreference_patterns(self) -> Dict[str, List[str]]:
        """Build coreference resolution patterns"""
        return {
            'company_pronouns': ['it', 'they', 'them', 'their', 'its'],
            'person_pronouns': ['he', 'him', 'his', 'she', 'her', 'hers'],
            'country_pronouns': ['it', 'its', 'they', 'them', 'their'],
            'demonstratives': ['this', 'that', 'these', 'those'],
            'generic_references': ['the company', 'the organization', 'the country', 'the leader']
        }
    
    def _extract_raw_entities(self, query: str) -> List[str]:
        """Extract raw entities from query"""
        entities = []
        
        # Check knowledge base entities
        query_lower = query.lower()
        for entity, info in self.entity_knowledge_base.items():
            # Check main entity name
            if entity.lower() in query_lower:
                entities.append(entity)
            
            # Check aliases
            for alias in info.get('aliases', []):
                if alias.lower() in query_lower:
                    entities.append(entity)  # Map alias to main entity
        
        # Extract capitalized words (simple NER)
        words = query.split()
        for word in words:
            if (len(word) > 2 and 
                word[0].isupper() and 
                word not in {'The', 'This', 'That', 'What', 'How', 'When', 'Where', 'Why', 'Will', 'Can'}):
                clean_word = word.strip('.,!?')
                if clean_word not in entities:
                    entities.append(clean_word)
        
        return list(set(entities))
    
    def _resolve_coreferences(self, query: str, conversation_context: List[str]) -> Dict[str, str]:
        """Resolve pronouns and references to entities"""
        coreferences = {}
        query_lower = query.lower()
        
        # Get recent entities from context
        recent_entities = []
        for context_query in conversation_context[-3:]:  # Last 3 turns
            recent_entities.extend(self._extract_raw_entities(context_query))
        
        if not recent_entities:
            return coreferences
        
        # Most recent entity (likely referent)
        primary_entity = recent_entities[-1] if recent_entities else None
        
        # Resolve pronouns based on entity type
        if primary_entity and primary_entity in self.entity_knowledge_base:
            entity_info = self.entity_knowledge_base[primary_entity]
            entity_type = entity_info.get('type', 'unknown')
            
            # Company pronouns
            if entity_type == 'company':
                for pronoun in self.coreference_patterns['company_pronouns']:
                    if f' {pronoun} ' in f' {query_lower} ':
                        coreferences[pronoun] = primary_entity
            
            # Person pronouns
            elif entity_type == 'person':
                for pronoun in self.coreference_patterns['person_pronouns']:
                    if f' {pronoun} ' in f' {query_lower} ':
                        coreferences[pronoun] = primary_entity
            
            # Country pronouns
            elif entity_type == 'country':
                for pronoun in self.coreference_patterns['country_pronouns']:
                    if f' {pronoun} ' in f' {query_lower} ':
                        coreferences[pronoun] = primary_entity
        
        # Resolve demonstratives
        for demo in self.coreference_patterns['demonstratives']:
            if f' {demo} ' in f' {query_lower} ' and primary_entity:
                coreferences[demo] = primary_entity
        
        return coreferences
    
    def _infer_relationships(self, entities: List[str]) -> Dict[str, List[str]]:
        """Infer relationships between entities"""
        relationships = {}
        
        for entity in entities:
            if entity in self.entity_knowledge_base:
                entity_relationships = self.entity_knowledge_base[entity].get('relationships', {})
                
                # Find related entities in current query
                related_entities = []
                for rel_type, rel_entities in entity_relationships.items():
                    for rel_entity in rel_entities:
                        if rel_entity in entities:
                            related_entities.append(f"{rel_type}:{rel_entity}")
                
                if related_entities:
                    relationships[entity] = related_entities
        
        return relationships
    
    def _compute_confidence(self, entities: List[str], coreferences: Dict[str, str]) -> float:
        """Compute overall confidence in entity resolution"""
        if not entities:
            return 0.0
        
        # Base confidence from knowledge base coverage
        known_entities = sum(1 for entity in entities if entity in self.entity_knowledge_base)
        knowledge_coverage = known_entities / len(entities)
        
        # Coreference resolution confidence
        coreference_confidence = min(len(coreferences) * 0.1, 0.3)
        
        # Combined confidence
        total_confidence = knowledge_coverage * 0.7 + coreference_confidence
        
        return min(total_confidence, 0.95)
    
    def resolve_entities(self, query: str, conversation_context: List[str] = None) -> EntityResolution:
        """Complete entity resolution pipeline"""
        if conversation_context is None:
            conversation_context = []
        
        # Step 1: Extract raw entities
        raw_entities = self._extract_raw_entities(query)
        
        # Step 2: Resolve coreferences
        coreferences = self._resolve_coreferences(query, conversation_context)
        
        # Step 3: Apply coreference resolution to query
        resolved_query = query
        for pronoun, entity in coreferences.items():
            # Simple replacement (can be enhanced)
            resolved_query = re.sub(
                rf'\b{re.escape(pronoun)}\b', 
                entity, 
                resolved_query, 
                flags=re.IGNORECASE
            )
        
        # Step 4: Re-extract entities from resolved query
        final_entities = self._extract_raw_entities(resolved_query)
        
        # Step 5: Build resolved entity objects
        resolved_entities = []
        for entity in final_entities:
            if entity in self.entity_knowledge_base:
                entity_info = self.entity_knowledge_base[entity]
                resolved_entity = ResolvedEntity(
                    text=entity,
                    entity_type=entity_info.get('type', 'unknown'),
                    confidence=0.9,
                    aliases=entity_info.get('aliases', []),
                    relationships=entity_info.get('relationships', {})
                )
            else:
                # Unknown entity
                resolved_entity = ResolvedEntity(
                    text=entity,
                    entity_type='unknown',
                    confidence=0.6,
                    aliases=[],
                    relationships={}
                )
            
            resolved_entities.append(resolved_entity)
        
        # Step 6: Infer relationships
        entity_relationships = self._infer_relationships(final_entities)
        
        # Step 7: Compute overall confidence
        overall_confidence = self._compute_confidence(final_entities, coreferences)
        
        return EntityResolution(
            entities=resolved_entities,
            coreferences=coreferences,
            confidence=overall_confidence
        )
    
    def get_entity_context(self, entities: List[str]) -> Dict[str, any]:
        """Get contextual information about entities"""
        context = {
            'entity_types': {},
            'relationships': {},
            'sectors': set(),
            'regions': set()
        }
        
        for entity in entities:
            if entity in self.entity_knowledge_base:
                entity_info = self.entity_knowledge_base[entity]
                
                context['entity_types'][entity] = entity_info.get('type', 'unknown')
                context['relationships'][entity] = entity_info.get('relationships', {})
                
                if 'sector' in entity_info:
                    context['sectors'].add(entity_info['sector'])
                
                if 'region' in entity_info:
                    context['regions'].add(entity_info['region'])
        
        # Convert sets to lists for JSON serialization
        context['sectors'] = list(context['sectors'])
        context['regions'] = list(context['regions'])
        
        return context

# Global entity resolver instance
_entity_resolver = None

def get_entity_resolver() -> EntityResolutionEngine:
    """Get global entity resolver instance"""
    global _entity_resolver
    if _entity_resolver is None:
        _entity_resolver = EntityResolutionEngine()
    return _entity_resolver