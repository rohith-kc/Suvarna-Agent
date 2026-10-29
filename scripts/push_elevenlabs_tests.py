"""Pushes data/scenarios.yaml's UC2 scenarios to ElevenLabs as saved
Simulation Tests, and attaches them to the UC2 agent - so KC can just
click "Run" on a named scenario in the dashboard instead of retyping a
customer script and dynamic variables by hand every time.

Re-running this replaces all of this agent's attached tests (so prompt
or scenario-catalogue changes stay in sync) - it does not touch
anything else on the agent (prompt, tools, voice).

Usage: python scripts/push_elevenlabs_tests.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import yaml

from data.generate_leads import build_lead_from_scenario
from data.loader import Lead, dynamic_variables
from simulation.config import _load_dotenv
from simulation.run_simulation import _stable_seed

_load_dotenv()

API_KEY = os.environ["ELEVENLABS_API_KEY"]
AGENT_ID = os.environ["ELEVENLABS_AGENT_ID_UC2"]
BASE = "https://api.elevenlabs.io/v1"
HEADERS = {"xi-api-key": API_KEY, "content-type": "application/json"}

MAX_TURNS = 8


def _load_personas():
    import simulation.simulator as simulator
    return simulator.load_personas()


def _simulation_scenario_text(scenario, persona_info):
    lines = "\n".join(f"- {line}" for line in scenario.get("customer_script", []))
    persona_name = (scenario.get("truth_overrides") or {}).get("persona", "cooperative")
    description = persona_info.get(persona_name, {}).get("description", "")
    behaviour = persona_info.get(persona_name, {}).get("behaviour_rules", "")
    return (
        f"You are playing the customer. Persona: {persona_name}. {description} "
        f"{behaviour}\n\nSay things like this, in your own words, roughly in order:\n{lines}\n\n"
        "Stay in character; don't reveal anything beyond what a real customer in this "
        "situation would know."
    )


def _success_conditions(scenario):
    conditions = [f"The call reaches the outcome: {scenario['expected_outcome']}."]
    for bad in scenario.get("must_not") or []:
        conditions.append(f"The agent must NOT: {bad}.")
    return conditions[:30]


def _create_test(scenario, persona_info):
    lead_record = build_lead_from_scenario(scenario, seed=_stable_seed(scenario["id"]))
    lead = Lead(visible=lead_record["lead"], truth=lead_record["truth"])
    variables = {k: ("" if v is None else str(v)) for k, v in dynamic_variables(lead).items()}

    body = {
        "name": scenario["name"],
        "type": "simulation",
        "simulation_scenario": _simulation_scenario_text(scenario, persona_info),
        "success_conditions": _success_conditions(scenario),
        "simulation_max_turns": MAX_TURNS,
        "dynamic_variables": variables,
    }
    resp = requests.post(f"{BASE}/convai/agent-testing/create", headers=HEADERS, json=body, timeout=60)
    resp.raise_for_status()
    return resp.json()["id"]


def main():
    with open("data/scenarios.yaml", "r", encoding="utf-8") as f:
        scenarios = yaml.safe_load(f)["scenarios"]
    uc2_scenarios = [s for s in scenarios if s["use_case"] == "gold_applicant"]

    persona_info = _load_personas()

    test_ids = []
    for scenario in uc2_scenarios:
        test_id = _create_test(scenario, persona_info)
        test_ids.append(test_id)
        print(f"created {scenario['id']} -> {test_id}")

    resp = requests.patch(
        f"{BASE}/convai/agents/{AGENT_ID}",
        headers=HEADERS,
        json={"platform_settings": {"testing": {"attached_tests": [{"test_id": t} for t in test_ids]}}},
        timeout=60,
    )
    resp.raise_for_status()
    print(f"Attached {len(test_ids)} tests to agent {AGENT_ID}")


if __name__ == "__main__":
    main()
