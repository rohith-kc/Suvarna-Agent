# Test card: scenario-uc2_cooperative_unsure_amount_hindi_switch

**Scenario:** Cooperative applicant unsure of amount, switches to Hindi mid-call (`uc2_cooperative_unsure_amount_hindi_switch`)

## Dynamic variables to paste

```
customer_name: Rohit
agent_name: Asha
lender_name: Suvarna Gold Finance
use_case: gold_applicant
call_trigger: gold_loan_application
trigger_detail: 
opening_line: You started the KYC step for a gold loan with us, and I wanted to see if I can help you finish.
last_step_completed: kyc_started
minutes_since_stop: 40
city: Jaipur
preferred_language: Hindi
branch_name: our Jaipur branch
```

## CRM record the agent can look up (get_customer_context)

```json
{
  "customer": {
    "lead_id": "scenario-uc2_cooperative_unsure_amount_hindi_switch",
    "name": "Rohit",
    "city": "Jaipur",
    "preferred_language": "Hindi",
    "consent_status": "applicant",
    "dnd_flag": false
  },
  "applications": [
    {
      "lead_id": "scenario-uc2_cooperative_unsure_amount_hindi_switch",
      "product": "gold loan",
      "last_step_completed": "kyc_started",
      "amount_entered": "150000",
      "started_at": "2026-01-01T10:51:00+00:00",
      "stopped_at": "2026-01-01T11:20:00+00:00",
      "device": "app"
    }
  ],
  "call_history": [
    {
      "lead_id": "scenario-uc2_cooperative_unsure_amount_hindi_switch",
      "attempt_no": 1,
      "called_at": "2025-12-29T12:00:00+00:00",
      "result": "asked_callback"
    }
  ]
}
```

## Customer role-play script

- **Persona:** cooperative
- **True blocker (reveal only once asked a specific question):** unsure_amount
- **Gold:** 22 g, stones: False, karat: 22
- **Say these in order, in your own words:**
  1. Yes, speaking.
  2. Oh right, I remember. I stopped because I wasn't sure how much I'd get.
  3. [switches to Hindi] Theek hai, Hindi mein baat kar sakte hain?
  4. Haan, about 22 grams, no stones, I think it's 22 karat.
  5. Saturday morning is fine.

## Expected outcome and pass checklist

- **Expected outcome:** `appraisal_booked`
- [ ] Identity confirmed before any loan detail
- [ ] Said it is an AI assistant
- [ ] Every number came from a tool, never invented
- [ ] Reached the expected outcome above
- [ ] Did NOT: states an amount calculate_eligibility did not return
- [ ] Did NOT: keeps replying in English after being asked to switch to Hindi
