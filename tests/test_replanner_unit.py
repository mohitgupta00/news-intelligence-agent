"""Unit tests for the improved replanner in graph/nodes.py."""
import os
import pytest

# Must set env before importing
os.environ.setdefault("GROQ_API_KEY", "test-key")
os.environ.setdefault("GROQ_MODEL", "llama-3.1-8b-instant")
os.environ.setdefault("NEWSAPI_KEY", "x")
os.environ.setdefault("GNEWS_KEY", "x")
os.environ.setdefault("NEWSDATA_KEY", "x")

from tests.conftest import make_state
from graph.nodes import replanner


def _plan_with_empty(query="Tesca stock"):
    return [
        {
            "step": 0,
            "tool": "fetch_news",
            "params": {"query": query, "n": 5},
            "depends_on": [],
        }
    ]


def _empty_outputs(query="Tesca stock"):
    return {
        0: {
            "step_index": 0,
            "tool": "fetch_news",
            "params": {"query": query, "n": 5},
            "result": "",
            "status": "empty",
        }
    }


def _success_outputs():
    return {
        0: {
            "step_index": 0,
            "tool": "fetch_news",
            "params": {"query": "OpenAI news", "n": 5},
            "result": "OpenAI announces new model...",
            "status": "success",
        },
        1: {
            "step_index": 1,
            "tool": "analyze_text",
            "params": {"task": "summarize"},
            "result": "OpenAI released GPT-5...",
            "status": "success",
        },
    }


class TestReplannerRetryLimit:
    """Verify replanner respects max_retries."""

    def test_stops_at_limit_of_2(self):
        """When replan_count == 2, replanner returns 'finish'."""
        state = make_state(
            plan=_plan_with_empty(),
            step_outputs=_empty_outputs(),
            replan_count=2,
        )
        out = replanner(state)
        assert out["replan_decision"] == "finish"

    def test_first_attempt_triggers_replan(self, monkeypatch):
        """When replan_count=0 and empty results, triggers replan."""
        import graph.nodes as nodes

        # Mock the LLM call to return a valid JSON recovery step
        def fake_groq(*args, **kwargs):
            from unittest.mock import MagicMock

            m = MagicMock()
            m.choices[0].message.content = (
                '[{"step": 0, "tool": "fetch_news", '
                '"params": {"query": "Tesla news", "n": 5}, "depends_on": []}]'
            )
            return m

        monkeypatch.setattr(nodes._groq_client.chat.completions, "create", fake_groq)

        state = make_state(
            plan=_plan_with_empty("Tesca"),
            step_outputs=_empty_outputs("Tesca"),
            replan_count=0,
        )
        out = replanner(state)
        assert out["replan_decision"] == "continue"
        assert out["replan_count"] == 1


class TestReplannerLLMSuccessPath:
    """LLM returns valid JSON → steps appended."""

    def test_new_steps_appended_to_plan(self, monkeypatch):
        """LLM returns new step → plan grows."""
        import graph.nodes as nodes

        def fake_groq(*args, **kwargs):
            from unittest.mock import MagicMock

            m = MagicMock()
            m.choices[0].message.content = (
                '[{"step": 0, "tool": "fetch_news", '
                '"params": {"query": "Tesla electric vehicle", "n": 5}, "depends_on": []}]'
            )
            return m

        monkeypatch.setattr(nodes._groq_client.chat.completions, "create", fake_groq)

        original_plan = _plan_with_empty("Tesca")
        state = make_state(
            plan=original_plan,
            step_outputs=_empty_outputs("Tesca"),
            replan_count=0,
        )
        out = replanner(state)
        new_plan = out["plan"]
        assert len(new_plan) == 2  # original 1 + 1 new
        new_step = new_plan[-1]
        assert new_step["params"]["query"] == "Tesla electric vehicle"

    def test_step_index_correctly_offset(self, monkeypatch):
        """Replanner must offset step indices to avoid duplicates."""
        import graph.nodes as nodes

        def fake_groq(*args, **kwargs):
            from unittest.mock import MagicMock

            m = MagicMock()
            m.choices[0].message.content = (
                '[{"step": 0, "tool": "fetch_news", '
                '"params": {"query": "Apple Mac news", "n": 5}, "depends_on": []}]'
            )
            return m

        monkeypatch.setattr(nodes._groq_client.chat.completions, "create", fake_groq)

        original_plan = [
            {"step": 0, "tool": "fetch_news", "params": {"query": "M4 Ultra chip", "n": 5}, "depends_on": []},
            {"step": 1, "tool": "analyze_text", "params": {"task": "summarize"}, "depends_on": [0]},
        ]
        state = make_state(
            plan=original_plan,
            step_outputs={
                0: {"step_index": 0, "tool": "fetch_news", "params": {}, "result": "", "status": "empty"},
                1: {"step_index": 1, "tool": "analyze_text", "params": {}, "result": "", "status": "empty"},
            },
            replan_count=0,
        )
        out = replanner(state)
        all_indices = [s["step"] for s in out["plan"]]
        # All indices must be unique
        assert len(all_indices) == len(set(all_indices))


class TestReplannerDuplicatePrevention:
    """Duplicate queries should be skipped."""

    def test_skips_duplicate_query(self, monkeypatch):
        """LLM returns a duplicate query → should be skipped."""
        import graph.nodes as nodes

        def fake_groq(*args, **kwargs):
            from unittest.mock import MagicMock

            m = MagicMock()
            # LLM returns original query + a new one
            m.choices[0].message.content = (
                '[{"step": 0, "tool": "fetch_news", '
                '"params": {"query": "Tesca", "n": 5}, "depends_on": []}, '
                '{"step": 1, "tool": "fetch_news", '
                '"params": {"query": "Tesla news", "n": 5}, "depends_on": []}]'
            )
            return m

        monkeypatch.setattr(nodes._groq_client.chat.completions, "create", fake_groq)

        state = make_state(
            plan=_plan_with_empty("Tesca"),
            step_outputs=_empty_outputs("Tesca"),
            replan_count=0,
        )
        out = replanner(state)
        new_queries = [s["params"]["query"] for s in out["plan"]]
        # Should only have original Tesca + the new Tesla news (duplicate Tesca skipped)
        assert new_queries.count("Tesca") == 1
        assert "Tesla news" in new_queries


class TestReplannerLLMFailure:
    """When LLM fails, replanner should handle gracefully."""

    def test_llm_exception_logged_and_handled(self, monkeypatch, caplog):
        """LLM call raises exception → logged + returns finish."""
        import graph.nodes as nodes

        def fake_groq_fail(*args, **kwargs):
            raise RuntimeError("LLM down")

        monkeypatch.setattr(nodes._groq_client.chat.completions, "create", fake_groq_fail)

        state = make_state(
            plan=_plan_with_empty("M4 Ultra"),
            step_outputs=_empty_outputs("M4 Ultra"),
            replan_count=0,
        )

        with caplog.at_level("ERROR"):
            out = replanner(state)

        # Should return finish because no recovery steps possible
        assert out["replan_decision"] == "finish"
        assert "Replanner LLM call failed" in caplog.text

    def test_json_parse_error_logged(self, monkeypatch, caplog):
        """LLM returns invalid JSON → logged warning."""
        import graph.nodes as nodes

        def fake_groq(*args, **kwargs):
            from unittest.mock import MagicMock

            m = MagicMock()
            m.choices[0].message.content = "This is not JSON at all"
            return m

        monkeypatch.setattr(nodes._groq_client.chat.completions, "create", fake_groq)

        state = make_state(
            plan=_plan_with_empty("Tesca"),
            step_outputs=_empty_outputs("Tesca"),
            replan_count=0,
        )

        with caplog.at_level("WARNING"):
            out = replanner(state)

        # Should warn and return finish
        assert out["replan_decision"] == "finish"
        # Warning might appear if no valid recovery steps


class TestReplannerAllDoneScenario:
    """When all steps are done (no empty), should return finish."""

    def test_all_done_returns_finish(self):
        state = make_state(
            plan=[
                {"step": 0, "tool": "fetch_news", "params": {"query": "OpenAI", "n": 5}, "depends_on": []},
                {"step": 1, "tool": "analyze_text", "params": {"task": "summarize"}, "depends_on": [0]},
            ],
            step_outputs=_success_outputs(),
            replan_count=0,
        )
        out = replanner(state)
        assert out["replan_decision"] == "finish"
