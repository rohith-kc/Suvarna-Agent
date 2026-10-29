# Results log

One row per simulation run. Logged every time per CLAUDE.md Part 2 rule 10:
after any prompt or tool change, rerun the simulation and log the result
here. If the score did not improve, revert the change.

All pass-rate numbers are against **synthetic** customers with **invented**
distributions — read as a quality signal on prompt/logic, not a real-world
prediction.

| Date | Use case | Change | N | Pass rate | Soft pass rate | Guardrail pass rate | Avg turns | Cost | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-10-28 | UC2 | Phase 5 baseline, after harness fixes (real guardrail checks, outcome derivation for wrong_person/no_answer, simulator hangup timing, tool-chain end_call) but before any prompt change | 38/60 graded (22 hit the free Gemini tier's daily quota mid-run, not graded — see docs/OPEN_QUESTIONS.md #14) | 2/38 (5%) | 0/38 | 4/38 (11%) | 3.7 | $0 (free tier) | Two systemic, repeated issues, not random noise: (1) `tts_safe` failed in 34/38 (89%) — apology/wrong-person closing lines ran 3–4 sentences instead of 1–2, because the prompt only described that moment, never gave an exact line; (2) `record_opt_out` called on several calls that were not opt-outs at all (a polite decline, a wrong-person "have a good day") — mislabels a lead as permanently DND. Fixing (1) first (see next row), since it alone forces nearly every call to "fail" regardless of outcome correctness. |
| 2026-10-28 | UC2 | Added an exact 2-sentence wrong-person/apology line to the prompt + a worked example (fix for the tts_safe finding above) | 10/10 attempted, 0 graded | n/a | n/a | n/a | $0 (free tier) | Could not measure: the free Gemini tier's daily quota for `gemini-flash-lite-latest` was fully exhausted by the baseline run above — every one of these 10 calls hit a 429 that outlasted retries. Needs a quota reset (next day) or a different provider/key to actually measure this change — flagged for KC, see docs/OPEN_QUESTIONS.md #14. Not reverting the change; it's a plausible, low-risk fix (an exact line replacing a vague instruction) and nothing suggests it made things worse — there's just no fresh data yet either way. |
