"""Plays the customer (CLAUDE.md Part 5.5). Sees the lead's truth — the
agent must never see any of this module's inputs beyond what the customer
actually says out loud (Part 2 rule 7).
"""

import json
import os

import yaml

PERSONAS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "personas.yaml")
HANGUP_TOKEN = "[HANGUP]"


def load_personas():
    with open(PERSONAS_PATH, "r", encoding="utf-8") as f:
        return {p["name"]: p for p in yaml.safe_load(f)["personas"]}


def _truth_brief(lead):
    truth = lead.truth
    parts = [f"use_case={lead.visible['use_case']}"]
    if lead.visible["use_case"] == "gold_applicant":
        parts.append(f"true_blocker={truth.get('true_blocker')}")
    parts.append(f"owns_gold={truth.get('owns_gold')}")
    if truth.get("owns_gold"):
        parts.append(f"grams={truth.get('grams')}")
        parts.append(f"has_stones={truth.get('has_stones')}")
        parts.append(f"purity_karat={truth.get('purity_karat')}")
    parts.append(f"amount_needed={truth.get('amount_needed')}")
    parts.append(f"eligible_amount={truth.get('eligible_amount')}")
    parts.append(f"needs_money_within_days={truth.get('needs_money_within_days')}")
    return "; ".join(parts)


def build_system_prompt(lead, personas=None):
    personas = personas or load_personas()
    persona_name = lead.truth.get("persona")
    persona = personas.get(persona_name, {})

    return (
        "You are role-playing a customer receiving a phone call from a gold "
        "loan company's AI assistant, for a text-based test. Stay fully in "
        "character and speak like a real person, in 1 to 2 short sentences. "
        "Answer only what this customer would plausibly know. Reveal the "
        "real reason you stopped only once asked a specific, good question "
        "— never immediately.\n\n"
        f"Persona: {persona_name}. {persona.get('description', '')}\n"
        f"Behaviour: {persona.get('behaviour_rules', '')}\n\n"
        f"What actually happened (only you know this): {_truth_brief(lead)}\n\n"
        "End the call by saying a short closing line followed by the exact "
        f"token {HANGUP_TOKEN} once you are done, hang up, or opt out."
    )


def _build_messages(lead, transcript, personas=None):
    messages = [{"role": "system", "content": build_system_prompt(lead, personas)}]
    for entry in transcript:
        role = "assistant" if entry["speaker"] == "customer" else "user"
        messages.append({"role": role, "content": entry["text"]})
    return messages


def _parse_customer_text(raw):
    text = raw.strip()
    if text.startswith("{"):
        try:
            text = json.loads(text).get("say", text)
        except (json.JSONDecodeError, AttributeError):
            pass
    return text


def customer_reply(llm_client, lead, transcript, personas=None):
    """Returns (text, hung_up)."""
    messages = _build_messages(lead, transcript, personas)
    raw = llm_client.complete("customer", messages)
    text = _parse_customer_text(raw)
    hung_up = HANGUP_TOKEN in text
    text = text.replace(HANGUP_TOKEN, "").strip()
    return text, hung_up
