"""Tests for data/build_crm.py (CLAUDE.md Part 5.3a)."""

from data.build_crm import build_crm_from_leads, read_customer_context
from data.generate_leads import generate_leads


def test_build_crm_from_leads_matches_the_given_leads(tmp_path):
    records = generate_leads(n=4, seed=42)
    leads = [r["lead"] for r in records]
    db_path = str(tmp_path / "crm.sqlite")

    build_crm_from_leads(leads, db_path)

    for lead in leads:
        context = read_customer_context(lead["lead_id"], db_path)
        assert context is not None
        assert context["customer"]["name"] == lead["customer_name"]
        assert context["customer"]["city"] == lead["city"]


def test_build_crm_from_leads_is_scoped_to_its_own_seed_not_a_stale_one(tmp_path):
    # Regression: a lead_id like "gold_applicant-0000" names a different
    # customer under every seed. A CRM built from seed A must not be
    # queried as if it were built from seed B - this is exactly why
    # run_simulation.py rebuilds the CRM for every run instead of reusing
    # a static data/crm.sqlite.
    seed_a_leads = [r["lead"] for r in generate_leads(n=2, seed=1)]
    seed_b_leads = [r["lead"] for r in generate_leads(n=2, seed=2)]
    lead_id = seed_a_leads[0]["lead_id"]
    assert seed_a_leads[0]["customer_name"] != seed_b_leads[0]["customer_name"], (
        "test assumption broken: seeds 1 and 2 happened to pick the same name"
    )

    db_path = str(tmp_path / "crm.sqlite")
    build_crm_from_leads(seed_a_leads, db_path)
    context = read_customer_context(lead_id, db_path)
    assert context["customer"]["name"] == seed_a_leads[0]["customer_name"]

    build_crm_from_leads(seed_b_leads, db_path)
    context = read_customer_context(lead_id, db_path)
    assert context["customer"]["name"] == seed_b_leads[0]["customer_name"]
