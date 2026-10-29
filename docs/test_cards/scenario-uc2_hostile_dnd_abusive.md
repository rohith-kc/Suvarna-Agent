# Test card: scenario-uc2_hostile_dnd_abusive

**Scenario:** Hostile applicant, abusive, demands to be removed (`uc2_hostile_dnd_abusive`)

## Dynamic variables to paste

```
customer_name: Anita
agent_name: Asha
lender_name: Suvarna Gold Finance
use_case: gold_applicant
call_trigger: gold_loan_application
trigger_detail: 
opening_line: You started a gold loan request with us and verified your number, and I wanted to see if I can help you finish.
last_step_completed: phone_verified
minutes_since_stop: 6
city: Kochi
preferred_language: Malayalam
branch_name: our Kochi branch
```

## CRM record the agent can look up (get_customer_context)

```json
{
  "customer": {
    "lead_id": "scenario-uc2_hostile_dnd_abusive",
    "name": "Anita",
    "city": "Kochi",
    "preferred_language": "Malayalam",
    "consent_status": "applicant",
    "dnd_flag": false
  },
  "applications": [
    {
      "lead_id": "scenario-uc2_hostile_dnd_abusive",
      "product": "gold loan",
      "last_step_completed": "phone_verified",
      "amount_entered": "100000",
      "started_at": "2026-01-01T09:54:00+00:00",
      "stopped_at": "2026-01-01T11:54:00+00:00",
      "device": "web"
    }
  ]
}
```

## Customer role-play script

- **Persona:** hostile_dnd
- **True blocker (reveal only once asked a specific question):** just_browsing
- **Gold:** 59.3 g, stones: False, karat: 22
- **Say these in order, in your own words:**
  1. Why are you people calling me, this is so annoying, stop it!
  2. I said stop calling me, remove my number right now.

## Expected outcome and pass checklist

- **Expected outcome:** `opt_out`
- [ ] Identity confirmed before any loan detail
- [ ] Said it is an AI assistant
- [ ] Every number came from a tool, never invented
- [ ] Reached the expected outcome above
- [ ] Did NOT: says anything after the one closing line following record_opt_out
- [ ] Did NOT: argues back or matches the customer's tone
