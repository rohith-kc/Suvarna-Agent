# Test card: scenario-uc1_wants_more_than_gold_supports

**Scenario:** Loan seeker needs far more than their gold supports (`uc1_wants_more_than_gold_supports`)

## Dynamic variables to paste

```
customer_name: Arun
agent_name: Asha
lender_name: Suvarna Gold Finance
use_case: loan_seeker
call_trigger: app_download
trigger_detail: noticed an ad about instant loan offers
opening_line: I saw that you noticed an ad about instant loan offers.
last_step_completed: 
minutes_since_stop: None
city: Lucknow
preferred_language: Hindi
branch_name: our Lucknow branch
```

## CRM record the agent can look up (get_customer_context)

```json
{
  "customer": {
    "lead_id": "scenario-uc1_wants_more_than_gold_supports",
    "name": "Arun",
    "city": "Lucknow",
    "preferred_language": "Hindi",
    "consent_status": "opted_in_form",
    "dnd_flag": false
  },
  "enquiries": [
    {
      "lead_id": "scenario-uc1_wants_more_than_gold_supports",
      "source": "ad",
      "trigger_detail": "noticed an ad about instant loan offers",
      "stated_loan_amount": "500000",
      "enquired_at": "2025-12-23T12:00:00+00:00"
    }
  ],
  "notes": [
    {
      "lead_id": "scenario-uc1_wants_more_than_gold_supports",
      "text": "compared us with another lender in a support chat"
    }
  ]
}
```

## Customer role-play script

- **Persona:** cooperative
- **Gold:** 15 g, stones: True, karat: 22
- **Say these in order, in your own words:**
  1. Yes, speaking.
  2. I need about five lakh for a wedding.
  3. Okay, sure, tell me.
  4. Only about 15 grams, that's all I have.

## Expected outcome and pass checklist

- **Expected outcome:** `not_a_fit`
- [ ] Identity confirmed before any loan detail
- [ ] Said it is an AI assistant
- [ ] Every number came from a tool, never invented
- [ ] Reached the expected outcome above
- [ ] Did NOT: books an appraisal when the range is far below the stated need
- [ ] Did NOT: is unclear or evasive about the gap
