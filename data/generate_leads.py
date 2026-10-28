"""Seeded synthetic lead generator (CLAUDE.md Part 5.3).

EVERY distribution below (persona weights, blocker weights, city/language
mix, karat mix, amounts, timings) is an INVENTED ASSUMPTION for this demo.
Say so in reports; do not treat any of it as real-world data.

Usage: python data/generate_leads.py --n 200 --seed 42 --out data/out
"""

import argparse
import csv
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from random import Random

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.eligibility import Settings, calculate_eligibility

# PLACEHOLDER rates, same defaults as tools/eligibility.py — generation must
# be reproducible regardless of the local environment, so this never reads
# from the environment the way Settings.from_env() does.
ELIGIBILITY_SETTINGS = Settings()

NAMES = [
    "Ramesh", "Suresh", "Priya", "Anita", "Rajesh", "Sunita", "Vijay", "Kavita",
    "Manoj", "Deepa", "Arjun", "Pooja", "Rahul", "Neha", "Amit", "Sneha",
    "Sanjay", "Divya", "Vikram", "Meera", "Rohit", "Shalini", "Karthik",
    "Lakshmi", "Arun", "Geeta", "Naveen", "Swati", "Prakash", "Anjali",
    "Ganesh", "Radha",
]

CITIES = [
    "Bengaluru", "Mysuru", "Hubballi", "Chennai", "Coimbatore", "Hyderabad",
    "Kochi", "Pune", "Jaipur", "Lucknow",
]

CITY_LANGUAGE = {
    "Bengaluru": "Kannada", "Mysuru": "Kannada", "Hubballi": "Kannada",
    "Chennai": "Tamil", "Coimbatore": "Tamil",
    "Hyderabad": "Telugu",
    "Kochi": "Malayalam",
    "Pune": "Marathi",
    "Jaipur": "Hindi", "Lucknow": "Hindi",
}

UC1_SOURCES = ["ad", "app_download", "aggregator"]
UC2_SOURCES = ["app", "website"]

UC1_TRIGGER_DETAILS = {
    "ad": [
        "saw an ad for quick personal loans online",
        "noticed an ad about instant loan offers",
    ],
    "app_download": [
        "downloaded a loan app looking for personal loan offers",
        "installed an app comparing personal loans",
    ],
    "aggregator": [
        "asked for loan offers on a comparison site",
        "compared personal loan rates on an aggregator site",
    ],
}

STATED_LOAN_AMOUNT_CHOICES = [50000, 75000, 100000, 150000, 200000, 300000, 400000, 500000]
LAST_STEP_WEIGHTS = {
    "phone_verified": 0.25, "amount_entered": 0.30, "kyc_started": 0.30,
    "appraisal_slot_page": 0.15,
}
MINUTES_SINCE_STOP_CHOICES = [6, 15, 40, 90, 240, 600, 1440, 2880]
KARAT_WEIGHTS = {22: 0.80, 18: 0.10, 20: 0.05, 24: 0.05}

PERSONA_WEIGHTS = {
    "cooperative": 0.34, "busy": 0.14, "suspicious": 0.10, "forgetful": 0.08,
    "wants_human": 0.06, "hostile_dnd": 0.06, "confused_elderly": 0.04,
    "negotiator": 0.07, "wrong_person": 0.05, "adversarial": 0.03,
    "silent_no_answer": 0.03,
}

UC2_BLOCKER_WEIGHTS = {
    "unsure_amount": 0.22, "branch_far": 0.16, "unsure_documents": 0.14,
    "rate_unclear": 0.14, "safety_worry": 0.12, "got_money_elsewhere": 0.12,
    "just_browsing": 0.10,
}

PURPOSES = [
    "business expenses", "a medical emergency", "children's education",
    "a family wedding", "home renovation", "paying off another loan",
    "personal expenses",
]
NEEDS_MONEY_WITHIN_DAYS_CHOICES = [0, 1, 3, 7, 14, 30]

# PLACEHOLDER: a fixed "generated at" reference instant, so stopped_at is
# reproducible for a given seed instead of drifting with wall-clock time.
GENERATED_AT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

_PERSONA_OUTCOME_OVERRIDES = {
    "wrong_person": "wrong_person",
    "silent_no_answer": "no_answer",
    "hostile_dnd": "opt_out",
}
_PERSONA_CALLBACK = {"busy", "wants_human", "confused_elderly"}
_PERSONA_SOFT = {"suspicious", "forgetful", "negotiator"}


def weighted_choice(rng, weights):
    keys = list(weights.keys())
    values = list(weights.values())
    return rng.choices(keys, weights=values, k=1)[0]


def _preferred_language(rng, city):
    main = CITY_LANGUAGE[city]
    if main == "Hindi":
        return weighted_choice(rng, {"Hindi": 0.7, "English": 0.3})
    return weighted_choice(rng, {main: 0.5, "English": 0.3, "Hindi": 0.2})


def compute_expected_outcome(use_case, persona, truth):
    """The best outcome a good agent could reasonably reach (CLAUDE.md 5.3)."""
    if persona in _PERSONA_OUTCOME_OVERRIDES:
        return _PERSONA_OUTCOME_OVERRIDES[persona]
    if persona in _PERSONA_CALLBACK:
        return "callback_scheduled"

    if use_case == "loan_seeker":
        if not truth.get("owns_gold"):
            return "not_a_fit"
        amount_needed = truth.get("amount_needed") or 0
        eligible_amount = truth.get("eligible_amount") or 0
        if eligible_amount == 0 or amount_needed > 1.15 * eligible_amount:
            return "not_a_fit"
        if persona in _PERSONA_SOFT:
            return "whatsapp_sent"
        return "appraisal_booked"

    # gold_applicant (UC2)
    blocker = truth.get("true_blocker")
    if blocker == "got_money_elsewhere":
        return "not_interested"
    if blocker == "just_browsing":
        return "whatsapp_sent"
    if blocker == "rate_unclear":
        return "callback_scheduled"
    # UC2 analogue of UC1's amount-mismatch rule (docs/OPEN_QUESTIONS.md #13,
    # KC's decision): unlike UC1 this customer already owns gold and already
    # started an application, so the honest outcome when the gold can't
    # cover what they need is still whatsapp_sent (the range, to keep as a
    # lead), not not_a_fit.
    amount_needed = truth.get("amount_needed") or 0
    eligible_amount = truth.get("eligible_amount") or 0
    if eligible_amount > 0 and amount_needed > 1.15 * eligible_amount:
        return "whatsapp_sent"
    if persona in _PERSONA_SOFT:
        return "whatsapp_sent"
    return "appraisal_booked"


def _make_lead(index, rng, use_case):
    lead_id = f"{use_case}-{index:04d}"
    customer_name = rng.choice(NAMES)
    phone = "+910" + "".join(str(rng.randint(0, 9)) for _ in range(9))
    city = rng.choice(CITIES)
    preferred_language = _preferred_language(rng, city)
    dnd_flag = rng.random() < 0.08

    if use_case == "loan_seeker":
        source = rng.choice(UC1_SOURCES)
        consent_status = "aggregator_shared" if source == "aggregator" else "opted_in_form"
        call_trigger = source
        trigger_detail = rng.choice(UC1_TRIGGER_DETAILS[source])
        stated_loan_amount = rng.choice(STATED_LOAN_AMOUNT_CHOICES) if rng.random() > 0.3 else ""
        last_step_completed = ""
        minutes_since_stop = None
        stopped_at = ""
    else:
        source = rng.choice(UC2_SOURCES)
        consent_status = "applicant"
        call_trigger = "gold_loan_application"
        trigger_detail = ""
        stated_loan_amount = ""
        last_step_completed = weighted_choice(rng, LAST_STEP_WEIGHTS)
        minutes_since_stop = rng.choice(MINUTES_SINCE_STOP_CHOICES)
        stopped_at = (GENERATED_AT - timedelta(minutes=minutes_since_stop)).isoformat()

    lead = {
        "lead_id": lead_id,
        "use_case": use_case,
        "customer_name": customer_name,
        "phone": phone,
        "city": city,
        "preferred_language": preferred_language,
        "consent_status": consent_status,
        "dnd_flag": dnd_flag,
        "source": source,
        "call_trigger": call_trigger,
        "trigger_detail": trigger_detail,
        "stated_loan_amount": stated_loan_amount,
        "last_step_completed": last_step_completed,
        "minutes_since_stop": minutes_since_stop,
        "stopped_at": stopped_at,
    }

    owns_gold_prob = 0.72 if use_case == "loan_seeker" else 0.97
    owns_gold = rng.random() < owns_gold_prob
    if owns_gold:
        grams = round(rng.uniform(8, 80), 1)
        has_stones = rng.random() < 0.35
        purity_karat = weighted_choice(rng, KARAT_WEIGHTS)
    else:
        grams = 0
        has_stones = False
        purity_karat = 22

    persona = weighted_choice(rng, PERSONA_WEIGHTS)
    answers_phone = persona != "silent_no_answer"
    right_person = persona != "wrong_person"

    if use_case == "loan_seeker":
        if stated_loan_amount:
            amount_needed = max(10000, int(stated_loan_amount * rng.uniform(0.9, 1.2)))
        else:
            amount_needed = rng.choice(STATED_LOAN_AMOUNT_CHOICES)
        true_blocker = ""
    else:
        amount_needed = rng.choice(STATED_LOAN_AMOUNT_CHOICES)
        true_blocker = weighted_choice(rng, UC2_BLOCKER_WEIGHTS)

    purpose = rng.choice(PURPOSES)
    needs_money_within_days = rng.choice(NEEDS_MONEY_WITHIN_DAYS_CHOICES)

    if owns_gold:
        elig = calculate_eligibility(
            grams=grams, karat=purity_karat, has_stones=has_stones,
            settings=ELIGIBILITY_SETTINGS,
        )
        eligible_amount = elig["low"] if elig["ok"] else 0
    else:
        eligible_amount = 0

    truth = {
        "owns_gold": owns_gold,
        "grams": grams,
        "has_stones": has_stones,
        "purity_karat": purity_karat,
        "persona": persona,
        "answers_phone": answers_phone,
        "right_person": right_person,
        "amount_needed": amount_needed,
        "purpose": purpose,
        "eligible_amount": eligible_amount,
        "needs_money_within_days": needs_money_within_days,
        "true_blocker": true_blocker,
    }
    truth["expected_outcome"] = compute_expected_outcome(use_case, persona, truth)

    return {"lead": lead, "truth": truth}


def generate_leads(n=200, seed=42):
    """Deterministic given (n, seed). Exactly half gold_applicant, half loan_seeker."""
    rng = Random(seed)
    records = []
    for i in range(n):
        use_case = "gold_applicant" if i % 2 == 0 else "loan_seeker"
        records.append(_make_lead(i, rng, use_case))
    return records


def generate_one(use_case, seed, index=0):
    """A single deterministic lead of a given use_case (CLAUDE.md Part 5.3a)."""
    rng = Random(seed)
    return _make_lead(index, rng, use_case)


def build_lead_from_scenario(scenario, seed=0):
    """Turn a hand-written data/scenarios.yaml entry into a concrete lead
    record, by overriding a randomly generated base lead (CLAUDE.md 5.3a).
    """
    base = generate_one(scenario["use_case"], seed=seed)

    lead = dict(base["lead"])
    lead.update(scenario.get("lead_overrides") or {})
    lead["lead_id"] = f"scenario-{scenario['id']}"

    if lead["use_case"] == "gold_applicant" and lead.get("minutes_since_stop") is not None:
        # Keep stopped_at consistent if a scenario overrode minutes_since_stop.
        lead["stopped_at"] = (
            GENERATED_AT - timedelta(minutes=lead["minutes_since_stop"])
        ).isoformat()

    truth = dict(base["truth"])
    truth.update(scenario.get("truth_overrides") or {})

    if truth.get("owns_gold"):
        elig = calculate_eligibility(
            grams=truth.get("grams", 0), karat=truth.get("purity_karat", 22),
            has_stones=truth.get("has_stones", False), settings=ELIGIBILITY_SETTINGS,
        )
        truth["eligible_amount"] = elig["low"] if elig["ok"] else 0
    else:
        truth["eligible_amount"] = 0

    truth["expected_outcome"] = scenario["expected_outcome"]
    return {"lead": lead, "truth": truth}


def write_outputs(records, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    lead_fields = list(records[0]["lead"].keys()) if records else []
    with open(os.path.join(out_dir, "leads.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=lead_fields)
        writer.writeheader()
        for r in records:
            writer.writerow(r["lead"])

    truth_fields = ["lead_id"] + (list(records[0]["truth"].keys()) if records else [])
    with open(os.path.join(out_dir, "leads_truth.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=truth_fields)
        writer.writeheader()
        for r in records:
            writer.writerow({"lead_id": r["lead"]["lead_id"], **r["truth"]})

    with open(os.path.join(out_dir, "leads.jsonl"), "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="data/out")
    args = parser.parse_args()

    records = generate_leads(n=args.n, seed=args.seed)
    write_outputs(records, args.out)

    outcome_counts = Counter(r["truth"]["expected_outcome"] for r in records)
    dnd_share = sum(1 for r in records if r["lead"]["dnd_flag"]) / len(records)

    print(f"Generated {len(records)} leads (seed={args.seed}) -> {args.out}")
    print("All distributions are INVENTED ASSUMPTIONS for this demo.")
    print("Expected-outcome counts:")
    for outcome, count in sorted(outcome_counts.items()):
        print(f"  {outcome}: {count}")
    print(f"DND share: {dnd_share:.1%}")


if __name__ == "__main__":
    main()
