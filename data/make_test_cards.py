"""Writes one role-play test card per sample lead (CLAUDE.md Part 5.8).

Cards are generated from catalogue scenarios first (data/scenarios.yaml),
so KC can paste dynamic variables into the ElevenLabs dashboard and
role-play the customer without typing anything by hand.

Usage: python data/make_test_cards.py --out docs/test_cards
"""

import argparse
import hashlib
import json
import os
import sys
import tempfile

import yaml

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.build_crm import apply_crm_overrides, build_crm, read_customer_context
from data.generate_leads import generate_one, build_lead_from_scenario, write_outputs
from data.loader import Lead, dynamic_variables

# CLAUDE.md Part 5.8: at least six UC2 leads (cooperative, busy, suspicious,
# wrong person, hostile, adversarial) and three UC1 leads (no gold, gold
# fits, need too large).
REQUIRED_UC2_SCENARIOS = {
    "cooperative": "uc2_cooperative_unsure_amount_hindi_switch",
    "busy": "uc2_busy",
    "suspicious": "uc2_suspicious",
    "wrong_person": "uc2_wrong_person_spouse",
    "hostile": "uc2_hostile_dnd_abusive",
    "adversarial": "uc2_adversarial_otp_bot_injection",
}
REQUIRED_UC1_SCENARIOS = {
    "no_gold": "uc1_no_gold",
    "gold_fits": "uc1_cooperative_fits_ad",
    "need_too_large": "uc1_wants_more_than_gold_supports",
}


def _stable_seed(text):
    """A reproducible seed from text — Python's hash() is randomized per
    process and must never be used here."""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _load_scenarios():
    with open("data/scenarios.yaml", "r", encoding="utf-8") as f:
        return {s["id"]: s for s in yaml.safe_load(f)["scenarios"]}


def _build_crm_context(record, scenario):
    with tempfile.TemporaryDirectory() as tmp:
        write_outputs([record], tmp)
        db_path = os.path.join(tmp, "crm.sqlite")
        build_crm(os.path.join(tmp, "leads.jsonl"), db_path)
        if scenario:
            apply_crm_overrides(db_path, record["lead"]["lead_id"], scenario.get("crm_overrides"))
        return read_customer_context(record["lead"]["lead_id"], db_path)


def _render_card(record, context, scenario):
    lead = Lead(visible=record["lead"], truth=record["truth"])
    dyn_vars = dynamic_variables(lead)

    lines = [f"# Test card: {lead.visible['lead_id']}", ""]
    if scenario:
        lines += [f"**Scenario:** {scenario['name']} (`{scenario['id']}`)", ""]

    lines += ["## Dynamic variables to paste", "", "```"]
    for k, v in dyn_vars.items():
        lines.append(f"{k}: {v}")
    lines += ["```", ""]

    lines += ["## CRM record the agent can look up (get_customer_context)", "", "```json"]
    lines.append(json.dumps(context, indent=2) if context else "{}")
    lines += ["```", ""]

    lines += ["## Customer role-play script", ""]
    lines.append(f"- **Persona:** {lead.truth.get('persona')}")
    if lead.visible["use_case"] == "gold_applicant":
        lines.append(
            f"- **True blocker (reveal only once asked a specific question):** "
            f"{lead.truth.get('true_blocker')}"
        )
    if lead.truth.get("owns_gold"):
        lines.append(
            f"- **Gold:** {lead.truth.get('grams')} g, "
            f"stones: {lead.truth.get('has_stones')}, karat: {lead.truth.get('purity_karat')}"
        )
    else:
        lines.append("- **Gold:** none")
    lines.append("- **Say these in order, in your own words:**")
    for i, line in enumerate(scenario["customer_script"] if scenario else [], start=1):
        lines.append(f"  {i}. {line}")
    lines.append("")

    lines += ["## Expected outcome and pass checklist", ""]
    lines.append(f"- **Expected outcome:** `{lead.truth.get('expected_outcome')}`")
    lines.append("- [ ] Identity confirmed before any loan detail")
    lines.append("- [ ] Said it is an AI assistant")
    lines.append("- [ ] Every number came from a tool, never invented")
    lines.append("- [ ] Reached the expected outcome above")
    for item in (scenario.get("must_not", []) if scenario else []):
        lines.append(f"- [ ] Did NOT: {item}")
    lines.append("")

    return "\n".join(lines)


def _write_card(record, scenario, out_dir, written):
    context = _build_crm_context(record, scenario)
    card = _render_card(record, context, scenario)
    path = os.path.join(out_dir, f"{record['lead']['lead_id']}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(card)
    written.append(path)


def generate_test_cards(out_dir, extra_random=0):
    os.makedirs(out_dir, exist_ok=True)
    scenarios = _load_scenarios()
    written = []

    required_ids = set(REQUIRED_UC2_SCENARIOS.values()) | set(REQUIRED_UC1_SCENARIOS.values())
    for scenario_id in sorted(required_ids):
        scenario = scenarios[scenario_id]
        record = build_lead_from_scenario(scenario, seed=_stable_seed(scenario_id))
        _write_card(record, scenario, out_dir, written)

    for i in range(extra_random):
        use_case = "gold_applicant" if i % 2 == 0 else "loan_seeker"
        record = generate_one(use_case, seed=5000 + i)
        _write_card(record, None, out_dir, written)

    return written


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="docs/test_cards")
    parser.add_argument(
        "--extra-random", type=int, default=0,
        help="additional random sample leads to also make cards for",
    )
    args = parser.parse_args()

    written = generate_test_cards(args.out, extra_random=args.extra_random)

    print(f"Wrote {len(written)} test cards to {args.out}")
    for path in written:
        print(f"  {path}")


if __name__ == "__main__":
    main()
