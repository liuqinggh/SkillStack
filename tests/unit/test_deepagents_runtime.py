"""Unit tests for DeepAgents runtime helpers (no live LLM)."""

from __future__ import annotations

from pathlib import Path
import sys

from langchain_core.messages import AIMessage, HumanMessage

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csbot.agents.deepagents_runtime import assistant_text_from_values_state, scoped_thread_id


def test_assistant_text_from_values_state_prefers_last_ai_message() -> None:
    state = {
        "messages": [
            HumanMessage(content="hi"),
            AIMessage(content="first"),
            AIMessage(content="last reply"),
        ]
    }
    assert assistant_text_from_values_state(state) == "last reply"


def test_assistant_text_from_values_state_empty_when_no_ai() -> None:
    assert assistant_text_from_values_state({"messages": [HumanMessage(content="only user")]}) == ""
    assert assistant_text_from_values_state({}) == ""
    assert assistant_text_from_values_state("not a dict") == ""


def test_scoped_thread_id_includes_agent_namespace() -> None:
    assert scoped_thread_id("claim", "11111111-1111-4111-8111-111111111111") == (
        "claim:11111111-1111-4111-8111-111111111111"
    )
