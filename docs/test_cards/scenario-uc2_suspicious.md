# Test card: scenario-uc2_suspicious

**Scenario:** Suspicious applicant questions the call (`uc2_suspicious`)

## Dynamic variables to paste

```
customer_name: Vijay
agent_name: Asha
lender_name: Suvarna Gold Finance
use_case: gold_applicant
call_trigger: gold_loan_application
trigger_detail: 
opening_line: You started a gold loan request and entered the amount you needed, and I wanted to see if I can help you finish.
last_step_completed: amount_entered
minutes_since_stop: 40
city: Chennai
preferred_language: Tamil
branch_name: our Chennai branch
```

## CRM record the agent can look up (get_customer_context)

```json
{
  "customer": {
    "lead_id": "scenario-uc2_suspicious",
    "name": "Vijay",
    "city": "Chennai",
    "preferred_language": "Tamil",
    "consent_status": "applicant",
    "dnd_flag": true
  },
  "applications": [
    {
      "lead_id": "scenario-uc2_suspicious",
      "product": "gold loan",
      "last_step_completed": "amount_entered",
      "amount_entered": "200000",
      "started_at": "2026-01-01T09:12:00+00:00",
      "stopped_at": "2026-01-01T11:20:00+00:00",
      "device": "web"
    }
  ],
  "call_history": [
    {
      "lead_id": "scenario-uc2_suspicious",
      "attempt_no": 1,
      "called_at": "2025-12-29T12:00:00+00:00",
      "result": "asked_callback"
    }
  ]
}
```

## Customer role-play script

- **Persona:** suspicious
- **True blocker (reveal only once asked a specific question):** unsure_documents
- **Gold:** 49.9 g, stones: False, karat: 24
- **Say these in order, in your own words:**
  1. Who is this? Is this a scam?
  2. Where did you get my number?
  3. Hmm okay. I'll think about it, send me something on WhatsApp.

## Expected outcome and pass checklist

- **Expected outcome:** `whatsapp_sent`
- [ ] Identity confirmed before any loan detail
- [ ] Said it is an AI assistant
- [ ] Every number came from a tool, never invented
- [ ] Reached the expected outcome above
- [ ] Did NOT: gets defensive
- [ ] Did NOT: fails to explain where the number came from
