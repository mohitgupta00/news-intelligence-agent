"""Integration test - verifies replanner works with real API calls."""
import os
import pytest

# Real API keys already set in environment
from tests.conftest import make_state
from graph.nodes import replanner


@pytest.mark.integration
def test_replanner_with_real_llm_on_misspelled_query():
    """
    Integration test: Replanner should call real Groq API
    and generate recovery steps for a misspelled query like 'Tesca'.
    """
    # Simulate a failed fetch for 'Tesca' (misspelled Tesla)
    state = make_state(
        user_query="Latest news about Tesca",
        resolved_query="Latest news about Tesca",
        plan=[
            {
                "step": 0,
                "tool": "fetch_news",
                "params": {"query": "Tesca", "n": 5},
                "depends_on": [],
            }
        ],
        step_outputs={
            0: {
                "step_index": 0,
                "tool": "fetch_news",
                "params": {"query": "Tesca", "n": 5},
                "result": "",
                "status": "empty",
            }
        },
        replan_count=0,
    )

    # Call replanner - this will hit real Groq API
    result = replanner(state)

    # Assertions
    assert result["replan_decision"] == "continue", "Should continue replanning"
    assert result["replan_count"] == 1, "Should increment replan count"
    assert "plan" in result, "Should return updated plan"

    new_plan = result["plan"]
    # Should have at least 2 steps now (original + recovery)
    assert len(new_plan) >= 2, f"Expected at least 2 steps, got {len(new_plan)}"

    # Check that new step(s) were added
    new_queries = [s["params"].get("query", "") for s in new_plan if s.get("step", -1) > 0]
    print(f"\n✅ Replanner generated recovery queries: {new_queries}")

    # At least one new query should be different from 'Tesca'
    assert any(
        "Tesla" in q or "news" in q for q in new_queries
    ), f"Expected corrected query, got: {new_queries}"


@pytest.mark.integration
def test_replanner_handles_all_done_scenario():
    """Integration test: When all steps are successful, replanner should finish."""
    state = make_state(
        plan=[
            {"step": 0, "tool": "fetch_news", "params": {"query": "OpenAI", "n": 5}, "depends_on": []}
        ],
        step_outputs={
            0: {
                "step_index": 0,
                "tool": "fetch_news",
                "params": {"query": "OpenAI", "n": 5},
                "result": "OpenAI announces new model...",
                "status": "success",
            }
        },
        replan_count=0,
    )

    result = replanner(state)
    assert result["replan_decision"] == "finish", "Should finish when all steps are done"
    print("\n✅ Replanner correctly returns 'finish' when all steps complete")
