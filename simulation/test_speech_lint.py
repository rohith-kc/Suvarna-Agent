"""Tests for simulation/speech_lint.py (CLAUDE.md Part 5.4a H)."""

from simulation.speech_lint import check_line, is_safe


def test_clean_line_is_safe():
    assert is_safe("Based on what you've told me, you may be eligible for about one lakh rupees.")


def test_markdown_is_flagged():
    assert "markdown" in check_line("Here are the **documents** you need.")


def test_rupee_symbol_is_flagged():
    assert "rupee_symbol" in check_line("That's about ₹20,000.")


def test_url_is_flagged():
    assert "url" in check_line("Check https://example.com for details.")


def test_brackets_are_flagged():
    assert "brackets" in check_line("Your range is [200000, 250000].")


def test_long_digit_string_is_flagged():
    assert "long_digit_string" in check_line("Your account number is 12345.")


def test_too_many_sentences_is_flagged():
    text = "This is one. This is two. This is three."
    assert "too_many_sentences" in check_line(text)


def test_too_many_words_is_flagged():
    text = " ".join(["word"] * 40)
    assert "too_many_words" in check_line(text)


def test_banned_jargon_is_flagged():
    assert any(v.startswith("banned_jargon") for v in check_line("This is a bullet loan."))


def test_banned_jargon_allowed_if_customer_used_it_first():
    violations = check_line("Yes, that's the tenure.", customer_used_words={"tenure"})
    assert not any(v.startswith("banned_jargon") for v in violations)


def test_emoji_is_flagged():
    assert "emoji" in check_line("Great news! \U0001F389")
