"""Tests for NuclearDataAgent.

The agent talks to the Claude API, so every test here uses a fake client: no network,
no API key, no SciBERT. Agents are built with __new__ to skip the real __init__, which
would load a 768-dim transformer just to test string handling.
"""
from types import SimpleNamespace

import pandas as pd
import pytest

from nugrade.ai_agent import NuclearDataAgent
from nugrade.grading_functions import nuclide_symbol_format


# --- Block / client fakes ----------------------------------------------------

def text_block(text):
    return SimpleNamespace(type="text", text=text)


def tool_use_block(id, name, input):
    return SimpleNamespace(type="tool_use", id=id, name=name, input=input)


def thinking_block(thinking="reasoning", signature="sig-abc"):
    return SimpleNamespace(type="thinking", thinking=thinking, signature=signature)


class FakeMessages:
    """Replays a scripted list of responses and records every request it received."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return self._responses.pop(0)


def make_agent(responses=(), tool_output="TOOL-OUTPUT"):
    agent = NuclearDataAgent.__new__(NuclearDataAgent)
    agent.client = SimpleNamespace(messages=FakeMessages(responses))
    agent.skill = "SYSTEM PROMPT"
    agent.tools = [{"name": "get_nuclear_data"}]
    agent.sql_con = None
    agent.scibert_available = False
    agent.execute_tool = lambda name, input, metrics=None, options=None: tool_output
    return agent


def response(*content, stop_reason="end_turn"):
    return SimpleNamespace(content=list(content), stop_reason=stop_reason)


# --- _serialize_content ------------------------------------------------------

class TestSerializeContent:
    def test_preserves_thinking_blocks_with_signature(self):
        """Thinking blocks must survive into history; the API rejects a turn that drops them."""
        blocks = [thinking_block("step by step", "sig-xyz"), text_block("answer")]

        result = NuclearDataAgent._serialize_content(blocks)

        assert result[0] == {
            "type": "thinking",
            "thinking": "step by step",
            "signature": "sig-xyz",
        }
        assert result[1] == {"type": "text", "text": "answer"}

    def test_preserves_redacted_thinking(self):
        blocks = [SimpleNamespace(type="redacted_thinking", data="encrypted-payload")]

        result = NuclearDataAgent._serialize_content(blocks)

        assert result == [{"type": "redacted_thinking", "data": "encrypted-payload"}]

    def test_preserves_tool_use(self):
        blocks = [tool_use_block("toolu_1", "search_corpus", {"query": "detector"})]

        result = NuclearDataAgent._serialize_content(blocks)

        assert result == [{
            "type": "tool_use", "id": "toolu_1",
            "name": "search_corpus", "input": {"query": "detector"},
        }]

    def test_no_block_is_silently_dropped(self):
        """Regression: thinking blocks used to vanish here, corrupting the next turn."""
        blocks = [thinking_block(), text_block("a"), tool_use_block("t1", "n", {})]

        assert len(NuclearDataAgent._serialize_content(blocks)) == len(blocks)


# --- _apply_cache_breakpoint -------------------------------------------------

class TestCacheBreakpoint:
    def test_marks_only_the_final_block(self):
        history = [
            {"role": "user", "content": [{"type": "text", "text": "first"}]},
            {"role": "user", "content": [{"type": "text", "text": "second"}]},
        ]

        NuclearDataAgent._apply_cache_breakpoint(history)

        assert "cache_control" not in history[0]["content"][0]
        assert history[1]["content"][-1]["cache_control"] == {"type": "ephemeral"}

    def test_old_breakpoints_are_cleared(self):
        """The API allows at most 4 breakpoints, so stale ones must not accumulate."""
        history = [
            {"role": "user", "content": [
                {"type": "text", "text": "old", "cache_control": {"type": "ephemeral"}}
            ]},
            {"role": "user", "content": [{"type": "text", "text": "new"}]},
        ]

        NuclearDataAgent._apply_cache_breakpoint(history)

        assert "cache_control" not in history[0]["content"][0]
        assert "cache_control" in history[1]["content"][-1]

    def test_stays_within_the_four_breakpoint_limit(self):
        history = [
            {"role": "user", "content": [
                {"type": "text", "text": f"turn {i}", "cache_control": {"type": "ephemeral"}}
            ]}
            for i in range(10)
        ]

        NuclearDataAgent._apply_cache_breakpoint(history)

        marked = sum(
            1 for m in history for b in m["content"] if "cache_control" in b
        )
        assert marked == 1


# --- chat() tool-use loop ----------------------------------------------------

class TestChatLoop:
    def test_parallel_tool_results_go_in_one_user_message(self):
        """Regression: results were appended one user message each, which trains the
        model out of making parallel tool calls."""
        agent = make_agent([
            response(
                tool_use_block("toolu_1", "get_nuclear_data", {}),
                tool_use_block("toolu_2", "get_experiment_list", {}),
                stop_reason="tool_use",
            ),
            response(text_block("done")),
        ])

        _, history = agent.chat("q", metrics={}, options=None, conversation_history=[])

        tool_result_messages = [
            m for m in history
            if m["role"] == "user"
            and isinstance(m["content"], list)
            and any(b.get("type") == "tool_result" for b in m["content"])
        ]
        assert len(tool_result_messages) == 1
        results = tool_result_messages[0]["content"]
        assert [b["tool_use_id"] for b in results] == ["toolu_1", "toolu_2"]

    def test_returns_final_text_and_records_history(self):
        agent = make_agent([response(text_block("the answer"))])

        reply, history = agent.chat("q", metrics={}, options=None, conversation_history=[])

        assert reply == "the answer"
        assert history[0]["role"] == "user"
        assert history[-1]["role"] == "assistant"

    def test_thinking_block_survives_a_tool_round_trip(self):
        agent = make_agent([
            response(thinking_block(), tool_use_block("toolu_1", "x", {}),
                     stop_reason="tool_use"),
            response(text_block("done")),
        ])

        _, history = agent.chat("q", metrics={}, options=None, conversation_history=[])

        first_assistant = next(m for m in history if m["role"] == "assistant")
        assert [b["type"] for b in first_assistant["content"]] == ["thinking", "tool_use"]

    def test_uses_the_configured_model_and_adaptive_thinking(self):
        agent = make_agent([response(text_block("hi"))])

        agent.chat("q", metrics={}, options=None, conversation_history=[])

        request = agent.client.messages.requests[0]
        assert request["model"] == NuclearDataAgent.MODEL
        assert request["thinking"] == {"type": "adaptive"}
        assert request["output_config"]["effort"] == NuclearDataAgent.EFFORT

    def test_does_not_crash_when_the_model_returns_no_text(self):
        """A thinking-only final turn must not raise StopIteration into the Flask route."""
        agent = make_agent([response(thinking_block())])

        reply, _ = agent.chat("q", metrics={}, options=None, conversation_history=[])

        assert isinstance(reply, str) and reply


# --- _get_nuclear_data -------------------------------------------------------

def make_metrics(rows):
    data = pd.DataFrame(rows)
    for column in ["dEnergy", "dData_assumed", "endf7-1_chi_squared",
                   "endf7-1_relative_error", "endf8_chi_squared"]:
        data[column] = 0.0
    reaction = SimpleNamespace(data=data)
    return {"7Li": SimpleNamespace(reactions={"N,TOT": reaction})}


BASE_ROWS = [
    {"Energy": 1e3, "Data": 1.0, "dData": 0.1, "Author": "Alpha",
     "EXFOR_Entry": "10001", "EXFOR_Subentry": "10001002", "Year": 1970,
     "endf8_relative_error": 0.01},
    {"Energy": 2e3, "Data": 2.0, "dData": 0.2, "Author": "Beta",
     "EXFOR_Entry": "10002", "EXFOR_Subentry": "10002002", "Year": 1980,
     "endf8_relative_error": 0.99},
    {"Energy": 3e3, "Data": 3.0, "dData": 0.3, "Author": "Gamma",
     "EXFOR_Entry": "10003", "EXFOR_Subentry": "10003002", "Year": 1990,
     "endf8_relative_error": 0.50},
]


class TestGetNuclearData:
    def test_returns_highest_error_first(self):
        """Regression: this sorted ascending while telling the model it was descending,
        so the agent received the best-agreeing points labelled as the worst."""
        agent = make_agent()

        output = agent._get_nuclear_data("7Li", "N,TOT", metrics=make_metrics(BASE_ROWS))

        rows = [line for line in output.splitlines() if "," in line]
        authors_in_order = [a for a in ("Beta", "Gamma", "Alpha")
                            if any(a in row for row in rows)]
        first_data_row = next(r for r in rows[1:] if any(
            a in r for a in ("Alpha", "Beta", "Gamma")))
        assert "Beta" in first_data_row, "highest-error point (0.99) must come first"
        assert authors_in_order == ["Beta", "Gamma", "Alpha"]

    def test_caps_output_at_ten_points(self):
        rows = [dict(BASE_ROWS[0], endf8_relative_error=i / 100) for i in range(25)]
        agent = make_agent()

        output = agent._get_nuclear_data("7Li", "N,TOT", metrics=make_metrics(rows))

        assert "Showing 10 of 25" in output

    def test_energy_filter_is_applied(self):
        agent = make_agent()

        output = agent._get_nuclear_data(
            "7Li", "N,TOT", metrics=make_metrics(BASE_ROWS),
            filters={"energy_lower": 2.5e3},
        )

        assert "Gamma" in output
        assert "Alpha" not in output and "Beta" not in output

    def test_author_filter_is_case_insensitive(self):
        agent = make_agent()

        output = agent._get_nuclear_data(
            "7Li", "N,TOT", metrics=make_metrics(BASE_ROWS),
            filters={"Author": "beta"},
        )

        assert "Beta" in output and "Alpha" not in output

    def test_unknown_nuclide_reports_rather_than_raises(self):
        agent = make_agent()

        output = agent._get_nuclear_data("999Xx", "N,TOT", metrics=make_metrics(BASE_ROWS))

        assert "not found" in output.lower()


# --- nuclide_symbol_format ---------------------------------------------------

class TestNuclideSymbolFormat:
    @pytest.mark.parametrize("raw,expected", [
        ("Li-7", "7Li"),
        ("7li", "7Li"),
        ("7Li", "7Li"),
        ("LI7", "7Li"),
        ("li 7", "7Li"),
        ("U-235", "235U"),
        ("235u", "235U"),
    ])
    def test_normalises_to_canonical_form(self, raw, expected):
        assert nuclide_symbol_format(raw) == expected
