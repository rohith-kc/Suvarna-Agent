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

13. **RESOLVED (2026-10-28).** CLAUDE.md Part 5.3's `expected_outcome`
   rules gave UC1 a `not_a_fit` exception when `amount_needed` is far
   above `eligible_amount`, but UC2 had no equivalent. Seen live in
   HUMAN GATE 4's real test call (lead `gold_applicant-0014`: needed
   400,000, eligible for ~225,000): the agent sensibly pivoted to a
   WhatsApp summary instead of forcing a booking, but the harness scored
   it `fail` since `expected_outcome` said `appraisal_booked` regardless.
   KC's decision: add the exception to UC2 too, but land on
   `whatsapp_sent` rather than `not_a_fit` — unlike UC1, this customer
   already owns gold and already started an application, so the honest
   outcome is still to keep them as a lead via WhatsApp, not end the
   relationship. Implemented in `compute_expected_outcome()`
   (`data/generate_leads.py`): when `eligible_amount > 0` and
   `amount_needed > 1.15 * eligible_amount`, UC2 now expects
   `whatsapp_sent`.

14. The free Gemini tier's actual daily quota for `gemini-flash-lite-latest`
   is lower than our own `MAX_REQUESTS_PER_DAY` safety cap (set to 5000 for
   this run) and ran out partway through the very first Phase 5 baseline
   run (60 calls): 22 of 60 calls hit a sustained 429 that outlasted
   `simulation/llm.py`'s retries (6 attempts, up to 30s backoff), and a
   follow-up 10-call run later the same day failed 10/10 immediately.
   AI Studio's quota page (https://aistudio.google.com/rate-limit) is the
   only place the real number is shown per Part 0 rule 5, and I can't open
   KC's account. Rough budget observed: about 40-50 real calls/day before
   it runs out. **(ask Karta — check the real number in AI Studio; decide
   whether to wait for the daily reset, add a GROQ_API_KEY as a second
   free-tier provider, or move to a paid key, before continuing Phase 5's
   baseline runs)**

   **Update (2026-10-29):** added the `GROQ_API_KEY` fallback
   (`LLM_FALLBACK_PROVIDER=groq` in `simulation/llm.py`/`config.py`) as
   suggested above. It worked - calls that hit a dead Gemini now complete
   on Groq instead of erroring - but by the end of today's testing (two
   60-call runs plus smaller ones) both Gemini's and Groq's free-tier daily
   quotas were genuinely exhausted (real 429s from both providers' own
   servers, not our own `MAX_REQUESTS_PER_DAY` cap, which was a separate,
   now-fixed bug - see `docs/RESULTS.md`, 2026-10-29). A clean 3-run
   evidence set (CLAUDE.md Part 5.6) needs either tomorrow's quota reset
   spread across more than one day, or a paid key. **(ask Karta)**

   **Update (2026-10-30):** two things now confirmed with hard numbers,
   not guesses. (1) Gemini's free tier is **500 requests/day**, and it
   resets on a *Pacific-time* clock (midnight PT = 07:00 UTC), not local
   midnight - it was still showing yesterday's exhaustion for the first
   ~40 minutes of today's testing. (2) Groq's real limit for
   `openai/gpt-oss-120b` is **200,000 tokens/day (TPD)**, not a request
   count - a single 60-call run needs roughly 700k-900k tokens (the
   ~2,000-token UC2 prompt is resent on every agent turn, which these
   stateless chat-completion APIs require), 3-4x Groq's entire daily
   budget by itself. Groq was only ever sized for the "10-20 call spot
   check" tier CLAUDE.md's own provider table already said it was for -
   using it as an automatic fallback for full 60-call baselines was my
   mistake; it can't carry one on its own. One clean 60-call run today
   used essentially all of Gemini's 500/day budget in a single shot.
   **Bottom line: 3 consecutive clean 60-call runs in one calendar day
   is not achievable on free tiers as currently used - it needs either
   several days, a smaller per-run N, or a paid key.** **(ask Karta)**

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
