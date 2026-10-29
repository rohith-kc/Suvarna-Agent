# Test card: scenario-uc2_busy

**Scenario:** Busy applicant, driving (`uc2_busy`)

## Dynamic variables to paste

```
customer_name: Sanjay
agent_name: Asha
lender_name: Suvarna Gold Finance
use_case: gold_applicant
call_trigger: gold_loan_application
trigger_detail: 
opening_line: You started the KYC step for a gold loan with us, and I wanted to see if I can help you finish.
last_step_completed: kyc_started
minutes_since_stop: 15
city: Bengaluru
preferred_language: Kannada
branch_name: our Bengaluru branch
```

## CRM record the agent can look up (get_customer_context)

```json
{
  "customer": {
    "lead_id": "scenario-uc2_busy",
    "name": "Sanjay",
    "city": "Bengaluru",
    "preferred_language": "Kannada",
    "consent_status": "applicant",
    "dnd_flag": false
  },
  "applications": [
    {
      "lead_id": "scenario-uc2_busy",
      "product": "gold loan",
      "last_step_completed": "kyc_started",
      "amount_entered": "50000",
      "started_at": "2026-01-01T09:39:00+00:00",
      "stopped_at": "2026-01-01T11:45:00+00:00",
      "device": "app"
    }
  ]
}
```

## Customer role-play script

- **Persona:** busy
- **True blocker (reveal only once asked a specific question):** unsure_amount
- **Gold:** 28.5 g, stones: False, karat: 22
- **Say these in order, in your own words:**
  1. Yes but I'm driving right now, can you call later?
  2. Evening is better.

## Expected outcome and pass checklist

- **Expected outcome:** `callback_scheduled`
- [ ] Identity confirmed before any loan detail
- [ ] Said it is an AI assistant
- [ ] Every number came from a tool, never invented
- [ ] Reached the expected outcome above
- [ ] Did NOT: keeps pitching after 'I'm driving, call later'
