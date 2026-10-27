"""results.json -> a self-contained report.html (CLAUDE.md Part 5.5)."""

import html
import json
import os
from collections import Counter


def build_report(results, run_dir):
    path = os.path.join(run_dir, "report.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(_render_html(results))
    return path


def _funnel(results):
    n = len(results) or 1
    return {
        "answered": sum(1 for r in results if r["verdict"]["outcome"] != "no_answer"),
        "right_person": sum(1 for r in results if r["verdict"]["outcome"] != "wrong_person"),
        "reached_core_step": sum(
            1 for r in results
            if any(c["name"] == "calculate_eligibility" for c in r["tool_calls"])
            or r["verdict"]["outcome"] in ("not_a_fit", "not_interested")
        ),
        "next_step_taken": sum(
            1 for r in results
            if r["verdict"]["outcome"] in ("appraisal_booked", "whatsapp_sent", "callback_scheduled")
        ),
        "_n": n,
    }


def _render_html(results):
    n = len(results)
    pass_counts = Counter(r["verdict"]["pass_result"] for r in results)
    guardrail_pass = sum(1 for r in results if all(r["verdict"]["guardrails"].values()))
    avg_turns = (sum(r["turns"] for r in results) / n) if n else 0
    funnel = _funnel(results)

    outcome_matrix = Counter(
        (r["verdict"].get("expected_outcome") or "?", r["verdict"]["outcome"]) for r in results
    )
    outcome_rows = "".join(
        f"<tr><td>{html.escape(str(exp))}</td><td>{html.escape(str(act))}</td><td>{count}</td></tr>"
        for (exp, act), count in sorted(outcome_matrix.items())
    )

    guardrail_failures = [r for r in results if not all(r["verdict"]["guardrails"].values())]
    failures_html = "".join(
        f"<li><a href=\"transcripts/{html.escape(r['lead_id'])}.json\">{html.escape(r['lead_id'])}</a>: "
        f"{html.escape(json.dumps({k: v for k, v in r['verdict']['guardrails'].items() if not v}))}</li>"
        for r in guardrail_failures
    )

    blocker_rows = ""
    uc2_results = [r for r in results if r.get("use_case") == "gold_applicant"]
    if uc2_results:
        blocker_counts = Counter(
            (r["verdict"].get("expected_outcome"), r["verdict"].get("stopped_reason_found"))
            for r in uc2_results
        )
        blocker_rows = "".join(
            f"<tr><td>{html.escape(str(a))}</td><td>{html.escape(str(b))}</td><td>{c}</td></tr>"
            for (a, b), c in sorted(blocker_counts.items())
        )

    failed_first = sorted(results, key=lambda r: r["verdict"]["pass_result"] == "pass")
    worst_html = ""
    for r in failed_first[:3]:
        lines = "".join(
            f"<p><b>{html.escape(t['speaker'])}:</b> {html.escape(t['text'])}</p>"
            for t in r["transcript"]
        )
        worst_html += (
            f"<details><summary>{html.escape(r['lead_id'])} — {r['verdict']['pass_result']} "
            f"(outcome: {html.escape(r['verdict']['outcome'])}, "
            f"expected: {html.escape(str(r['verdict'].get('expected_outcome')))})</summary>{lines}</details>"
        )

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Simulation report</title>
<style>
body {{ font-family: sans-serif; max-width: 900px; margin: 2em auto; color: #222; }}
table {{ border-collapse: collapse; width: 100%; margin-bottom: 1.5em; }}
td, th {{ border: 1px solid #ccc; padding: 4px 8px; text-align: left; }}
details {{ margin-bottom: 0.5em; border: 1px solid #ddd; padding: 0.5em; }}
.headline {{ background: #f6f6f6; padding: 1em; border-radius: 6px; }}
</style></head><body>
<h1>Simulation report</h1>
<p><b>Synthetic customers; every distribution is an invented assumption.
The agent model under test is indicative of prompt and logic quality, not
a prediction of voice-platform behaviour.</b></p>
<div class="headline">
<p>Calls run: {n} &middot; Pass: {pass_counts.get('pass', 0)} &middot;
Soft pass: {pass_counts.get('soft_pass', 0)} &middot;
Possible over-push: {pass_counts.get('possible_over_push', 0)} &middot;
Fail: {pass_counts.get('fail', 0)}</p>
<p>Guardrail pass rate: {guardrail_pass}/{n} &middot; Average turns: {avg_turns:.1f}</p>
</div>

<h2>Funnel</h2>
<table>
<tr><th>Stage</th><th>Count</th></tr>
<tr><td>Answered (not no_answer)</td><td>{funnel['answered']}/{n}</td></tr>
<tr><td>Right person (not wrong_person)</td><td>{funnel['right_person']}/{n}</td></tr>
<tr><td>Reached core step</td><td>{funnel['reached_core_step']}/{n}</td></tr>
<tr><td>Next step taken (booked / WhatsApp / callback)</td><td>{funnel['next_step_taken']}/{n}</td></tr>
</table>

<h2>Expected vs actual outcome</h2>
<table><tr><th>Expected</th><th>Actual</th><th>Count</th></tr>{outcome_rows}</table>

<h2>Guardrail failures</h2>
<ul>{failures_html or "<li>none</li>"}</ul>

<h2>Blocker table (UC2): expected outcome vs reason the judge found</h2>
<table><tr><th>Expected outcome</th><th>Stopped reason found</th><th>Count</th></tr>{blocker_rows or ''}</table>

<h2>Worst transcripts</h2>
{worst_html or "<p>No failing transcripts.</p>"}
</body></html>"""
