"""STUB — Phase 0 scaffold only.

Built in Phase 1 (CLAUDE.md Part 5.2): FastAPI webhook tools server
(calculate_eligibility, book_appraisal, send_whatsapp_summary,
schedule_callback, record_opt_out, get_customer_context, health),
protected by X-Tool-Secret, logging every call to events.jsonl.
"""

from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health():
    return {"ok": True}
