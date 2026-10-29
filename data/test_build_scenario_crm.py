"""Tests for data/build_scenario_crm.py (CLAUDE.md Part 5.3a / Phase 7).

This is what a deployed tools server's build step runs, so every
docs/test_cards/ scenario lead_id must resolve to the same CRM record the
card itself shows (make_test_cards.py uses the same seeding scheme).
"""

from data.build_crm import read_customer_context
from data.build_scenario_crm import build_scenario_crm


def test_builds_a_row_for_every_scenario(tmp_path):
    db_path = str(tmp_path / "crm.sqlite")
    n = build_scenario_crm(db_path)
    assert n == 40  # CLAUDE.md 5.3a: at least 40 scenarios, 25 UC2 + 15 UC1

    context = read_customer_context("scenario-uc2_busy", db_path)
    assert context is not None
    assert context["customer"]["name"] == "Sanjay"
    assert context["customer"]["city"] == "Bengaluru"


def test_matches_the_committed_test_card_for_uc2_busy(tmp_path):
    # docs/test_cards/scenario-uc2_busy.md shows this exact CRM record -
    # a deployed server's CRM must match it, or the card is lying to KC.
    db_path = str(tmp_path / "crm.sqlite")
    build_scenario_crm(db_path)
    context = read_customer_context("scenario-uc2_busy", db_path)
    application = context["applications"][0]
    assert application["last_step_completed"] == "kyc_started"
    assert application["amount_entered"] == "50000"
    assert application["device"] == "app"
