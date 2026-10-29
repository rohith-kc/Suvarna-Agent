# Suvarna Gold Finance — outbound voice agent demo

A demo (not production) outbound voice agent for a **fictional** gold-loan lender,
"Suvarna Gold Finance", built as a Karta AI interview exhibit. See [CLAUDE.md](CLAUDE.md)
for the full brief, rules and build sequence.

Two use cases: a gold-loan applicant who stopped mid-application (UC2, built first),
and a generic loan seeker checked honestly for gold-loan fit (UC1). No real phone calls
are made; everything is tested via a text simulation harness and the voice platform's
own browser test tools.

## Try it

- **[Meet Asha](https://claude.ai/artifact/Seb78nfK4UBQZa1BW6MdL6)** — a one-page intro:
  what she does, eight scenarios worth trying, and a link into the live agent.
- **[Talk to her live](https://suvarna-tools-server.onrender.com/demo)** — voice or text,
  with 25 scripted scenarios (cooperative, suspicious, wrong person, an adversarial
  OTP/prompt-injection attempt, and more). Each card briefs you on what the agent
  already knows and what only you, the "customer", know, so it's not a free canvas.

**Status, honestly:** the conversation (prompts, tools, guardrails, the CRM lookup) is
real and working end-to-end against the live ElevenLabs agent above. The ~200-call
synthetic simulation report — the evidence that guardrails hold across every scenario,
not just the ones you happen to try by hand — is mid-tuning; see `docs/RESULTS.md` for
the latest logged run and `docs/OPEN_QUESTIONS.md` for what's still open.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env            # fill in later phases; not needed yet
pytest -q
python simulation/run_simulation.py --dry-run
```

See `docs/DESIGN.md`, `docs/TESTING.md` and `docs/DEMO.md` (added in later phases) for
product reasoning, the test layers, and the demo script.
