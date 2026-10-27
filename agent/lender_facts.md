<!--
Lender facts: Suvarna Gold Finance (a FICTIONAL demo lender).
EVERY fact below is a PLACEHOLDER invented for this demo. Replace with real
lender policy before this is ever used with a real lender. See
docs/OPEN_QUESTIONS.md items 2 and 3 for what is still unconfirmed with KC.

This file is injected verbatim into the "Lender facts" section of each
use-case prompt at the {{lender_facts}} marker (agent/prompt.py).
-->

Suvarna Gold Finance facts (all placeholders, label them as such if asked):

Branch hours: Monday to Saturday, 10am to 6pm. Closed Sundays and public
holidays.

Documents to bring: a government photo ID (Aadhaar, PAN, voter ID, or
passport), one address proof if different from the ID, and the gold
jewellery itself for appraisal. Nothing else is required for a
straightforward application.

How jewellery is handled: at the branch, it is weighed and tested in front
of the customer, sealed into a tamper-evident pouch with the customer's
signature across the seal, and stored in the branch vault. On full
repayment, the same sealed pouch is opened and returned in person, and the
customer checks and signs again.

Doorstep appraisal: not offered. Every appraisal happens at a branch.
(PLACEHOLDER pending KC's answer to docs/OPEN_QUESTIONS.md item 3 — if this
changes, update this file and tools/server.py's DOORSTEP_AVAILABLE flag
together.)

Rate card: interest rate is 12 percent per annum, simple interest, matching
tools/eligibility.py's default. No processing fee and no prepayment penalty
for a standard loan (PLACEHOLDER — unconfirmed). Only ever state figures
from this rate card. If asked about a rate or fee not listed here, do not
guess — offer a human callback.

WhatsApp checklist wording (used with send_whatsapp_summary): a short
message naming the ID needed, the gold to bring, roughly how long the
branch visit takes, and the eligibility range from calculate_eligibility.
