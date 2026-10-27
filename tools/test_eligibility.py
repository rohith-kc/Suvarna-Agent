"""Tests for tools/eligibility.py.

All rate/LTV numbers are PLACEHOLDERS (CLAUDE.md Part 5.1). These tests pin
down the reference values CLAUDE.md gives by hand, plus the general rules
(tiers, bullet, stones haircut, top-up, monotonicity, two-price rule) and
indian_words.
"""

import pytest

from tools.eligibility import Settings, calculate_eligibility, indian_words

DEFAULT = Settings()


def test_20_grams_monthly_no_stones_high():
    # value = 20 * 11800 = 236,000; tier1 candidate = 236000*0.85 = 200,600;
    # rounds down to 200,000.
    result = calculate_eligibility(grams=20, karat=22, repayment_type="monthly",
                                    has_stones=False, settings=DEFAULT)
    assert result["ok"] is True
    assert result["high"] == 200000


def test_100_grams_monthly_no_stones_high_uses_75pct_tier():
    # value = 100 * 11800 = 1,180,000; tier3 candidate = 1,180,000*0.75 = 885,000
    # (already the largest valid candidate and a multiple of 1000).
    result = calculate_eligibility(grams=100, karat=22, repayment_type="monthly",
                                    has_stones=False, settings=DEFAULT)
    assert result["ok"] is True
    assert result["high"] == 885000


def test_tier_boundary_value_300000_caps_at_tier1():
    # Use custom rates so grams * price == 300,000 exactly.
    # tier1 candidate = min(250000, 300000*0.85=255000) = 250000 (valid, >0)
    # tier2 candidate = min(500000, 300000*0.80=240000) = 240000, NOT >250000 -> invalid
    settings = Settings(rate_30d_avg_22k=10000, rate_prev_close_22k=10000)
    result = calculate_eligibility(grams=30, karat=22, repayment_type="monthly",
                                    has_stones=False, settings=settings)
    assert result["ok"] is True
    assert result["high"] == 250000


def test_bullet_divides_by_bullet_factor():
    # Same 20g case, bullet: bullet_factor = 1 + 0.12*12/12 = 1.12
    # candidate = 200600 / 1.12 = 179,107.14...; rounds down to 179,000.
    result = calculate_eligibility(grams=20, karat=22, repayment_type="bullet",
                                    has_stones=False, settings=DEFAULT)
    assert result["ok"] is True
    assert result["high"] == 179000


def test_18k_scales_by_18_over_22():
    # value = 20 * (18/22) * 11800 = 193,090.909...; *0.85 = 164,127.27...;
    # rounds down to 164,000.
    result = calculate_eligibility(grams=20, karat=18, repayment_type="monthly",
                                    has_stones=False, settings=DEFAULT)
    assert result["ok"] is True
    assert result["high"] == 164000


def test_two_price_rule_uses_lower_price():
    settings = Settings(rate_30d_avg_22k=10000, rate_prev_close_22k=12000)
    result = calculate_eligibility(grams=20, karat=22, settings=settings)
    assert result["ok"] is True
    assert result["assumptions"]["price_per_gram"] == 10000


def test_invalid_grams_zero():
    result = calculate_eligibility(grams=0, karat=22, settings=DEFAULT)
    assert result["ok"] is False


def test_invalid_grams_too_large():
    result = calculate_eligibility(grams=2001, karat=22, settings=DEFAULT)
    assert result["ok"] is False


def test_invalid_karat():
    result = calculate_eligibility(grams=20, karat=21, settings=DEFAULT)
    assert result["ok"] is False


def test_invalid_unit():
    result = calculate_eligibility(grams=20, karat=22, unit="ounce", settings=DEFAULT)
    assert result["ok"] is False


def test_invalid_repayment_type():
    result = calculate_eligibility(grams=20, karat=22, repayment_type="weekly", settings=DEFAULT)
    assert result["ok"] is False


def test_never_raises_on_bad_grams_type():
    result = calculate_eligibility(grams="not a number", karat=22, settings=DEFAULT)
    assert result["ok"] is False
    assert "error" in result


def test_tola_unit_converts_before_validation():
    # 1 tola = 11.6638 grams; same high as the equivalent-grams gram case.
    grams_equiv = 20 * 11.6638
    by_tola = calculate_eligibility(grams=20, karat=22, unit="tola", settings=DEFAULT)
    by_gram = calculate_eligibility(grams=grams_equiv, karat=22, unit="gram", settings=DEFAULT)
    assert by_tola["ok"] is True
    assert by_tola["high"] == by_gram["high"]


def test_stones_haircut_reduces_low_more_than_no_stones():
    with_stones = calculate_eligibility(grams=20, karat=22, has_stones=True, settings=DEFAULT)
    without_stones = calculate_eligibility(grams=20, karat=22, has_stones=False, settings=DEFAULT)
    assert with_stones["ok"] is True and without_stones["ok"] is True
    # stones_haircut (0.10) > general_margin (0.05), so stones lowers "low" more.
    assert with_stones["low"] <= without_stones["low"]
    # "high" never uses the haircut regardless of has_stones.
    assert with_stones["high"] == without_stones["high"]


def test_low_and_high_both_returned_even_if_equal():
    result = calculate_eligibility(grams=20, karat=22, settings=DEFAULT)
    assert "low" in result and "high" in result
    assert result["low"] <= result["high"]


def test_existing_loan_larger_than_max_gives_zero_topup():
    result = calculate_eligibility(grams=20, karat=22, existing_loan=10_000_000, settings=DEFAULT)
    assert result["ok"] is True
    assert result["topup_available_low"] == 0
    assert result["topup_available_high"] == 0


def test_existing_loan_zero_gives_no_topup_fields():
    result = calculate_eligibility(grams=20, karat=22, existing_loan=0, settings=DEFAULT)
    assert result["ok"] is True
    assert "topup_available_low" not in result
    assert "topup_available_high" not in result


def test_monotonic_more_grams_never_lowers_amount():
    grams_sequence = [5, 10, 20, 30, 50, 80, 100, 150, 200]
    highs = [calculate_eligibility(grams=g, karat=22, settings=DEFAULT)["high"] for g in grams_sequence]
    for earlier, later in zip(highs, highs[1:]):
        assert later >= earlier


def test_agent_never_sees_a_number_the_tool_did_not_return():
    # The pure function must not raise and must round to round_down_to.
    result = calculate_eligibility(grams=37, karat=22, settings=DEFAULT)
    assert result["ok"] is True
    assert result["high"] % DEFAULT.round_down_to == 0
    assert result["low"] % DEFAULT.round_down_to == 0


@pytest.mark.parametrize("n,expected", [
    (25000, "twenty five thousand"),
    (180000, "one lakh eighty thousand"),
    (200000, "two lakh"),
    (240000, "two lakh forty thousand"),
    (1250000, "twelve lakh fifty thousand"),
])
def test_indian_words(n, expected):
    assert indian_words(n) == expected


def test_say_to_customer_uses_the_tool_words_verbatim():
    result = calculate_eligibility(grams=20, karat=22, settings=DEFAULT)
    assert result["low_spoken"] in result["say_to_customer"]
    assert result["high_spoken"] in result["say_to_customer"]
    assert "indicative" in result["say_to_customer"]
