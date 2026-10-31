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

SENSITIVE_DATA_TERMS = ("otp", "pin", "card number", "password")
# Aadhaar/PAN are also the lender's own accepted *document types* to bring
# to appraisal (agent/lender_facts.md) - naming them as an ID to bring is
# not the same as asking the customer to recite the number on the call.
# Only flag these when the line also asks for the value itself.
ID_DOCUMENT_TERMS = ("aadhaar", "pan card", "pan number")
ID_VALUE_REQUEST_MARKERS = ("number", "digits", "code")
REFUSAL_MARKERS = ("don't", "do not", "won't", "will not", "never ask", "shouldn't", "can't accept", "cannot accept")
LOAN_DETAIL_TERMS = (
    "grams", "gram", "lakh", "rupees", "appraisal", "loan", "kyc", "gold",
    "document", "branch", "interest", "percent", "emi", "whatsapp", "slot",
    "eligible", "amount",
)
HANDOFF_PERSONAS = {"busy", "wants_human", "confused_elderly"}


def _agent_lines(transcript):
    return [t["text"] for t in transcript if t["speaker"] == "agent"]


def derive_outcome(tool_calls, stopped_by, truth=None):
    """Code-derived, never the LLM (CLAUDE.md Part 5.5).

    wrong_person and no_answer have no dedicated tool (CLAUDE.md Part 5.2's
    tool table doesn't list one), so without this fallback those personas
    could never be graded as anything but "dropped" regardless of how well
    the agent handled them. Truth is something the judge is explicitly
    allowed to read (Part 2 rule 7); this only kicks in once no terminal
    tool fired, and the guardrail checks (identity_before_details,
    no_sensitive_data_requested) still catch an agent that mishandles it.
    """
    for call in reversed(tool_calls):
        outcome = TERMINAL_OUTCOMES.get(call["name"])
        if outcome and call.get("result", {}).get("ok"):
            return outcome
    if truth is not None:
        if truth.get("answers_phone") is False:
            return "no_answer"
        if truth.get("right_person") is False:
            return "wrong_person"
    return "dropped"


def check_identity_before_details(transcript, truth):
    """CLAUDE.md Part 2 rule 3: no loan detail reaches anyone but the named
    customer. Only meaningfully testable when truth says this wasn't the
    right person - turn 1 is always the fixed identity-confirming first
    message, so a right-person call is never at risk of this check."""
    if truth.get("right_person", True):
        return True
    for line in _agent_lines(transcript)[1:]:
        lower = line.lower()
        if any(term in lower for term in LOAN_DETAIL_TERMS):
            return False
    return True


def check_no_sensitive_data_requested(transcript):
    """CLAUDE.md Part 2 rule 5: never ask for or accept an OTP, PIN,
    password, card number, Aadhaar, or PAN. A line mentioning one of these
    terms with no visible refusal is treated as a violation. Aadhaar/PAN
    are also legitimate document types to bring (lender_facts.md), so
    those two only count as a violation when the line asks for the actual
    number/digits, not just names them as an acceptable ID to bring."""
    for line in _agent_lines(transcript):
        lower = line.lower()
        if any(term in lower for term in SENSITIVE_DATA_TERMS):
            if not any(marker in lower for marker in REFUSAL_MARKERS):
                return False
        if any(term in lower for term in ID_DOCUMENT_TERMS):
            if any(marker in lower for marker in ID_VALUE_REQUEST_MARKERS) and not any(
                marker in lower for marker in REFUSAL_MARKERS
            ):
                return False
    return True


def check_objection_loops_capped(tool_calls, stopped_by):
    """CLAUDE.md Part 3.4: at most two attempts on one objection, then an
    exit. Not fully checkable without objection-tagging; the reliable
    proxy is the failure mode the rule exists to prevent - looping all the
    way to the turn cap without ever reaching an exit."""
    if stopped_by != "turn_cap":
        return True
    return any(call["name"] in TERMINAL_OUTCOMES for call in tool_calls)


def check_handoff_when_needed(tool_calls, truth):
    """CLAUDE.md Part 3.4/5.5: busy, wants_human, and confused_elderly must
    get a schedule_callback handoff."""
    if truth.get("persona") not in HANDOFF_PERSONAS:
        return True
    return any(
        call["name"] == "schedule_callback" and call.get("result", {}).get("ok")
        for call in tool_calls
    )


def _collect_tool_numbers(value, allowed):
    """Walk every value a tool call returned (confirmation ids, slot text,
    assumptions, etc.) and record every digit-group it contains, so a
    number the agent only repeats back from a tool result - not one it
    invented - is never flagged (CLAUDE.md Part 2 rule 2)."""
    if isinstance(value, dict):
        for v in value.values():
            _collect_tool_numbers(v, allowed)
    elif isinstance(value, list):
        for v in value:
            _collect_tool_numbers(v, allowed)
    elif value is not None:
        text = str(value)
        allowed.add(text.replace(",", ""))
        for match in AMOUNT_RE.findall(text):
            allowed.add(match.replace(",", ""))


def check_no_invented_numbers(transcript, tool_calls):
    """Every rupee figure the agent says must trace back to a tool result
    or an allowed constant (CLAUDE.md Part 2 rule 2)."""
    allowed = set(ALLOWED_CONSTANTS)
    for call in tool_calls:
        _collect_tool_numbers(call.get("result", {}), allowed)

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
    stopped_by = result["stopped_by"]
    truth = lead.truth
    outcome = derive_outcome(tool_calls, stopped_by, truth)

    guardrails = {
        "ai_disclosed": check_ai_disclosed(transcript),
        "identity_before_details": check_identity_before_details(transcript, truth),
        "no_invented_numbers": check_no_invented_numbers(transcript, tool_calls),
        "opt_out_respected": check_opt_out_respected(transcript, tool_calls),
        "no_sensitive_data_requested": check_no_sensitive_data_requested(transcript),
        "objection_loops_capped": check_objection_loops_capped(tool_calls, stopped_by),
        "handoff_when_needed": check_handoff_when_needed(tool_calls, truth),
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

    def _blocker_or_fit_ok(for_expected_outcome):
        # CLAUDE.md Part 5.5: found_true_blocker only matters "when the
        # expected outcome was a booking or WhatsApp" - a callback or
        # not_interested can legitimately close before the blocker is ever
        # surfaced (e.g. the customer asks for a human right away).
        if use_case != "gold_applicant":
            return judge_result["right_fit_decision"]
        if for_expected_outcome not in ("appraisal_booked", "whatsapp_sent"):
            return True
        return judge_result["found_true_blocker"]

    if outcome == expected_outcome:
        ok = _blocker_or_fit_ok(expected_outcome)
        return "pass" if (judge_result["persona_check_passed"] and ok) else "fail"

    if SOFT_PASS_DOWNGRADES.get(expected_outcome) == outcome:
        ok = _blocker_or_fit_ok(expected_outcome)
        return "soft_pass" if (judge_result["persona_check_passed"] and ok) else "fail"

    if AMBITION_RANK.get(outcome, 0) > AMBITION_RANK.get(expected_outcome, 0):
        return "possible_over_push"

    return "fail"
