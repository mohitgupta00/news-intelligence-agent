import os
import pytest
from unittest.mock import MagicMock

# Set dummy env vars BEFORE any project imports
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
os.environ.setdefault("GROQ_MODEL", "llama-3.1-8b-instant")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("NEWSAPI_KEY", "test-newsapi-key")
os.environ.setdefault("GNEWS_KEY", "test-gnews-key")
os.environ.setdefault("NEWSDATA_KEY", "test-newsdata-key")


def make_state(
    user_query="Summarize latest news about OpenAI",
    resolved_query="",
    intent="summarize",
    plan=None,
    step_outputs=None,
    replan_count=0,
    replan_decision=None,
    entity_memory=None,
):
    """Build a valid NewsIQState-shaped dict without hitting any API."""
    return {
        "user_query": user_query,
        "resolved_query": resolved_query or user_query,
        "api_queries": [],
        "intent": intent,
        "temporal_constraint": None,
        "plan": plan or [],
        "current_step": 0,
        "step_outputs": step_outputs or {},
        "planning_done": False,
        "all_steps_complete": False,
        "entity_memory": entity_memory or {
            "last_entity": "",
            "last_entities": [],
            "last_task": "",
            "last_result": "",
        },
        "prior_entity_results": [],
        "session_cache": {},
        "replan_count": replan_count,
        "replan_decision": replan_decision,
        "final_answer": None,
        "messages": [],
    }


def make_groq_response(content):
    """Fake Groq API response."""
    mock = MagicMock()
    mock.choices[0].message.content = content
    return mock