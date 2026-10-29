"""The most important test file in the repo (CLAUDE.md Part 2 rule 7).

Hidden "truth" fields must never reach the agent: not in dynamic variables,
not in a rendered prompt, not in anything the CRM tool returns. These tests
must fail loudly if that guarantee is ever broken.
"""

import json

from data.build_crm import build_crm, read_customer_context
from data.generate_leads import generate_leads, write_outputs
from data.loader import Lead, dynamic_variables

TRUTH_ONLY_FIELD_NAMES = [
    "owns_gold", "grams", "has_stones", "purity_karat", "persona",
    "answers_phone", "right_person", "amount_needed", "purpose",
    "eligible_amount", "needs_money_within_days", "true_blocker",
    "expected_outcome",
]


def _all_keys(obj):
    """All dict keys anywhere in a nested JSON-like structure (exact match,
    not substring — 'personal' must not be mistaken for a 'persona' leak)."""
    keys = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(k)
            keys.update(_all_keys(v))
    elif isinstance(obj, list):
        for item in obj:
            keys.update(_all_keys(item))
    return keys


def test_dynamic_variables_never_contain_a_truth_field_name_as_a_key():
    records = generate_leads(n=50, seed=99)
    for r in records:
        lead = Lead(visible=r["lead"], truth=r["truth"])
        keys = set(dynamic_variables(lead).keys())
        assert keys.isdisjoint(TRUTH_ONLY_FIELD_NAMES)


def test_dynamic_variables_never_contain_a_truth_value():
    records = generate_leads(n=50, seed=99)
    for r in records:
        lead = Lead(visible=r["lead"], truth=r["truth"])
        rendered = json.dumps(dynamic_variables(lead))
        for field in ("grams", "persona", "true_blocker", "expected_outcome", "eligible_amount"):
            value = r["truth"].get(field)
            if value in (None, "", 0, False):
                continue
            assert str(value) not in rendered, (
                f"truth field {field}={value!r} leaked into dynamic_variables "
                f"for lead {r['lead']['lead_id']}"
            )


def test_crm_tool_never_returns_a_truth_field(tmp_path):
    records = generate_leads(n=50, seed=99)
    write_outputs(records, str(tmp_path))
    db_path = tmp_path / "crm.sqlite"
    build_crm(str(tmp_path / "leads.jsonl"), str(db_path))

    for r in records:
        context = read_customer_context(r["lead"]["lead_id"], str(db_path))
        assert context is not None
        rendered = json.dumps(context)

        keys_found = _all_keys(context) & set(TRUTH_ONLY_FIELD_NAMES)
        assert not keys_found, f"truth field names {keys_found} leaked into CRM context"

        # expected_outcome is checked by key only, not by value: the CRM's
        # own invented call_history.result vocabulary (e.g. "no_answer")
        # legitimately overlaps with outcome codes by coincidence of
        # wording, not because anything leaked.
        for field in ("grams", "persona", "true_blocker", "eligible_amount"):
            value = r["truth"].get(field)
            if value in (None, "", 0, False):
                continue
            assert str(value) not in rendered, (
                f"truth field {field}={value!r} leaked into CRM context "
                f"for lead {r['lead']['lead_id']}"
            )
