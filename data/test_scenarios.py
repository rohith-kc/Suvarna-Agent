"""Structural checks on data/scenarios.yaml (CLAUDE.md Part 5.3a)."""

import yaml

REQUIRED_KEYS = {
    "id", "name", "use_case", "lead_overrides", "truth_overrides",
    "crm_overrides", "customer_script", "expected_outcome", "must_not",
}
ALL_BLOCKERS = {
    "unsure_amount", "unsure_documents", "branch_far", "safety_worry",
    "rate_unclear", "got_money_elsewhere", "just_browsing",
}
ALL_PERSONAS = {
    "cooperative", "busy", "suspicious", "forgetful", "wants_human",
    "hostile_dnd", "confused_elderly", "negotiator", "wrong_person",
    "adversarial", "silent_no_answer",
}


def _load():
    with open("data/scenarios.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["scenarios"]


def test_at_least_40_scenarios_25_uc2_15_uc1():
    scenarios = _load()
    assert len(scenarios) >= 40
    assert sum(1 for s in scenarios if s["use_case"] == "gold_applicant") >= 25
    assert sum(1 for s in scenarios if s["use_case"] == "loan_seeker") >= 15


def test_every_scenario_has_required_keys():
    for s in _load():
        assert REQUIRED_KEYS.issubset(s.keys()), s.get("id")


def test_ids_are_unique():
    ids = [s["id"] for s in _load()]
    assert len(ids) == len(set(ids))


def test_every_blocker_code_covered():
    scenarios = _load()
    covered = {
        s["truth_overrides"].get("true_blocker")
        for s in scenarios if s["use_case"] == "gold_applicant"
    }
    assert ALL_BLOCKERS.issubset(covered)


def test_every_persona_covered():
    scenarios = _load()
    covered = {s["truth_overrides"].get("persona") for s in scenarios}
    assert ALL_PERSONAS.issubset(covered)


def test_customer_script_has_several_lines():
    for s in _load():
        assert 1 <= len(s["customer_script"]) <= 10
