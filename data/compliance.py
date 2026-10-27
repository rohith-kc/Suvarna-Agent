"""Compliance gate (CLAUDE.md Part 5.3, Part 2 rule 1).

A DND lead is never called, in simulation or otherwise. A UC1 lead without
recorded consent is never called either.
"""


def is_callable(lead):
    visible = lead.visible
    if visible.get("dnd_flag"):
        return False
    if visible.get("use_case") == "loan_seeker" and not visible.get("consent_status"):
        return False
    return True
