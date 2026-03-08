from typing import TypedDict, Optional, Annotated
from operator import add

def merge_dicts(a: dict, b: dict) -> dict:
    """Merge two dicts — used for fan-out step_outputs."""
    return {**a, **b}

class StepOutput(TypedDict):
    step_index: int
    tool: str
    params: dict
    result: str
    status: str

class EntityMemory(TypedDict):
    last_entity: Optional[str]
    last_entities: list[str]
    last_task: Optional[str]
    last_result: Optional[str]

class PriorEntityResult(TypedDict):
    entity: str
    result: str
    query: str

class NewsIQState(TypedDict):
    messages: Annotated[list, add]
    user_query: str
    resolved_query: str
    api_queries: list[str]
    intent: str
    temporal_constraint: Optional[str]
    
    plan: list[dict]
    current_step: int
    step_outputs: Annotated[dict, merge_dicts]
    planning_done: bool
    
    entity_memory: EntityMemory
    prior_entity_results: list[PriorEntityResult]
    session_cache: dict
    
    replan_count: int
    replan_decision: Optional[str]
    final_answer: Optional[str]
