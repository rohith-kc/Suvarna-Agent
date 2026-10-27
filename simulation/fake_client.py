"""Deterministic fake LLM client (CLAUDE.md Part 5.5), used by --dry-run
and CI to exercise the whole pipeline — tool calls, transcript building,
judging — fully offline, with no real API calls.

It decides its next canned line from the content of the last message, not
from message counts, so it stays correct regardless of exactly how
agent_runner.py threads tool-result messages into the conversation.
"""

import json


class FakeClient:
    """Same complete(role, messages, json_schema=None) interface as
    simulation/llm.py."""

    def complete(self, role, messages, json_schema=None):
        if role == "customer":
            return self._customer_line(messages)
        if role == "agent":
            return self._agent_line(messages)
        if role == "judge":
            return self._judge_verdict(messages)
        raise ValueError(f"unknown role: {role!r}")

    @staticmethod
    def _last_content(messages):
        return messages[-1]["content"].lower() if messages else ""

    def _customer_line(self, messages):
        last = self._last_content(messages)
        if "book" in last and ("appraisal" in last or "slot" in last):
            return json.dumps({"say": "Saturday morning works. Thank you, goodbye. [HANGUP]"})
        if "still looking" in last or "did you get what you needed" in last:
            return json.dumps({"say": "Still looking, I wasn't sure how much I'd get."})
        if "grams" in last or "stones" in last or "karat" in last:
            return json.dumps({"say": "About 20 grams, no stones, 22 karat."})
        if "eligible" in last or "rupees" in last:
            return json.dumps({"say": "Okay, that sounds fine, let's book it."})
        return json.dumps({"say": "Yes, speaking."})

    def _agent_line(self, messages):
        last = self._last_content(messages)
        if "[tool result" in last and "calculate_eligibility" in last:
            return json.dumps({
                "say": "Based on what you've told me, you may be eligible for a range. "
                       "Shall we book an appraisal?",
                "tool": None, "end_call": False,
            })
        if "[tool result" in last and "book_appraisal" in last:
            return json.dumps({"say": "Wonderful, thank you, goodbye.", "tool": None, "end_call": True})
        if "grams" in last and ("karat" in last or "stones" in last):
            return json.dumps({
                "say": "Let me check that for you.",
                "tool": {"name": "calculate_eligibility", "args": {"grams": 20, "karat": 22, "has_stones": False}},
                "end_call": False,
            })
        if "book it" in last or "sounds fine" in last or "works" in last:
            return json.dumps({
                "say": "Let me book that for you.",
                "tool": {
                    "name": "book_appraisal",
                    "args": {"customer_name": "Test Customer", "mode": "branch", "slot": "Saturday morning"},
                },
                "end_call": False,
            })
        if "still looking" in last or "wasn't sure" in last:
            return json.dumps({
                "say": "No problem. Roughly how many grams do you have, and any stones?",
                "tool": None, "end_call": False,
            })
        if "yes, speaking" in last or "speaking" in last:
            return json.dumps({
                "say": "Did you get what you needed, or are you still looking?",
                "tool": None, "end_call": False,
            })
        return json.dumps({"say": "Thank you, goodbye.", "tool": None, "end_call": True})

    def _judge_verdict(self, messages):
        return json.dumps({
            "furthest_stage": "close",
            "stopped_reason_found": "unsure_amount",
            "found_true_blocker": True,
            "right_fit_decision": True,
            "persona_check_passed": True,
            "notes": "fake judge: canned verdict for --dry-run / CI",
        })
