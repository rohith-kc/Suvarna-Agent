"""Fake CRM builder (CLAUDE.md Part 5.3a).

Builds data/crm.sqlite from leads.jsonl using VISIBLE DATA ONLY, plus
invented history (call_history, notes, existing_loans — all placeholders).
Never reads or writes truth fields: data/test_leakage.py proves
read_customer_context() can't return any.

Usage: python data/build_crm.py --leads data/out/leads.jsonl --out data/crm.sqlite
"""

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from random import Random

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.generate_leads import GENERATED_AT

DEVICE_CHOICES = ["app", "web"]
CALL_HISTORY_RESULTS = ["no_answer", "asked_callback", "busy"]
# PLACEHOLDER: invented note content, standing in for real CRM/app-analytics notes.
NOTE_TEMPLATES = [
    "asked about interest rate in app chat",
    "opened the documents page twice",
    "started filling KYC but closed the app",
    "compared us with another lender in a support chat",
    "asked whether doorstep appraisal is available",
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    lead_id TEXT PRIMARY KEY,
    name TEXT,
    city TEXT,
    preferred_language TEXT,
    consent_status TEXT,
    dnd_flag INTEGER
);
CREATE TABLE IF NOT EXISTS enquiries (
    lead_id TEXT,
    source TEXT,
    trigger_detail TEXT,
    stated_loan_amount TEXT,
    enquired_at TEXT
);
CREATE TABLE IF NOT EXISTS applications (
    lead_id TEXT,
    product TEXT,
    last_step_completed TEXT,
    amount_entered TEXT,
    started_at TEXT,
    stopped_at TEXT,
    device TEXT
);
CREATE TABLE IF NOT EXISTS call_history (
    lead_id TEXT,
    attempt_no INTEGER,
    called_at TEXT,
    result TEXT
);
CREATE TABLE IF NOT EXISTS notes (
    lead_id TEXT,
    text TEXT
);
CREATE TABLE IF NOT EXISTS existing_loans (
    lead_id TEXT PRIMARY KEY,
    has_loan_with_us INTEGER,
    outstanding_amount REAL
);
"""


def _lead_rng(lead_id):
    """Stable per-lead randomness, independent of file order (CLAUDE.md 5.3a)."""
    digest = hashlib.sha256(lead_id.encode("utf-8")).hexdigest()
    return Random(int(digest[:8], 16))


def _invented_past_timestamp(rng, max_days_ago=20):
    days_ago = rng.randint(1, max_days_ago)
    return (GENERATED_AT - timedelta(days=days_ago)).isoformat()


def _started_at_before(stopped_at_iso, rng):
    """A plausible application-start time strictly before stopped_at."""
    if not stopped_at_iso:
        return _invented_past_timestamp(rng)
    stopped = datetime.fromisoformat(stopped_at_iso)
    return (stopped - timedelta(minutes=rng.randint(5, 180))).isoformat()


def build_crm(leads_path, db_path):
    leads = []
    with open(leads_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            leads.append(json.loads(line)["lead"])
    build_crm_from_leads(leads, db_path)


def build_crm_from_leads(leads, db_path):
    """Same as build_crm(), but from an already-in-memory list of visible
    lead dicts rather than a leads.jsonl file - lets a caller (e.g.
    run_simulation.py) build a CRM that's guaranteed to match whatever
    leads it actually sampled, regardless of seed (CLAUDE.md 5.3a: a
    lead_id like "gold_applicant-0000" names a different customer under
    each seed, so a CRM built from one seed's leads.jsonl would silently
    return the wrong person's history for a run using another seed)."""
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        for lead in leads:
            _insert_lead(conn, lead)
        conn.commit()
    finally:
        conn.close()


def _insert_lead(conn, lead):
    lead_id = lead["lead_id"]
    rng = _lead_rng(lead_id)

    conn.execute(
        "INSERT INTO customers (lead_id, name, city, preferred_language, consent_status, dnd_flag) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            lead_id, lead["customer_name"], lead["city"], lead["preferred_language"],
            lead["consent_status"], int(bool(lead["dnd_flag"])),
        ),
    )

    if lead["use_case"] == "loan_seeker":
        conn.execute(
            "INSERT INTO enquiries (lead_id, source, trigger_detail, stated_loan_amount, enquired_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                lead_id, lead["source"], lead["trigger_detail"],
                str(lead["stated_loan_amount"]), _invented_past_timestamp(rng),
            ),
        )
    else:
        conn.execute(
            "INSERT INTO applications (lead_id, product, last_step_completed, amount_entered, "
            "started_at, stopped_at, device) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                lead_id, "gold loan", lead["last_step_completed"],
                str(rng.choice([50000, 100000, 150000, 200000])),
                _started_at_before(lead.get("stopped_at", ""), rng),
                lead.get("stopped_at", ""), rng.choice(DEVICE_CHOICES),
            ),
        )

    if rng.random() < 0.30:
        conn.execute(
            "INSERT INTO call_history (lead_id, attempt_no, called_at, result) VALUES (?, ?, ?, ?)",
            (lead_id, 1, _invented_past_timestamp(rng), rng.choice(CALL_HISTORY_RESULTS)),
        )

    if rng.random() < 0.40:
        conn.execute(
            "INSERT INTO notes (lead_id, text) VALUES (?, ?)",
            (lead_id, rng.choice(NOTE_TEMPLATES)),
        )

    if rng.random() < 0.10:
        conn.execute(
            "INSERT INTO existing_loans (lead_id, has_loan_with_us, outstanding_amount) "
            "VALUES (?, ?, ?)",
            (lead_id, 1, float(rng.choice([30000, 60000, 90000, 120000]))),
        )


def apply_crm_overrides(db_path, lead_id, overrides):
    """Layer a scenario's crm_overrides onto an already-built CRM row
    (CLAUDE.md Part 5.3a / 5.8), for test-card generation and Phase 4's
    scenario runner.
    """
    if not overrides:
        return
    conn = sqlite3.connect(db_path)
    try:
        for row in overrides.get("call_history", []):
            conn.execute(
                "INSERT INTO call_history (lead_id, attempt_no, called_at, result) "
                "VALUES (?, ?, ?, ?)",
                (lead_id, row.get("attempt_no", 1), row.get("called_at", ""), row.get("result", "")),
            )
        for row in overrides.get("notes", []):
            conn.execute(
                "INSERT INTO notes (lead_id, text) VALUES (?, ?)",
                (lead_id, row.get("text", "")),
            )
        existing_loan = overrides.get("existing_loans")
        if existing_loan:
            conn.execute("DELETE FROM existing_loans WHERE lead_id = ?", (lead_id,))
            conn.execute(
                "INSERT INTO existing_loans (lead_id, has_loan_with_us, outstanding_amount) "
                "VALUES (?, ?, ?)",
                (
                    lead_id, int(bool(existing_loan.get("has_loan_with_us"))),
                    float(existing_loan.get("outstanding_amount", 0)),
                ),
            )
        conn.commit()
    finally:
        conn.close()


def read_customer_context(lead_id, db_path):
    """Visible CRM record + invented history only. Never a truth field."""
    if not os.path.exists(db_path):
        return None

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        customer = conn.execute(
            "SELECT * FROM customers WHERE lead_id = ?", (lead_id,)
        ).fetchone()
        if customer is None:
            return None

        context = {"customer": dict(customer)}
        context["customer"]["dnd_flag"] = bool(context["customer"]["dnd_flag"])

        for table, key in (
            ("enquiries", "enquiries"), ("applications", "applications"),
            ("call_history", "call_history"), ("notes", "notes"),
        ):
            rows = [dict(row) for row in conn.execute(
                f"SELECT * FROM {table} WHERE lead_id = ?", (lead_id,)
            )]
            if rows:
                context[key] = rows

        existing_loan = conn.execute(
            "SELECT * FROM existing_loans WHERE lead_id = ?", (lead_id,)
        ).fetchone()
        if existing_loan:
            row = dict(existing_loan)
            row["has_loan_with_us"] = bool(row["has_loan_with_us"])
            context["existing_loan"] = row

        return context
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--leads", default="data/out/leads.jsonl")
    parser.add_argument("--out", default="data/crm.sqlite")
    args = parser.parse_args()
    build_crm(args.leads, args.out)
    print(f"Built CRM at {args.out} from {args.leads}")


if __name__ == "__main__":
    main()
