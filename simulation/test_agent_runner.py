"""End-to-end test of one simulated call using FakeClient (CLAUDE.md
Part 5.5) — proves the agent <-> customer <-> tools plumbing works without
any real LLM call.
"""

from data.generate_leads import generate_one
from data.loader import Lead
from simulation.agent_runner import run_call
from simulation.fake_client import FakeClient


def _uc2_lead():
    record = generate_one("gold_applicant", seed=1)
    lead = Lead(visible=record["lead"], truth=record["truth"])
    lead.visible["last_step_completed"] = "amount_entered"
    return lead


def test_full_call_with_fake_client_reaches_a_terminal_outcome():
    lead = _uc2_lead()
    client = FakeClient()
    result = run_call(lead, client, "Hello, this is Asha, an AI assistant calling from Suvarna Gold Finance. Am I speaking with Test?")

    assert result["stopped_by"] in ("end_call", "customer_hangup", "turn_cap")
    assert result["turns"] > 0
    assert len(result["transcript"]) > 2


def test_full_call_calls_calculate_eligibility_and_book_appraisal():
    lead = _uc2_lead()
    client = FakeClient()
    result = run_call(lead, client, "Hello, this is Asha, an AI assistant calling from Suvarna Gold Finance. Am I speaking with Test?")

    tool_names = [c["name"] for c in result["tool_calls"]]
    assert "calculate_eligibility" in tool_names
    assert "book_appraisal" in tool_names


def test_tool_results_are_never_spoken_to_the_customer_verbatim():
    lead = _uc2_lead()
    client = FakeClient()
    result = run_call(lead, client, "Hello, this is Asha, an AI assistant calling from Suvarna Gold Finance. Am I speaking with Test?")

    for t in result["transcript"]:
        assert "[Tool result" not in t["text"]
