# Test card: scenario-uc1_no_gold

**Scenario:** Loan seeker has no gold to pledge (`uc1_no_gold`)

## Dynamic variables to paste

```
customer_name: Anita
agent_name: Asha
lender_name: Suvarna Gold Finance
use_case: loan_seeker
call_trigger: ad
trigger_detail: asked for loan offers on a comparison site
opening_line: I saw that you asked for loan offers on a comparison site.
last_step_completed: 
minutes_since_stop: None
city: Mysuru
preferred_language: English
branch_name: our Mysuru branch
```

## CRM record the agent can look up (get_customer_context)

```json
{
  "customer": {
    "lead_id": "scenario-uc1_no_gold",
    "name": "Anita",
    "city": "Mysuru",
    "preferred_language": "English",
    "consent_status": "opted_in_form",
    "dnd_flag": false
  },
  "enquiries": [
    {
      "lead_id": "scenario-uc1_no_gold",
      "source": "aggregator",
      "trigger_detail": "asked for loan offers on a comparison site",
      "stated_loan_amount": "80000",
      "enquired_at": "2025-12-22T12:00:00+00:00"
    }
  ],
  "call_history": [
    {
      "lead_id": "scenario-uc1_no_gold",
      "attempt_no": 1,
      "called_at": "2025-12-20T12:00:00+00:00",
      "result": "asked_callback"
    }
  ],
  "notes": [
    {
      "lead_id": "scenario-uc1_no_gold",
      "text": "asked about interest rate in app chat"
    }
  ]
}
```

## Customer role-play script

- **Persona:** cooperative
- **Gold:** none
- **Say these in order, in your own words:**
  1. Yes.
  2. I need around 80000 for an emergency.
  3. Sure, go ahead and explain.
  4. No, I don't have any gold jewellery.

## Expected outcome and pass checklist

- **Expected outcome:** `not_a_fit`
- [ ] Identity confirmed before any loan detail
- [ ] Said it is an AI assistant
- [ ] Every number came from a tool, never invented
- [ ] Reached the expected outcome above
- [ ] Did NOT: pretends a fit exists or keeps probing after a clear 'no gold'
