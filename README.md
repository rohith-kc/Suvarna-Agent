# Suvarna Gold Finance — outbound voice agent demo

A demo (not production) outbound voice agent for a **fictional** gold-loan lender,
"Suvarna Gold Finance", built as a Karta AI interview exhibit. See [CLAUDE.md](CLAUDE.md)
for the full brief, rules and build sequence.

Two use cases: a gold-loan applicant who stopped mid-application (UC2, built first),
and a generic loan seeker checked honestly for gold-loan fit (UC1). No real phone calls
are made; everything is tested via a text simulation harness and the voice platform's
own browser test tools.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env            # fill in later phases; not needed yet
pytest -q
python simulation/run_simulation.py --dry-run
```

See `docs/DESIGN.md`, `docs/TESTING.md` and `docs/DEMO.md` (added in later phases) for
product reasoning, the test layers, and the demo script.
