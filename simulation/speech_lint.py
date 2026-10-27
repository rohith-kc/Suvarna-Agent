"""Deterministic checker that an agent line is safe to speak aloud
(CLAUDE.md Part 5.4a H). A violation fails the tts_safe guardrail.
"""

import re

BANNED_JARGON = ["ltv", "valuation methodology", "bullet loan", "tenure"]
DIGIT_RUN_RE = re.compile(r"\d{4,}")
MARKDOWN_RE = re.compile(r"[*_`#]|\[.*?\]\(.*?\)")
BRACKET_RE = re.compile(r"[\[\]{}]")
URL_RE = re.compile(r"https?://|www\.")
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF]")


def check_line(text, customer_used_words=None):
    """Returns a list of violation strings; empty means the line is safe."""
    customer_used_words = customer_used_words or set()
    violations = []

    if MARKDOWN_RE.search(text):
        violations.append("markdown")
    if EMOJI_RE.search(text):
        violations.append("emoji")
    if "₹" in text:
        violations.append("rupee_symbol")
    if URL_RE.search(text):
        violations.append("url")
    if BRACKET_RE.search(text):
        violations.append("brackets")
    if DIGIT_RUN_RE.search(text):
        violations.append("long_digit_string")

    sentence_count = len([s for s in re.split(r"[.!?]+", text) if s.strip()])
    if sentence_count > 2:
        violations.append("too_many_sentences")

    word_count = len(text.split())
    if word_count > 35:
        violations.append("too_many_words")

    lowered = text.lower()
    for term in BANNED_JARGON:
        if term in lowered and term not in customer_used_words:
            violations.append(f"banned_jargon:{term}")

    return violations


def is_safe(text, customer_used_words=None):
    return not check_line(text, customer_used_words)
