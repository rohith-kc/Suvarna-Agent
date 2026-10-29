"""STUB — Phase 0 scaffold only.

Full implementation (sampling leads, running calls with a thread pool,
retries/backoff, cost guard, transcripts, results.json) is built in Phase 4
(CLAUDE.md Part 5.5). For now, --dry-run only verifies the CLI and exits 0
so CI has something real to run; Phase 4 wires it to fake_client.py for a
genuine offline pipeline check.
"""

import argparse
import sys


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
    args = parser.parse_args()

    if args.dry_run:
        print("Phase 0 stub: CLI wiring OK. Full --dry-run pipeline built in Phase 4.")
        return 0

    raise NotImplementedError("Phase 4: implement per CLAUDE.md Part 5.5")


if __name__ == "__main__":
    sys.exit(main())
