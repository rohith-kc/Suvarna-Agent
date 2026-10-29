"""Simulates speech-recognition failure modes on customer lines, so a text
simulation can still exercise them (CLAUDE.md Part 5.4a H). Used for the
noisy_line persona and for a slice of --scenarios runs.
"""

import random

NUMBER_SWAPS = [
    ("twenty two", "twenty"), ("twenty", "twenty two"),
    ("fifteen", "fifty"), ("fifty", "fifteen"),
    ("thirteen", "thirty"), ("thirty", "thirteen"),
]

ENVIRONMENT_EVENTS = {
    "silence_7s": "[silence 7s]",
    "silence_14s": "[silence 14s]",
    "interrupt": "[customer interrupts]",
}


def corrupt_line(text, rng=None):
    """Garble a line the way a speech recogniser might: swap a number for
    a similar one, drop a word, or merge two words."""
    rng = rng or random.Random()
    lowered = text.lower()

    for original, swapped in NUMBER_SWAPS:
        if original in lowered:
            idx = lowered.index(original)
            return text[:idx] + swapped + text[idx + len(original):]

    words = text.split()
    if len(words) <= 2:
        return text

    mode = rng.choice(["drop_word", "merge_words"])
    if mode == "drop_word":
        idx = rng.randrange(len(words))
        return " ".join(words[:idx] + words[idx + 1:])

    idx = rng.randrange(len(words) - 1)
    merged = words[idx] + words[idx + 1]
    return " ".join(words[:idx] + [merged] + words[idx + 2:])


def with_environment_event(text, event):
    """event is one of 'silence_7s', 'silence_14s', 'interrupt'."""
    marker = ENVIRONMENT_EVENTS[event]
    return f"{marker} {text}".strip() if text else marker
