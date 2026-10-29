"""Tests for data/generate_leads.py (CLAUDE.md Part 5.3).

Every distribution here is an INVENTED ASSUMPTION for the demo; these tests
check internal consistency (reproducibility, split, uncallable phones,
expected-outcome rules), not real-world accuracy.
"""

import re

import pytest

from data.generate_leads import build_lead_from_scenario, compute_expected_outcome, generate_leads

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


def test_uc2_amount_far_above_eligible_whatsapp_sent():
    # KC's decision on docs/OPEN_QUESTIONS.md #13: UC2 gets a UC1-style
    # amount-mismatch rule, but lands on whatsapp_sent, not not_a_fit —
    # this customer already owns gold and already started an application.
    truth = {
        "true_blocker": "unsure_amount",
        "owns_gold": True,
        "amount_needed": 400000,
        "eligible_amount": 200000,
    }
    assert compute_expected_outcome("gold_applicant", "cooperative", truth) == "whatsapp_sent"


def test_uc2_amount_mismatch_rule_skipped_when_no_eligible_amount():
    # eligible_amount 0 (no gold) must not trigger the mismatch rule.
    truth = {
        "true_blocker": "unsure_amount",
        "owns_gold": False,
        "amount_needed": 400000,
        "eligible_amount": 0,
    }
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


def test_scenario_persona_override_keeps_right_person_consistent():
    # A scenario overriding persona to wrong_person must also flip
    # right_person, or judge.derive_outcome's truth-based fallback for
    # wrong_person/no_answer would use stale data from the random base lead.
    scenario = {
        "id": "test_wrong_person",
        "use_case": "gold_applicant",
        "truth_overrides": {"persona": "wrong_person", "owns_gold": True},
        "expected_outcome": "wrong_person",
    }
    record = build_lead_from_scenario(scenario, seed=1)
    assert record["truth"]["right_person"] is False
    assert record["truth"]["answers_phone"] is True


def test_scenario_persona_override_silent_no_answer_sets_answers_phone_false():
    scenario = {
        "id": "test_silent",
        "use_case": "gold_applicant",
        "truth_overrides": {"persona": "silent_no_answer", "owns_gold": True},
        "expected_outcome": "no_answer",
    }
    record = build_lead_from_scenario(scenario, seed=1)
    assert record["truth"]["answers_phone"] is False
    assert record["truth"]["right_person"] is True


def test_scenario_explicit_right_person_override_is_not_clobbered():
    scenario = {
        "id": "test_explicit",
        "use_case": "gold_applicant",
        "truth_overrides": {"persona": "wrong_person", "right_person": True, "owns_gold": True},
        "expected_outcome": "wrong_person",
    }
    record = build_lead_from_scenario(scenario, seed=1)
    assert record["truth"]["right_person"] is True
