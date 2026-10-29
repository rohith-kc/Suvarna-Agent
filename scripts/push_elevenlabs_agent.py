"""Pushes the UC2 agent's prompt and 6 webhook tools to ElevenLabs via the
REST API (Phase 7) - reuses the already-tested prompt and tool definitions
instead of pasting them into the dashboard by hand.

Creates the agent on first run; on later runs (once
ELEVENLABS_AGENT_ID_UC2 is set in .env) it updates that same agent in
place instead of creating a duplicate - run this again after any prompt
or tool change in Phase 5's iterate step.

Deliberately doesn't touch conversation_config.tts (voice) on update, so
it never clobbers whatever voice KC picked by listening to it in the
dashboard (CLAUDE.md Part 5.4: pick and test the voice by ear, not here).

Usage: python scripts/push_elevenlabs_agent.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

from agent.prompt import render_static
from simulation.config import _load_dotenv

_load_dotenv()

API_KEY = os.environ["ELEVENLABS_API_KEY"]
BASE = "https://api.elevenlabs.io/v1"
HEADERS = {"xi-api-key": API_KEY, "content-type": "application/json"}

TOOL_SECRET_ENV_VAR_LABEL = "tool_secret"  # exact label KC created in ElevenLabs

AGENT_NAME = "Suvarna UC2 - gold applicant"
FIRST_MESSAGE = (
    "Hello, this is {{agent_name}}, an AI assistant calling from {{lender_name}}. "
    "Am I speaking with {{customer_name}}?"
)

# Only used when creating the agent for the first time - a stable, known
# voice. KC swaps this for an Indian-accented voice in the dashboard, and
# this script never overwrites that choice on later (update) runs.
DEFAULT_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"


def _stringify_enums(schema):
    """ElevenLabs only allows enum on a string-type parameter (not
    integer/number), and every enum value must itself be a string. Our
    own tools/server.py endpoints still coerce a JSON string like "22"
    to int fine (FastAPI/Pydantic does this by default), so this is
    purely a presentation-layer adjustment for ElevenLabs' schema."""
    if not isinstance(schema, dict):
        return schema
    if "enum" in schema:
        schema["enum"] = [str(v) for v in schema["enum"]]
        if schema.get("type") in ("integer", "number"):
            schema["type"] = "string"
    for prop in schema.get("properties", {}).values():
        _stringify_enums(prop)
    return schema


def _webhook_tools():
    with open("tools/tool_definitions.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    tools = []
    for entry in data["tools"]:
        cfg = dict(entry["tool_config"])
        api_schema = dict(cfg["api_schema"])
        api_schema["request_headers"] = {
            "X-Tool-Secret": {"env_var_label": TOOL_SECRET_ENV_VAR_LABEL}
        }
        api_schema["request_body_schema"] = _stringify_enums(
            dict(api_schema.get("request_body_schema", {}))
        )
        cfg["api_schema"] = api_schema
        tools.append(cfg)
    return tools


def _agent_prompt_config():
    return {
        "prompt": render_static("gold_applicant"),
        "llm": "gemini-2.5-flash-lite",
        "temperature": 0.3,
        "tools": _webhook_tools(),
        "built_in_tools": {
            "end_call": {"name": "end_call", "params": {}},
            "language_detection": {"name": "language_detection", "params": {}},
        },
    }


def create():
    body = {
        "name": AGENT_NAME,
        "conversation_config": {
            "agent": {
                "first_message": FIRST_MESSAGE,
                "language": "en",
                "prompt": _agent_prompt_config(),
            },
            "tts": {"voice_id": DEFAULT_VOICE_ID},
        },
    }
    resp = requests.post(f"{BASE}/convai/agents/create", headers=HEADERS, json=body, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    print(f"Created agent {data['agent_id']}")
    print("Add this to .env: ELEVENLABS_AGENT_ID_UC2=" + data["agent_id"])
    return data["agent_id"]


def update(agent_id):
    body = {
        "name": AGENT_NAME,
        "conversation_config": {
            "agent": {
                "first_message": FIRST_MESSAGE,
                "language": "en",
                "prompt": _agent_prompt_config(),
            },
        },
    }
    resp = requests.patch(f"{BASE}/convai/agents/{agent_id}", headers=HEADERS, json=body, timeout=60)
    resp.raise_for_status()
    print(f"Updated agent {agent_id}")


def main():
    agent_id = os.environ.get("ELEVENLABS_AGENT_ID_UC2", "").strip()
    if agent_id:
        update(agent_id)
    else:
        create()


if __name__ == "__main__":
    main()
