"""Gold-loan eligibility calculation (CLAUDE.md Part 5.1).

Pure functions, no I/O. The agent must never do its own arithmetic — every
rupee figure it speaks comes from calculate_eligibility().

ALL rate, LTV and margin numbers below are PLACEHOLDERS for the demo
("Suvarna Gold Finance" is a fictional lender) and are overridable via
environment variables through Settings.from_env().
"""

import math
import os
from dataclasses import dataclass

TOLA_TO_GRAM = 11.6638
VALID_KARATS = {18, 20, 22, 24}
VALID_REPAYMENT_TYPES = {"monthly", "bullet"}
VALID_UNITS = {"gram", "tola"}
MAX_PLAUSIBLE_GRAMS = 2000

# (low, high, ltv) — RBI Lending Against Gold and Silver Collateral
# Directions 2025 tiers (CLAUDE.md Part 1), effective 1 April 2026.
LTV_TIERS = (
    (0, 250_000, 0.85),
    (250_000, 500_000, 0.80),
    (500_000, float("inf"), 0.75),
)


@dataclass
class Settings:
    """All values are PLACEHOLDERS (CLAUDE.md Part 5.1)."""

    rate_30d_avg_22k: float = 11800  # rupees per gram, PLACEHOLDER
    rate_prev_close_22k: float = 12000  # rupees per gram, PLACEHOLDER
    interest_rate_pa: float = 0.12  # PLACEHOLDER, simple interest
    bullet_tenure_months: int = 12  # PLACEHOLDER
    stones_haircut: float = 0.10  # PLACEHOLDER: share of weight assumed not gold if stones
    general_margin: float = 0.05  # PLACEHOLDER: general appraisal margin, no stones
    round_down_to: int = 1000

    @classmethod
    def from_env(cls):
        def _float(name, default):
            raw = os.environ.get(name)
            return float(raw) if raw else default

        def _int(name, default):
            raw = os.environ.get(name)
            return int(raw) if raw else default

        return cls(
            rate_30d_avg_22k=_float("RATE_30D_AVG_22K", cls.rate_30d_avg_22k),
            rate_prev_close_22k=_float("RATE_PREV_CLOSE_22K", cls.rate_prev_close_22k),
            interest_rate_pa=_float("INTEREST_RATE_PA", cls.interest_rate_pa),
            bullet_tenure_months=_int("BULLET_TENURE_MONTHS", cls.bullet_tenure_months),
            stones_haircut=_float("STONES_HAIRCUT", cls.stones_haircut),
            general_margin=_float("GENERAL_MARGIN", cls.general_margin),
            round_down_to=_int("ROUND_DOWN_TO", cls.round_down_to),
        )


def _max_principal(effective_grams, karat, price_per_gram, bullet_factor, round_down_to):
    """Step 2-5 of CLAUDE.md Part 5.1: value -> tiered LTV -> rounded principal."""
    value = effective_grams * (karat / 22) * price_per_gram

    best_candidate = None
    best_ltv = None
    for low, high, ltv in LTV_TIERS:
        candidate = min(high, value * ltv / bullet_factor)
        if candidate > low and (best_candidate is None or candidate > best_candidate):
            best_candidate = candidate
            best_ltv = ltv

    principal = best_candidate or 0
    rounded = math.floor(principal / round_down_to) * round_down_to
    return rounded, best_ltv


def calculate_eligibility(
    grams,
    karat=22,
    repayment_type="monthly",
    has_stones=False,
    existing_loan=0,
    unit="gram",
    settings=None,
):
    """Return a conservative low-high eligibility range. Never raises."""
    try:
        settings = settings or Settings.from_env()

        if unit not in VALID_UNITS:
            return {"ok": False, "error": f"unit must be one of {sorted(VALID_UNITS)}"}

        grams = float(grams)
        if unit == "tola":
            grams = grams * TOLA_TO_GRAM

        if not (0 < grams <= MAX_PLAUSIBLE_GRAMS):
            return {
                "ok": False,
                "error": f"grams must be > 0 and no more than {MAX_PLAUSIBLE_GRAMS}",
            }

        if karat not in VALID_KARATS:
            return {"ok": False, "error": f"karat must be one of {sorted(VALID_KARATS)}"}

        if repayment_type not in VALID_REPAYMENT_TYPES:
            return {
                "ok": False,
                "error": f"repayment_type must be one of {sorted(VALID_REPAYMENT_TYPES)}",
            }

        existing_loan = float(existing_loan or 0)

        price_per_gram = min(settings.rate_30d_avg_22k, settings.rate_prev_close_22k)
        bullet_factor = (
            1 + settings.interest_rate_pa * settings.bullet_tenure_months / 12
            if repayment_type == "bullet"
            else 1.0
        )

        haircut = settings.stones_haircut if has_stones else settings.general_margin
        low_grams = grams * (1 - haircut)

        high, high_ltv = _max_principal(
            grams, karat, price_per_gram, bullet_factor, settings.round_down_to
        )
        low, _low_ltv = _max_principal(
            low_grams, karat, price_per_gram, bullet_factor, settings.round_down_to
        )

        low_spoken = indian_words(low)
        high_spoken = indian_words(high)

        if low == high:
            say_to_customer = (
                f"Based on what you've told me, you may be eligible for about "
                f"{high_spoken} rupees. This is indicative, and the final amount "
                f"can come out lower at appraisal."
            )
        else:
            say_to_customer = (
                f"Based on what you've told me, you may be eligible for about "
                f"{low_spoken} to {high_spoken} rupees. This is indicative, and "
                f"the final amount can come out lower at appraisal."
            )

        result = {
            "ok": True,
            "low": low,
            "high": high,
            "low_spoken": low_spoken,
            "high_spoken": high_spoken,
            "say_to_customer": say_to_customer,
            "assumptions": {
                "price_per_gram": price_per_gram,
                "ltv_used": high_ltv,
                "bullet_factor": bullet_factor,
                "haircut": haircut,
            },
        }

        if existing_loan > 0:
            result["topup_available_low"] = max(0, low - existing_loan)
            result["topup_available_high"] = max(0, high - existing_loan)

        return result
    except (TypeError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


_ONES = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
    "eighteen", "nineteen",
]
_TENS = [
    "", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety",
]


def _two_digit_words(n):
    if n < 20:
        return _ONES[n]
    tens, ones = divmod(n, 10)
    if ones == 0:
        return _TENS[tens]
    return f"{_TENS[tens]} {_ONES[ones]}"


def _three_digit_words(n):
    hundreds, rem = divmod(n, 100)
    parts = []
    if hundreds:
        parts.append(f"{_ONES[hundreds]} hundred")
    if rem:
        parts.append(_two_digit_words(rem))
    return " ".join(parts)


def indian_words(n):
    """Spoken Indian-English words for a non-negative integer rupee amount."""
    n = int(n)
    if n == 0:
        return "zero"

    crore, rem = divmod(n, 10_000_000)
    lakh, rem = divmod(rem, 100_000)
    thousand, rem = divmod(rem, 1000)
    hundreds = rem

    parts = []
    if crore:
        crore_words = _two_digit_words(crore) if crore < 100 else _three_digit_words(crore)
        parts.append(f"{crore_words} crore")
    if lakh:
        parts.append(f"{_two_digit_words(lakh)} lakh")
    if thousand:
        parts.append(f"{_two_digit_words(thousand)} thousand")
    if hundreds:
        parts.append(_three_digit_words(hundreds))

    return " ".join(parts)
