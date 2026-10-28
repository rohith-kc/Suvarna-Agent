"""Tests for data/loader.py (CLAUDE.md Part 5.3)."""

import json

from data.generate_leads import generate_leads
from data.loader import dynamic_variables, load_leads

EXPECTED_KEYS = {
    "lead_id", "customer_name", "agent_name", "lender_name", "use_case", "call_trigger",
    "trigger_detail", "opening_line", "last_step_completed", "minutes_since_stop",
    "city", "preferred_language", "branch_name",
}


def test_load_leads_roundtrip(tmp_path):
    records = generate_leads(n=5, seed=1)
    path = tmp_path / "leads.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    leads = load_leads(str(path))
    assert len(leads) == 5
    for lead, record in zip(leads, records):
        assert lead.visible == record["lead"]
        assert lead.truth == record["truth"]


def test_dynamic_variables_has_expected_keys():
    records = generate_leads(n=5, seed=1)
    leads = [_to_lead(r) for r in records]
    for lead in leads:
        assert set(dynamic_variables(lead).keys()) == EXPECTED_KEYS


def test_dynamic_variables_agent_name_is_asha():
    records = generate_leads(n=1, seed=1)
    lead = _to_lead(records[0])
    assert dynamic_variables(lead)["agent_name"] == "Asha"


def test_dynamic_variables_uc2_opening_lines_match_table():
    expected = {
        "phone_verified": "You started a gold loan request with us and verified your number, and I wanted to see if I can help you finish.",
        "amount_entered": "You started a gold loan request and entered the amount you needed, and I wanted to see if I can help you finish.",
        "kyc_started": "You started the KYC step for a gold loan with us, and I wanted to see if I can help you finish.",
        "appraisal_slot_page": "You were choosing an appraisal slot for a gold loan with us, and I wanted to see if I can help you finish.",
    }
    records = generate_leads(n=200, seed=42)
    seen = set()
    for r in records:
        if r["lead"]["use_case"] != "gold_applicant":
            continue
        lead = _to_lead(r)
        step = lead.visible["last_step_completed"]
        seen.add(step)
        assert dynamic_variables(lead)["opening_line"] == expected[step]
    assert seen == set(expected)  # all four values occur in 200 leads


def test_dynamic_variables_only_reads_visible_fields():
    # Corrupt the truth dict and confirm dynamic_variables output is unaffected.
    records = generate_leads(n=1, seed=1)
    lead = _to_lead(records[0])
    before = dynamic_variables(lead)
    lead.truth["grams"] = "LEAKED_VALUE_SHOULD_NOT_APPEAR"
    after = dynamic_variables(lead)
    assert before == after


def _to_lead(record):
    from data.loader import Lead
    return Lead(visible=record["lead"], truth=record["truth"])
