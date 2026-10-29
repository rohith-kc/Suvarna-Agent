"""Tests for data/generate_leads.py (CLAUDE.md Part 5.3).

Every distribution here is an INVENTED ASSUMPTION for the demo; these tests
check internal consistency (reproducibility, split, uncallable phones,
expected-outcome rules), not real-world accuracy.
"""

import re

import pytest

from data.generate_leads import compute_expected_outcome, generate_leads

PHONE_RE = re.compile(r"^\+910\d{9}$")


def test_reproducible_with_same_seed():
    a = generate_leads(n=50, seed=42)
    b = generate_leads(n=50, seed=42)
    assert a == b


def test_different_with_another_seed():
    a = generate_leads(n=50, seed=1)
    b = generate_leads(n=50, seed=2)
    assert a != b


def test_count_and_roughly_even_split():
    records = generate_leads(n=200, seed=42)
    assert len(records) == 200
    gold_applicant = sum(1 for r in records if r["lead"]["use_case"] == "gold_applicant")
    loan_seeker = sum(1 for r in records if r["lead"]["use_case"] == "loan_seeker")
    assert gold_applicant == 100
    assert loan_seeker == 100


def test_phones_are_uncallable():
    records = generate_leads(n=200, seed=42)
    for r in records:
        phone = r["lead"]["phone"]
        assert PHONE_RE.match(phone), f"bad phone: {phone}"


def test_uc2_has_blocker_last_step_and_stopped_time():
    records = generate_leads(n=200, seed=42)
    for r in records:
        if r["lead"]["use_case"] == "gold_applicant":
            assert r["truth"]["true_blocker"]
            assert r["lead"]["last_step_completed"]
            assert r["lead"]["minutes_since_stop"] is not None
            assert r["lead"]["stopped_at"]


def test_uc1_has_no_blocker_last_step_or_stopped_time():
    records = generate_leads(n=200, seed=42)
    for r in records:
        if r["lead"]["use_case"] == "loan_seeker":
            assert not r["truth"].get("true_blocker")
            assert not r["lead"]["last_step_completed"]
            assert r["lead"]["minutes_since_stop"] is None
            assert not r["lead"]["stopped_at"]


def test_dnd_leads_are_a_small_minority():
    records = generate_leads(n=2000, seed=42)
    share = sum(1 for r in records if r["lead"]["dnd_flag"]) / len(records)
    assert 0.02 < share < 0.20


def test_expected_outcome_matches_documented_rules():
    records = generate_leads(n=500, seed=7)
    for r in records:
        expected = compute_expected_outcome(
            use_case=r["lead"]["use_case"],
            persona=r["truth"]["persona"],
            truth=r["truth"],
        )
        assert r["truth"]["expected_outcome"] == expected


@pytest.mark.parametrize("persona,expected", [
    ("wrong_person", "wrong_person"),
    ("silent_no_answer", "no_answer"),
    ("hostile_dnd", "opt_out"),
])
def test_persona_overrides_take_priority_uc2(persona, expected):
    truth = {
        "true_blocker": "unsure_amount",
        "owns_gold": True,
        "amount_needed": 100000,
        "eligible_amount": 200000,
    }
    assert compute_expected_outcome("gold_applicant", persona, truth) == expected


@pytest.mark.parametrize("persona", ["busy", "wants_human", "confused_elderly"])
def test_persona_overrides_take_priority_callback(persona):
    truth = {
        "true_blocker": "unsure_amount",
        "owns_gold": True,
        "amount_needed": 100000,
        "eligible_amount": 200000,
    }
    assert compute_expected_outcome("gold_applicant", persona, truth) == "callback_scheduled"


def test_uc2_blocker_rules_take_priority_over_persona():
    # rate_unclear always -> callback_scheduled, even for a negotiator persona.
    truth = {"true_blocker": "rate_unclear", "owns_gold": True}
    assert compute_expected_outcome("gold_applicant", "negotiator", truth) == "callback_scheduled"


def test_uc2_got_money_elsewhere_not_interested():
    truth = {"true_blocker": "got_money_elsewhere", "owns_gold": True}
    assert compute_expected_outcome("gold_applicant", "cooperative", truth) == "not_interested"


def test_uc2_just_browsing_whatsapp_sent():
    truth = {"true_blocker": "just_browsing", "owns_gold": True}
    assert compute_expected_outcome("gold_applicant", "cooperative", truth) == "whatsapp_sent"


def test_uc2_default_appraisal_booked():
    truth = {"true_blocker": "unsure_amount", "owns_gold": True}
    assert compute_expected_outcome("gold_applicant", "cooperative", truth) == "appraisal_booked"


def test_uc1_no_gold_not_a_fit():
    truth = {"owns_gold": False, "amount_needed": 100000, "eligible_amount": 0}
    assert compute_expected_outcome("loan_seeker", "cooperative", truth) == "not_a_fit"


def test_uc1_amount_far_above_eligible_not_a_fit():
    truth = {"owns_gold": True, "amount_needed": 300000, "eligible_amount": 200000}
    assert compute_expected_outcome("loan_seeker", "cooperative", truth) == "not_a_fit"


@pytest.mark.parametrize("persona", ["suspicious", "forgetful", "negotiator"])
def test_uc1_soft_personas_whatsapp_sent(persona):
    truth = {"owns_gold": True, "amount_needed": 100000, "eligible_amount": 200000}
    assert compute_expected_outcome("loan_seeker", persona, truth) == "whatsapp_sent"


def test_uc1_default_appraisal_booked():
    truth = {"owns_gold": True, "amount_needed": 100000, "eligible_amount": 200000}
    assert compute_expected_outcome("loan_seeker", "cooperative", truth) == "appraisal_booked"
