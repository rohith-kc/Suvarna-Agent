# Open questions

Seeded from CLAUDE.md Part 8. Add to this list whenever a task reveals
something the brief got wrong or doesn't know — don't guess, ask KC.

1. Does the lender sell anything besides gold loans? If not, most UC1 calls
   end `not_a_fit` and UC1 is mostly a qualification call. **(ask Karta)**
2. What does the lender record about where each applicant stopped, and how
   soon can the agent see it? Decides whether UC2 can name the exact step.
   **(ask Karta)**
3. Does the lender offer doorstep appraisal? Removes the biggest practical
   blocker if so. **(ask Karta)**
4. Which number series and consent rules apply to each use case? Treated as
   promotional until confirmed. **(ask counsel)**
5. Which metric does Karta's customer pay on: bookings, disbursals or
   contacts? **(ask Karta)**
6. What voice stack does Karta use today? If it is not ElevenLabs, only the
   platform layer changes. **(ask Karta)**
7. Show-up after booking is the real result and needs the lender's branch
   data. **(unknown)**
8. Whether Sarvam's free credits cover voice agents. **(check Sarvam docs)**

## Found during build

9. CLAUDE.md Part 4.1's repository tree lists `simulation/` without an
   `llm.py` or `config.py`, but Part 5.5 instructs building
   `simulation/llm.py` (the provider layer, `complete(role, messages,
   json_schema=None)`) and says "Config in `simulation/config.py` reads
   env." Phase 0 scaffolds only the files literally in the 4.1 tree;
   `llm.py` and `config.py` will need to be added in Phase 4 to follow 5.5.
   **(ask Karta — confirm it's fine to add these two files in Phase 4 even
   though they're not in the Part 4.1 tree)**

10. Added `agent/prompt.py` in Phase 3, also not in the Part 4.1 tree.
   Part 5.4 says to "inject `agent/lender_facts.md`" into each prompt at a
   `{{lender_facts}}` marker, and Phase 3's done-when criteria needs a test
   that renders the prompt with dynamic variables resolved — both need a
   small renderer to exist somewhere. `agent/prompt.py` resolves
   `{{lender_facts}}` (identical every call) and then the per-call dynamic
   variables from `data/loader.py`'s `dynamic_variables()`. Phase 4's
   `simulation/agent_runner.py` should import and reuse this rather than
   re-implementing the same logic. **(ask Karta — confirm this is fine; no
   action needed otherwise)**

11. Phase 4's cost guard (`run_simulation.py`, Part 5.5: "print an estimate
   before any run over 20 calls... using token counts") is only a
   call-count gate (>20 calls needs `--yes`), not a real token-based $
   estimate. A true estimate needs the provider's current per-token price,
   which Part 0 rule 5 says to verify in the provider's own docs rather
   than hardcode from memory. KC picked the free Gemini tier (HUMAN GATE
   4), so cost is $0 for now, but this should be revisited with a real
   estimate before switching to any paid provider. `MAX_SIM_COST_USD` is
   read into `simulation/config.py` but not yet enforced. **(ask Karta —
   fine to leave as-is while on the free tier; revisit before paid use)**

13. CLAUDE.md Part 5.3's `expected_outcome` rules give UC1 a `not_a_fit`
   exception when `amount_needed` is far above `eligible_amount`, but
   UC2's rules have no equivalent — a cooperative UC2 lead whose
   `amount_needed` vastly exceeds what their gold supports still expects
   `appraisal_booked`. Seen live in HUMAN GATE 4's real test call
   (lead `gold_applicant-0014`: needed 400,000, eligible for ~225,000):
   the agent sensibly pivoted to a WhatsApp summary instead of forcing a
   booking, which is arguably the *better* behaviour — but the harness
   scored it `fail` since `expected_outcome` says `appraisal_booked`
   regardless. This looks like a genuine gap in the spec's UC2 rule, not
   a bug in `compute_expected_outcome()` (which matches Part 5.3 exactly).
   **(ask Karta — should UC2 get a UC1-style amount-mismatch exception
   too? Not changed without a decision, since it affects what counts as
   a pass)**

12. Gemini's free-tier model names moved on from `gemini-2.5-flash`
   (404s: "no longer available to new users, use gemini-3.8-flash") to a
   `-latest`/`-lite-latest` alias scheme. `gemini-flash-latest` also hit a
   503 ("high demand") during HUMAN GATE 4's real test call; the working
   model as of 2026-10-28 was `gemini-flash-lite-latest`. `simulation/llm.py`
   now retries on 429/500/502/503/504 and timeouts, but if these aliases
   shift again, re-check aistudio.google.com's own quickstart snippet
   (the most reliable source — it showed the exact working model name and
   current key format when docs search gave conflicting answers).
   **(informational — no action needed unless models 404/503 again)**
