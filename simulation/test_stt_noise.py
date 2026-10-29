"""Tests for simulation/stt_noise.py (CLAUDE.md Part 5.4a H)."""

import random

from simulation.stt_noise import corrupt_line, with_environment_event


def test_number_swap_is_deterministic_and_changes_the_number():
    result = corrupt_line("I have about twenty grams of gold.")
    assert "twenty two" in result


def test_drop_or_merge_shortens_or_changes_a_line_without_numbers():
    text = "The branch is quite far from my place today"
    result = corrupt_line(text, rng=random.Random(1))
    assert result != text


def test_short_lines_are_left_alone():
    assert corrupt_line("Yes.") == "Yes."


def test_environment_events_have_the_right_markers():
    assert with_environment_event("hello", "silence_7s") == "[silence 7s] hello"
    assert with_environment_event("", "silence_14s") == "[silence 14s]"
    assert with_environment_event("wait", "interrupt") == "[customer interrupts] wait"
