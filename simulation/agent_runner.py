"""Runs one simulated call (CLAUDE.md Part 5.5).

System prompt = the use-case prompt rendered with dynamic_variables(lead).
The conversation starts with the first message as the agent's turn 1. Then
up to MAX_TURNS turns of customer <-> agent, with tools executed locally
against the real tools/server.py endpoint functions (so simulation and the
voice platform run identical logic). Tool use goes through the JSON action
protocol (Part 5.5), not any provider's native function-calling, so it
works the same way regardless of LLM_PROVIDER.
"""

import json
import os

import tools.server as tools_server
from agent.prompt import render
from data.loader import dynamic_variables
from simulation import simulator

MAX_TURNS = 24
MAX_TOOL_CHAIN = 3
TERMINAL_TOOLS = {"record_opt_out"}

TOOL_DEFINITIONS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "tool_definitions.json"
)


def _load_tool_catalog_text():
    """Builds a short "name(args): description" catalog from the single
    source of truth (tools/tool_definitions.json) so a real LLM — unlike
    the scripted FakeClient — knows the exact argument names each tool
    expects, instead of guessing them."""
    with open(TOOL_DEFINITIONS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    lines = []
    for entry in data["tools"]:
        cfg = entry["tool_config"]
        schema = cfg["api_schema"].get("request_body_schema", {})
        props = schema.get("properties", {})
        required = set(schema.get("required", []))
        arg_bits = [
            f"{name}: {prop.get('type', 'any')}{'' if name in required else ' (optional)'}"
            for name, prop in props.items()
        ]
        args_text = ", ".join(arg_bits) if arg_bits else "no arguments"
        lines.append(f"- {cfg['name']}({args_text}) — {cfg['description']}")
    return "\n".join(lines)


TOOL_CATALOG_TEXT = _load_tool_catalog_text()

REPLY_FORMAT_FOOTER = (
    "\n\n## Tools available (simulation only; exact argument names — use them precisely)\n"
    f"{TOOL_CATALOG_TEXT}\n\n"
    "## Reply format (simulation only — the voice platform does not see this)\n"
    "Reply with ONLY a JSON object, no other text before or after it: "
    '{"say": "<what you say out loud>", '
    '"tool": null or {"name": "<one of the tool names above>", "args": {<exactly the argument names listed for that tool>}}, '
    '"end_call": true or false}. '
    "Call at most one tool per reply."
)


def _call_server_tool(request_cls, endpoint_fn, args):
    return endpoint_fn(request_cls(**args))


TOOL_FUNCTIONS = {
    "calculate_eligibility": lambda args: _call_server_tool(
        tools_server.EligibilityRequest, tools_server.calculate_eligibility_endpoint, args
    ),
    "book_appraisal": lambda args: _call_server_tool(
        tools_server.BookAppraisalRequest, tools_server.book_appraisal_endpoint, args
    ),
    "send_whatsapp_summary": lambda args: _call_server_tool(
        tools_server.WhatsappRequest, tools_server.send_whatsapp_summary_endpoint, args
    ),
    "schedule_callback": lambda args: _call_server_tool(
        tools_server.CallbackRequest, tools_server.schedule_callback_endpoint, args
    ),
    "record_opt_out": lambda args: _call_server_tool(
        tools_server.OptOutRequest, tools_server.record_opt_out_endpoint, args
    ),
    "get_customer_context": lambda args: _call_server_tool(
        tools_server.CustomerContextRequest, tools_server.get_customer_context_endpoint, args
    ),
}


def _execute_tool(name, args):
    """Never raises — a real LLM occasionally calls a tool with the wrong
    or missing arguments, and the agent should see a clear error (and
    follow its own fallback instructions) rather than crash the harness."""
    tool_fn = TOOL_FUNCTIONS.get(name)
    if tool_fn is None:
        return {"ok": False, "error": f"unknown tool: {name}"}
    try:
        return tool_fn(args)
    except Exception as exc:  # noqa: BLE001 - deliberately broad; see docstring
        return {"ok": False, "error": f"tool call failed: {exc}"}


class HarnessError(Exception):
    """The agent failed the JSON action protocol twice in a row — a harness
    error, not an agent failure (CLAUDE.md Part 5.5)."""


def _parse_json_action(raw_text):
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    action = json.loads(text)
    if "say" not in action:
        raise ValueError("missing 'say'")
    return action


def _get_agent_action(llm_client, agent_messages):
    raw = llm_client.complete("agent", agent_messages)
    try:
        return raw, _parse_json_action(raw)
    except (json.JSONDecodeError, ValueError):
        agent_messages.append({"role": "assistant", "content": raw})
        agent_messages.append({
            "role": "user",
            "content": (
                "That wasn't valid JSON in the required format. Reply again "
                'with ONLY {"say": "...", "tool": null or {...}, "end_call": false}.'
            ),
        })
        raw2 = llm_client.complete("agent", agent_messages)
        try:
            return raw2, _parse_json_action(raw2)
        except (json.JSONDecodeError, ValueError) as exc:
            raise HarnessError(f"agent returned invalid JSON twice: {raw2!r}") from exc


def run_call(lead, llm_client, first_message_text, personas=None):
    system_prompt = render(lead.visible["use_case"], dynamic_variables(lead)) + REPLY_FORMAT_FOOTER

    transcript = [{"speaker": "agent", "text": first_message_text}]
    tool_calls = []
    agent_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": json.dumps(
            {"say": first_message_text, "tool": None, "end_call": False}
        )},
    ]

    stopped_by = "turn_cap"
    turns = 0
    action = None

    while turns < MAX_TURNS:
        customer_text, hung_up = simulator.customer_reply(llm_client, lead, transcript, personas)
        if customer_text:
            transcript.append({"speaker": "customer", "text": customer_text})
            agent_messages.append({"role": "user", "content": customer_text})
        turns += 1

        for _ in range(MAX_TOOL_CHAIN):
            raw, action = _get_agent_action(llm_client, agent_messages)
            agent_messages.append({"role": "assistant", "content": raw})
            transcript.append({"speaker": "agent", "text": action["say"]})

            tool = action.get("tool")
            if not tool:
                break

            result = _execute_tool(tool["name"], tool.get("args", {}))
            tool_calls.append({"name": tool["name"], "args": tool.get("args", {}), "result": result})
            agent_messages.append({
                "role": "user",
                "content": (
                    f"[Tool result for {tool['name']}, not spoken to the customer] "
                    f"{json.dumps(result)}"
                ),
            })

            if tool["name"] in TERMINAL_TOOLS:
                break

        tool_name = (action.get("tool") or {}).get("name") if action else None
        if action and (action.get("end_call") or tool_name in TERMINAL_TOOLS):
            stopped_by = "end_call"
            break
        if hung_up:
            stopped_by = "customer_hangup"
            break

    return {
        "transcript": transcript,
        "tool_calls": tool_calls,
        "turns": turns,
        "stopped_by": stopped_by,
    }
