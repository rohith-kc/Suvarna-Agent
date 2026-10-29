"""Prompt rendering tests (CLAUDE.md Phase 3 done-when criteria).

Renders the UC2 prompt for the sample leads and proves: no unresolved
{{...}} variables remain, no truth field leaks into what the LLM (or
ElevenLabs) actually sees, and the word budget (Part 2 rule 9) holds.
"""

import re

from agent.prompt import render, render_static
from data.loader import dynamic_variables, load_leads

UNRESOLVED_VAR_RE = re.compile(r"\{\{[a-zA-Z_]+\}\}")


def _uc2_sample_leads():
    leads = load_leads("data/sample/leads.jsonl")
    return [lead for lead in leads if lead.visible["use_case"] == "gold_applicant"]


def test_sample_has_uc2_leads():
    # Sanity check that this test is exercising something real.
    assert len(_uc2_sample_leads()) >= 5


def test_uc2_prompt_has_no_unresolved_variables_for_sample_leads():
    for lead in _uc2_sample_leads():
        rendered = render("gold_applicant", dynamic_variables(lead))
        match = UNRESOLVED_VAR_RE.search(rendered)
        assert match is None, (
            f"unresolved variable {match.group() if match else ''} in prompt "
            f"for {lead.visible['lead_id']}"
        )


def test_uc2_prompt_never_leaks_truth_for_sample_leads():
    for lead in _uc2_sample_leads():
        rendered = render("gold_applicant", dynamic_variables(lead))
        for field in ("grams", "persona", "true_blocker", "eligible_amount"):
            value = lead.truth.get(field)
            if value in (None, "", 0, False):
                continue
            assert str(value) not in rendered, (
                f"truth field {field}={value!r} leaked into the rendered "
                f"prompt for {lead.visible['lead_id']}"
            )


def test_uc2_prompt_word_budget():
    text = render_static("gold_applicant")
    word_count = len(text.split())
    assert word_count < 1550, f"UC2 prompt is {word_count} words, over the ~1500 budget"
