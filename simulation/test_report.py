"""Tests for simulation/report.py (CLAUDE.md Part 5.5)."""

from simulation.report import build_report


def _ok_result(lead_id, expected_outcome, stopped_reason_found):
    return {
        "lead_id": lead_id,
        "use_case": "gold_applicant",
        "turns": 3,
        "transcript": [{"speaker": "agent", "text": "Hello."}],
        "tool_calls": [],
        "verdict": {
            "outcome": "appraisal_booked",
            "expected_outcome": expected_outcome,
            "pass_result": "pass",
            "stopped_reason_found": stopped_reason_found,
            "guardrails": {"ai_disclosed": True},
        },
    }


def _error_result(lead_id):
    # Shaped like run_simulation.py's _run_one_safe() error placeholder:
    # no stopped_reason_found key at all, so .get() returns None.
    return {
        "lead_id": lead_id,
        "use_case": "gold_applicant",
        "turns": 0,
        "transcript": [],
        "tool_calls": [],
        "error": "RequestBudgetExceeded: hit the daily cap",
        "verdict": {
            "outcome": "error",
            "expected_outcome": "appraisal_booked",
            "pass_result": "error",
            "guardrails": {},
        },
    }


def test_build_report_does_not_crash_on_a_harness_error_result(tmp_path):
    # Regression: sorting the blocker table crashed with a TypeError when
    # one result had no stopped_reason_found key (None vs str comparison)
    # - exactly what a harness-error placeholder looks like.
    results = [_ok_result("gold_applicant-0000", "appraisal_booked", "unsure_amount"), _error_result("gold_applicant-0001")]
    path = build_report(results, str(tmp_path))
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    assert "Simulation report" in html
