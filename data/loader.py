"""Load leads and build prompt-ready dynamic variables (CLAUDE.md Part 5.3).

dynamic_variables() reads ONLY visible fields plus fixed defaults. It must
never be given anything from a lead's truth dict — that boundary is what
data/test_leakage.py checks.
"""

import json
from dataclasses import dataclass
from typing import Any, Dict

LENDER_NAME = "Suvarna Gold Finance"
AGENT_NAME = "Asha"

# PLACEHOLDER: real branch names/locations are unknown until lender facts
# are confirmed (docs/OPEN_QUESTIONS.md #2, #3) — Phase 3 may replace this.
_BRANCH_NAME_TEMPLATE = "our {city} branch"

_UC2_OPENING_LINES = {
    "phone_verified": (
        "You started a gold loan request with us and verified your number, "
        "and I wanted to see if I can help you finish."
    ),
    "amount_entered": (
        "You started a gold loan request and entered the amount you needed, "
        "and I wanted to see if I can help you finish."
    ),
    "kyc_started": (
        "You started the KYC step for a gold loan with us, and I wanted to "
        "see if I can help you finish."
    ),
    "appraisal_slot_page": (
        "You were choosing an appraisal slot for a gold loan with us, and I "
        "wanted to see if I can help you finish."
    ),
}


@dataclass
class Lead:
    visible: Dict[str, Any]
    truth: Dict[str, Any]


def load_leads(path):
    leads = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            leads.append(Lead(visible=record["lead"], truth=record["truth"]))
    return leads


def _opening_line(lead):
    if lead.visible["use_case"] == "gold_applicant":
        return _UC2_OPENING_LINES.get(lead.visible.get("last_step_completed"), "")
    trigger_detail = lead.visible.get("trigger_detail", "")
    return f"I saw that you {trigger_detail}." if trigger_detail else ""


def dynamic_variables(lead):
    """Exactly the variables the prompts use. Visible fields + fixed defaults only."""
    visible = lead.visible
    return {
        "customer_name": visible["customer_name"],
        "agent_name": AGENT_NAME,
        "lender_name": LENDER_NAME,
        "use_case": visible["use_case"],
        "call_trigger": visible.get("call_trigger", ""),
        "trigger_detail": visible.get("trigger_detail", ""),
        "opening_line": _opening_line(lead),
        "last_step_completed": visible.get("last_step_completed", ""),
        "minutes_since_stop": visible.get("minutes_since_stop"),
        "city": visible["city"],
        "preferred_language": visible["preferred_language"],
        "branch_name": _BRANCH_NAME_TEMPLATE.format(city=visible["city"]),
    }
