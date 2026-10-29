"""CLI: samples leads, runs simulated calls, writes results (CLAUDE.md
Part 5.5).

    python simulation/run_simulation.py --dry-run
    python simulation/run_simulation.py --use-case gold_applicant --n 60 --runs 1 --seed 42
    python simulation/run_simulation.py --lead-id gold_applicant-0007 --verbose
    python simulation/run_simulation.py --scenarios
"""

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml

from data.build_crm import build_crm_from_leads
from data.compliance import is_callable
from data.generate_leads import build_lead_from_scenario, generate_leads
from data.loader import Lead, dynamic_variables
from simulation.agent_runner import run_call
from simulation.config import Config
from simulation.fake_client import FakeClient
from simulation.judge import evaluate_pass, judge_call
from simulation.report import build_report

FIRST_MESSAGE_TEMPLATE = (
    "Hello, this is {agent_name}, an AI assistant calling from {lender_name}. "
    "Am I speaking with {customer_name}?"
)


def _first_message(lead):
    return FIRST_MESSAGE_TEMPLATE.format(**dynamic_variables(lead))


def _stable_seed(text):
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _load_scenario_leads():
    with open("data/scenarios.yaml", "r", encoding="utf-8") as f:
        scenarios = yaml.safe_load(f)["scenarios"]
    pairs = []
    for scenario in scenarios:
        record = build_lead_from_scenario(scenario, seed=_stable_seed(scenario["id"]))
        lead = Lead(visible=record["lead"], truth=record["truth"])
        pairs.append((lead, scenario["expected_outcome"]))
    return pairs


def _make_client(config):
    if config.provider == "fake":
        return FakeClient()

    from simulation.llm import complete as llm_complete

    class _ProviderClient:
        def complete(self, role, messages, json_schema=None):
            return llm_complete(role, messages, json_schema=json_schema, config=config)

    return _ProviderClient()


def run_one(lead, client, expected_outcome=None):
    first_message = _first_message(lead)
    result = run_call(lead, client, first_message)
    verdict = judge_call(client, lead, result)
    expected = expected_outcome if expected_outcome is not None else lead.truth.get("expected_outcome")
    verdict["expected_outcome"] = expected
    verdict["pass_result"] = evaluate_pass(verdict, expected, lead.visible["use_case"])
    return {
        "lead_id": lead.visible["lead_id"],
        "use_case": lead.visible["use_case"],
        "transcript": result["transcript"],
        "tool_calls": result["tool_calls"],
        "turns": result["turns"],
        "stopped_by": result["stopped_by"],
        "verdict": verdict,
    }


def _run_one_safe(lead, client, expected_outcome=None):
    """Never raises — one call failing (a 429 that outlasts retries, a
    harness error) must not lose every other call's results in the batch.
    Returns an error placeholder instead, flagged clearly in the report."""
    try:
        return run_one(lead, client, expected_outcome)
    except Exception as exc:  # noqa: BLE001 - deliberately broad; see docstring
        return {
            "lead_id": lead.visible["lead_id"],
            "use_case": lead.visible["use_case"],
            "transcript": [],
            "tool_calls": [],
            "turns": 0,
            "stopped_by": "harness_error",
            "error": f"{type(exc).__name__}: {exc}",
            "verdict": {
                "outcome": "error",
                "expected_outcome": expected_outcome if expected_outcome is not None else lead.truth.get("expected_outcome"),
                "pass_result": "error",
                "guardrails": {},
            },
        }


def _write_results(results, run_dir):
    os.makedirs(os.path.join(run_dir, "transcripts"), exist_ok=True)
    for r in results:
        with open(os.path.join(run_dir, "transcripts", f"{r['lead_id']}.json"), "w", encoding="utf-8") as f:
            json.dump(r, f, indent=2)
    with open(os.path.join(run_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


def _print_verbose(outcome):
    print(f"=== {outcome['lead_id']} ===")
    for t in outcome["transcript"]:
        print(f"{t['speaker']}: {t['text']}")
    print("--- tool calls ---")
    for c in outcome["tool_calls"]:
        print(c)
    print("--- verdict ---")
    print(json.dumps(outcome["verdict"], indent=2))


def _build_crm_for_this_run(leads_visible):
    """get_customer_context looks a lead up by lead_id alone (CLAUDE.md
    5.3a), but "gold_applicant-0000" names a different customer under
    every seed - a CRM built once from one seed's leads.jsonl would
    silently hand the agent a different lead's history whenever this run
    uses another seed or a scenario lead_id. Build one fresh, scoped to
    exactly the leads this run will actually call, every time."""
    db_path = os.path.join(tempfile.gettempdir(), f"suvarna_crm_{os.getpid()}.sqlite")
    build_crm_from_leads(leads_visible, db_path)
    os.environ["CRM_DB_PATH"] = db_path


def _sample_candidates(n, seed, use_case):
    records = generate_leads(n=max(n * 3, n), seed=seed)
    candidates = [Lead(visible=r["lead"], truth=r["truth"]) for r in records]
    if use_case:
        candidates = [lead for lead in candidates if lead.visible["use_case"] == use_case]
    return [(lead, None) for lead in candidates if is_callable(lead)][:n]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--use-case", choices=["gold_applicant", "loan_seeker"])
    parser.add_argument("--n", type=int, default=60)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--lead-id")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--scenarios", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true", help="confirm a run of more than 20 calls")
    args = parser.parse_args()

    config = Config.from_env()
    if args.dry_run:
        config.provider = "fake"
    client = _make_client(config)

    if args.lead_id:
        index = int(args.lead_id.rsplit("-", 1)[-1]) + 1
        records = generate_leads(n=index, seed=args.seed)
        match = next((r for r in records if r["lead"]["lead_id"] == args.lead_id), None)
        if match is None:
            print(f"lead_id {args.lead_id} not found with seed {args.seed}")
            return 1
        lead = Lead(visible=match["lead"], truth=match["truth"])
        _build_crm_for_this_run([lead.visible])
        outcome = run_one(lead, client)
        if args.verbose:
            _print_verbose(outcome)
        _write_results([outcome], "runs/manual")
        return 0

    if args.scenarios:
        calls = _load_scenario_leads()
    else:
        n = 3 if args.dry_run else args.n
        calls = _sample_candidates(n, args.seed, args.use_case)
    _build_crm_for_this_run([lead.visible for lead, _ in calls])

    if not args.dry_run and len(calls) > 20 and not args.yes:
        print(
            f"About to run {len(calls)} calls against provider={config.provider!r}. "
            f"Re-run with --yes to confirm (cost guard, CLAUDE.md Part 5.5)."
        )
        return 1

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    run_dir = f"runs/{timestamp}"
    results = []

    for _ in range(args.runs):
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futures = [pool.submit(_run_one_safe, lead, client, expected) for lead, expected in calls]
            for fut in futures:
                results.append(fut.result())

    _write_results(results, run_dir)
    report_path = build_report(results, run_dir)

    error_count = sum(1 for r in results if r["verdict"]["pass_result"] == "error")
    pass_count = sum(1 for r in results if r["verdict"]["pass_result"] == "pass")
    guardrail_pass = sum(
        1 for r in results if r["verdict"]["guardrails"] and all(r["verdict"]["guardrails"].values())
    )
    print(f"Ran {len(results)} calls (provider={config.provider}).")
    if error_count:
        print(f"Harness errors (not graded): {error_count}/{len(results)}")
    print(f"Pass rate: {pass_count}/{len(results)}")
    print(f"Guardrail pass rate: {guardrail_pass}/{len(results)}")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
