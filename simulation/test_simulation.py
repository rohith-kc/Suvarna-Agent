"""CLI-level tests for simulation/run_simulation.py (CLAUDE.md Part 5.5,
5.6): --dry-run must produce a report.html fully offline.
"""

import json
import os
import subprocess
import sys

import pytest


def test_dry_run_produces_a_report(tmp_path):
    result = subprocess.run(
        [sys.executable, "simulation/run_simulation.py", "--dry-run"],
        cwd=os.getcwd(), capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Report: runs/" in result.stdout

    report_line = next(line for line in result.stdout.splitlines() if line.startswith("Report:"))
    report_path = report_line.split("Report: ", 1)[1].strip()
    assert os.path.exists(report_path)

    with open(report_path, "r", encoding="utf-8") as f:
        html = f.read()
    assert "Simulation report" in html


def test_scenarios_run_with_fake_client_all_pass_guardrails():
    result = subprocess.run(
        [sys.executable, "simulation/run_simulation.py", "--scenarios", "--dry-run"],
        cwd=os.getcwd(), capture_output=True, text=True, timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    report_line = next(line for line in result.stdout.splitlines() if line.startswith("Report:"))
    run_dir = os.path.dirname(report_line.split("Report: ", 1)[1].strip())
    with open(os.path.join(run_dir, "results.json"), "r", encoding="utf-8") as f:
        results = json.load(f)

    assert len(results) == 40
    for r in results:
        assert all(r["verdict"]["guardrails"].values()), (
            f"guardrail failure in {r['lead_id']}: {r['verdict']['guardrails']}"
        )
