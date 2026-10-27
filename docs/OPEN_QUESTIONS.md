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
