# Test card: scenario-uc1_cooperative_fits_ad

**Scenario:** Cooperative loan seeker from an ad, gold comfortably covers the need (`uc1_cooperative_fits_ad`)

## Dynamic variables to paste

```
customer_name: Rajesh
agent_name: Asha
lender_name: Suvarna Gold Finance
use_case: loan_seeker
call_trigger: app_download
trigger_detail: saw an ad for quick personal loans online
opening_line: I saw that you saw an ad for quick personal loans online.
last_step_completed: 
minutes_since_stop: None
city: Bengaluru
preferred_language: Hindi
branch_name: our Bengaluru branch
```

## CRM record the agent can look up (get_customer_context)

```json
{
  "customer": {
    "lead_id": "scenario-uc1_cooperative_fits_ad",
    "name": "Rajesh",
    "city": "Bengaluru",
    "preferred_language": "Hindi",
    "consent_status": "opted_in_form",
    "dnd_flag": false
  },
  "enquiries": [
    {
      "lead_id": "scenario-uc1_cooperative_fits_ad",
      "source": "ad",
      "trigger_detail": "saw an ad for quick personal loans online",
      "stated_loan_amount": "100000",
      "enquired_at": "2025-12-30T12:00:00+00:00"
    }
  ]
}
```

## Customer role-play script

- **Persona:** cooperative
- **Gold:** 30 g, stones: False, karat: 22
- **Say these in order, in your own words:**
  1. Yes, speaking.
  2. I need around one lakh for some personal expenses.
  3. Sure, I'd like to hear about it.
  4. About 30 grams, no stones.
  5. Yes, let's book an appraisal.

## Expected outcome and pass checklist

- **Expected outcome:** `appraisal_booked`
- [ ] Identity confirmed before any loan detail
- [ ] Said it is an AI assistant
- [ ] Every number came from a tool, never invented
- [ ] Reached the expected outcome above
- [ ] Did NOT: mentions gold before asking permission to bring it up
