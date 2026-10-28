"""Tests for simulation/simulator.py (CLAUDE.md Part 5.5)."""

from data.loader import Lead
from simulation.simulator import customer_reply


class _ExplodingClient:
    """Raises if called - proves silent_no_answer never reaches the LLM."""

    def complete(self, role, messages, json_schema=None):
        raise AssertionError("silent_no_answer must not call the LLM")


def test_silent_no_answer_short_circuits_without_calling_the_llm():
    lead = Lead(visible={"use_case": "gold_applicant"}, truth={"persona": "silent_no_answer"})
    text, hung_up = customer_reply(_ExplodingClient(), lead, transcript=[])
    assert text == ""
    assert hung_up is True
