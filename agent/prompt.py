"""Renders a use-case system prompt (CLAUDE.md Part 5.4).

Not in the original Part 4.1 repository tree — added because both Phase 3's
rendering test and Phase 4's simulation/agent_runner.py need the same
"resolve {{lender_facts}}, then resolve per-call dynamic variables" logic.
Flagged in docs/OPEN_QUESTIONS.md; agent_runner.py should import and reuse
this module rather than re-implementing it.

{{lender_facts}} is resolved from agent/lender_facts.md at render time (it
is the same text on every call). Everything else in {{...}} form is a
per-call dynamic variable (CLAUDE.md Part 5.3's dynamic_variables()) and is
resolved from the dict passed to render().
"""

import os
import re

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)

_TEMPLATES = {
    "gold_applicant": "uc2_applicant_prompt.md",
    "loan_seeker": "uc1_seeker_prompt.md",
}


def _read(filename):
    with open(os.path.join(AGENT_DIR, filename), "r", encoding="utf-8") as f:
        return f.read()


def load_template(use_case):
    return _read(_TEMPLATES[use_case])


def _strip_dev_comments(text):
    """Strip <!-- --> dev comments — they're for repo maintainers, never
    for the model, and one happens to mention the literal {{lender_facts}}
    marker in prose, which would otherwise look unresolved."""
    return _HTML_COMMENT_RE.sub("", text).strip()


def render_static(use_case):
    """Resolve {{lender_facts}} only — identical for every call of this use case."""
    template = _strip_dev_comments(load_template(use_case))
    lender_facts = _strip_dev_comments(_read("lender_facts.md"))
    return template.replace("{{lender_facts}}", lender_facts)


def render(use_case, dynamic_variables):
    """Resolve lender facts, then the per-call dynamic variables."""
    text = render_static(use_case)
    for key, value in dynamic_variables.items():
        text = text.replace("{{" + key + "}}", "" if value is None else str(value))
    return text
