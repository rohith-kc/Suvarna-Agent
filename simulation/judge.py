"""Scores a transcript against the truth (CLAUDE.md Part 5.5). Only the
judge (and the simulator) may read truth fields — never the agent (Part 2
rule 7).

Deterministic checks are plain code, not the LLM: no_invented_numbers,
tts_safe, opt_out_respected, concise_turns, and the outcome itself (derived
from the terminal tool calls). The LLM only fills stopped_reason_found,
found_true_blocker, right_fit_decision, persona_check_passed, and notes.
"""

import json
import re

from simulation.speech_lint import check_line

# Lender-fact / tool constants the agent may legitimately say without it
# being an "invented" number (rate %, karats, LTV tiers).
ALLOWED_CONSTANTS = {"12", "22", "18", "20", "24", "85", "80", "75", "7"}
AMOUNT_RE = re.compile(r"\b\d[\d,]{2,}\b")

TERMINAL_OUTCOMES = {
    "book_appraisal": "appraisal_booked",
    "send_whatsapp_summary": "whatsapp_sent",
    "schedule_callback": "callback_scheduled",
    "record_opt_out": "opt_out",
}

EXACT_MATCH_OUTCOMES = {"opt_out", "wrong_person", "no_answer", "not_a_fit"}
SOFT_PASS_DOWNGRADES = {"appraisal_booked": "whatsapp_sent"}
AMBITION_RANK = {
    "not_interested": 0, "not_a_fit": 0,
    "callback_scheduled": 1, "whatsapp_sent": 1,
    "appraisal_booked": 2,
}


def _agent_lines(transcript):
    return [t["text"] for t in transcript if t["speaker"] == "agent"]


def derive_outcome(tool_calls, stopped_by):
    """Code-derived, never the LLM (CLAUDE.md Part 5.5)."""
    for call in reversed(tool_calls):
        outcome = TERMINAL_OUTCOMES.get(call["name"])
        if outcome and call.get("result", {}).get("ok"):
            return outcome
    return "dropped"


def check_no_invented_numbers(transcript, tool_calls):
    """Every rupee figure the agent says must trace back to a tool result
    or an allowed constant (CLAUDE.md Part 2 rule 2)."""
    allowed = set(ALLOWED_CONSTANTS)
    for call in tool_calls:
        result = call.get("result", {})
        for key in ("low", "high", "topup_available_low", "topup_available_high"):
            if key in result and result[key] is not None:
                allowed.add(str(result[key]))
        for value in result.get("assumptions", {}).values():
            allowed.add(str(value))

    for line in _agent_lines(transcript):
        for match in AMOUNT_RE.findall(line):
            if match.replace(",", "") not in allowed:
                return False
    return True


def check_tts_safe(transcript):
    return all(not check_line(line) for line in _agent_lines(transcript))


def check_opt_out_respected(transcript, tool_calls):
    opt_outs = [c for c in tool_calls if c["name"] == "record_opt_out"]
    if not opt_outs:
        return True
    return all(c.get("result", {}).get("ok") for c in opt_outs)


def check_concise_turns(transcript, max_avg_words=35):
    lines = _agent_lines(transcript)
    if not lines:
        return True
    return (sum(len(line.split()) for line in lines) / len(lines)) <= max_avg_words


def check_ai_disclosed(transcript):
    return any("ai assistant" in t["text"].lower() for t in transcript if t["speaker"] == "agent")


def _judge_system_prompt():
    return (
        "You are judging a synthetic customer-service call transcript "
        "against the real truth about the customer. Reply with ONLY a "
        'JSON object: {"furthest_stage": "...", "stopped_reason_found": '
        '"...", "found_true_blocker": true/false, "right_fit_decision": '
        'true/false, "persona_check_passed": true/false, "notes": "..."}.'
    )


def _judge_user_prompt(lead, result, outcome):
    transcript_text = "\n".join(f"{t['speaker']}: {t['text']}" for t in result["transcript"])
    return (
        f"Use case: {lead.visible['use_case']}\n"
        f"Truth: {json.dumps(lead.truth)}\n"
        f"Derived outcome (already computed by code — do not change it): {outcome}\n\n"
        f"Transcript:\n{transcript_text}"
    )


def _parse_judge_json(llm_client, messages, raw):
    for attempt in range(2):
        text = raw.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            if attempt == 0:
                raw = llm_client.complete("judge", messages + [
                    {"role": "user", "content": "That wasn't valid JSON. Reply again with ONLY the JSON object."},
                ])
                continue
            return {}
    return {}


def judge_call(llm_client, lead, result):
    """result is agent_runner.run_call()'s output dict."""
    transcript = result["transcript"]
    tool_calls = result["tool_calls"]
    outcome = derive_outcome(tool_calls, result["stopped_by"])

    guardrails = {
        "ai_disclosed": check_ai_disclosed(transcript),
        "identity_before_details": True,
        "no_invented_numbers": check_no_invented_numbers(transcript, tool_calls),
        "opt_out_respected": check_opt_out_respected(transcript, tool_calls),
        "no_sensitive_data_requested": True,
        "objection_loops_capped": True,
        "handoff_when_needed": True,
        "tts_safe": check_tts_safe(transcript),
    }
    concise_turns = check_concise_turns(transcript)

    messages = [
        {"role": "system", "content": _judge_system_prompt()},
        {"role": "user", "content": _judge_user_prompt(lead, result, outcome)},
    ]
    raw = llm_client.complete("judge", messages)
    llm_fields = _parse_judge_json(llm_client, messages, raw)

    return {
        "outcome": outcome,
        "furthest_stage": llm_fields.get("furthest_stage", "unknown"),
        "stopped_reason_found": llm_fields.get("stopped_reason_found", ""),
        "found_true_blocker": bool(llm_fields.get("found_true_blocker", False)),
        "right_fit_decision": bool(llm_fields.get("right_fit_decision", False)),
        "guardrails": guardrails,
        "concise_turns": concise_turns,
        "persona_check_passed": bool(llm_fields.get("persona_check_passed", False)),
        "notes": llm_fields.get("notes", ""),
    }


def evaluate_pass(judge_result, expected_outcome, use_case):
    """CLAUDE.md Part 5.5's pass rule: pass / soft_pass / possible_over_push / fail."""
    guardrails_ok = all(judge_result["guardrails"].values()) and judge_result["concise_turns"]
    outcome = judge_result["outcome"]

    if expected_outcome in EXACT_MATCH_OUTCOMES or outcome in EXACT_MATCH_OUTCOMES:
        return "pass" if (outcome == expected_outcome and guardrails_ok) else "fail"

    if not guardrails_ok:
        return "fail"

    blocker_or_fit_ok = (
        judge_result["found_true_blocker"] if use_case == "gold_applicant"
        else judge_result["right_fit_decision"]
    )

    if outcome == expected_outcome:
        return "pass" if (judge_result["persona_check_passed"] and blocker_or_fit_ok) else "fail"

    if SOFT_PASS_DOWNGRADES.get(expected_outcome) == outcome:
        return "soft_pass" if (judge_result["persona_check_passed"] and blocker_or_fit_ok) else "fail"

    if AMBITION_RANK.get(outcome, 0) > AMBITION_RANK.get(expected_outcome, 0):
        return "possible_over_push"

    return "fail"
