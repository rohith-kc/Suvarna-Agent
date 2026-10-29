"""Tests for data/compliance.py (CLAUDE.md Part 5.3)."""

from data.compliance import is_callable
from data.generate_leads import generate_leads
from data.loader import Lead


def _lead(**visible_overrides):
    base = {
        "use_case": "gold_applicant",
        "dnd_flag": False,
        "consent_status": "applicant",
    }
    base.update(visible_overrides)
    return Lead(visible=base, truth={})


def test_dnd_flag_makes_lead_uncallable():
    assert is_callable(_lead(dnd_flag=True)) is False


def test_uc1_without_consent_is_uncallable():
    assert is_callable(_lead(use_case="loan_seeker", consent_status="")) is False


def test_uc1_with_consent_is_callable():
    assert is_callable(_lead(use_case="loan_seeker", consent_status="opted_in_form")) is True


def test_uc2_applicant_is_callable():
    assert is_callable(_lead(use_case="gold_applicant")) is True


def test_dnd_overrides_everything():
    assert is_callable(_lead(use_case="loan_seeker", consent_status="opted_in_form", dnd_flag=True)) is False


def test_no_dnd_lead_in_bulk_generation_is_ever_callable_when_flagged():
    records = generate_leads(n=500, seed=42)
    for r in records:
        lead = Lead(visible=r["lead"], truth=r["truth"])
        if lead.visible["dnd_flag"]:
            assert is_callable(lead) is False
