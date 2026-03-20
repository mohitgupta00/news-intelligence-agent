from typing import TypedDict, Optional, Annotated, List, Dict, Any
from operator import add

def merge_dicts(a: dict, b: dict) -> dict:
    """Merge two dicts — used for fan-out step_outputs and session_cache."""
    result = dict(a) if a else {}
    if b:
        result.update(b)
    return result

def merge_lists(a: list, b: list) -> list:
    """Merge two lists — used for active entities and search queries."""
    result = list(a) if a else []
    if b:
        result.extend(b)
    return list(set(result))  # Remove duplicates

class StepOutput(TypedDict):
    step_index: int
    tool: str
    params: dict
    result: str
    status: str
    raw_data: Optional[Dict[str, Any]]  # Separate raw API responses

class EntityMemory(TypedDict):
    last_entity: Optional[str]
    last_entities: list[str]
    last_task: Optional[str]
    last_result: Optional[str]
    current_entities: Optional[list[str]]  # Currently extracted entities

class PriorEntityResult(TypedDict):
    entity: str
    result: str
    query: str

class QueryResolution(TypedDict):
    original_query: str
    resolved_query: str
    resolution_method: str  # "rule_based", "llm", "entity_memory", "none"
    entities_used: list[str]
    confidence: float

class ContextHints(TypedDict):
    resolved_entities: Optional[list[str]]  # From router
    resolved_topic: Optional[str]  # From router
    routing_confidence: Optional[float]  # Router confidence
    suggested_sources: Optional[list[str]]  # Preferred news sources

class NewsIQState(TypedDict):
    # Core query tracking
    messages: Annotated[list, add]
    user_query: str
    resolved_query: str
    api_queries: list[str]
    intent: str
    temporal_constraint: Optional[str]
    
    # Single-pass context resolution
    context_summary: Optional[str]  # Compact conversation summary
    resolution_confidence: Optional[float]  # Confidence in query resolution (0-1)
    
    # Enhanced entity and context tracking
    active_entities: Annotated[List[str], merge_lists]  # Currently discussed entities
    search_queries: Annotated[List[str], merge_lists]   # All search queries used
    query_resolution: Optional[QueryResolution]         # How query was resolved
    context_hints: Optional[ContextHints]               # Router insights
    extracted_entities: Optional[List[str]]             # Entities from current query
    
    # Planning and execution
    plan: list[dict]
    current_step: int
    step_outputs: Annotated[dict, merge_dicts]
    planning_done: bool
    
    # Memory and caching
    entity_memory: EntityMemory
    prior_entity_results: list[PriorEntityResult]
    session_cache: dict
    conversation_history: Optional[list[dict]]  # Conversation context
    
    # Control flow
    replan_count: int
    replan_decision: Optional[str]
    final_answer: Optional[str]
    
    # Performance tracking
    processing_stats: Optional[Dict[str, Any]]  # Timing, cache hits, etc.

# Backward compatibility alias
GraphState = NewsIQState
