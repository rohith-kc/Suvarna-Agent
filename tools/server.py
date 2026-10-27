"""Tools webhook server (CLAUDE.md Part 5.2).

FastAPI endpoints the voice platform (or the simulation, which calls the
underlying Python functions directly instead) uses as tools. Every call is
appended to events.jsonl. All endpoints are protected by the X-Tool-Secret
header, except that the check is skipped (with a logged warning) when
TOOL_SECRET is unset, e.g. in local dev.

book_appraisal's doorstep refusal and get_customer_context's "not available"
response are PLACEHOLDERS: doorstep availability is a lender fact not yet
confirmed (docs/OPEN_QUESTIONS.md item 3), and the fake CRM get_customer_context
reads from is built in Phase 2 (CLAUDE.md Part 5.3a).
"""

import itertools
import json
import logging
import os
import time

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from tools.eligibility import calculate_eligibility

logger = logging.getLogger("tools.server")

app = FastAPI()

EVENTS_LOG_PATH = "events.jsonl"

# PLACEHOLDER: no doorstep appraisal until KC confirms (docs/OPEN_QUESTIONS.md #3).
DOORSTEP_AVAILABLE = False

OPT_OUTS = []
SCHEDULED_CALLBACKS = []
SENT_WHATSAPP_MESSAGES = []

_appraisal_ids = itertools.count(1)


def log_event(tool, arguments, result):
    event = {
        "timestamp": time.time(),
        "tool": tool,
        "arguments": arguments,
        "result": result,
    }
    with open(EVENTS_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def verify_tool_secret(x_tool_secret: str = Header(default=None)):
    secret = os.environ.get("TOOL_SECRET")
    if not secret:
        logger.warning("TOOL_SECRET is not set; tools server is running without auth.")
        return
    if x_tool_secret != secret:
        raise HTTPException(status_code=401, detail="invalid or missing X-Tool-Secret")


@app.get("/health")
def health():
    return {"ok": True}


class EligibilityRequest(BaseModel):
    grams: float
    karat: int = 22
    repayment_type: str = "monthly"
    has_stones: bool = False
    existing_loan: float = 0
    unit: str = "gram"


@app.post("/calculate_eligibility", dependencies=[Depends(verify_tool_secret)])
def calculate_eligibility_endpoint(req: EligibilityRequest):
    result = calculate_eligibility(
        grams=req.grams,
        karat=req.karat,
        repayment_type=req.repayment_type,
        has_stones=req.has_stones,
        existing_loan=req.existing_loan,
        unit=req.unit,
    )
    log_event("calculate_eligibility", req.model_dump(), result)
    return result


class BookAppraisalRequest(BaseModel):
    customer_name: str
    mode: str  # "branch" or "doorstep"
    slot: str


@app.post("/book_appraisal", dependencies=[Depends(verify_tool_secret)])
def book_appraisal_endpoint(req: BookAppraisalRequest):
    if req.mode not in ("branch", "doorstep"):
        result = {"ok": False, "error": "mode must be 'branch' or 'doorstep'"}
    elif req.mode == "doorstep" and not DOORSTEP_AVAILABLE:
        result = {"ok": False, "error": "doorstep appraisal is not offered"}
    else:
        result = {
            "ok": True,
            "confirmation_id": f"APPT-{next(_appraisal_ids):06d}",
            "mode": req.mode,
            "slot": req.slot,
        }
    log_event("book_appraisal", req.model_dump(), result)
    return result


class WhatsappRequest(BaseModel):
    customer_name: str
    summary: str


@app.post("/send_whatsapp_summary", dependencies=[Depends(verify_tool_secret)])
def send_whatsapp_summary_endpoint(req: WhatsappRequest):
    SENT_WHATSAPP_MESSAGES.append(req.model_dump())
    result = {"ok": True}
    log_event("send_whatsapp_summary", req.model_dump(), result)
    return result


class CallbackRequest(BaseModel):
    customer_name: str
    when: str
    reason: str


@app.post("/schedule_callback", dependencies=[Depends(verify_tool_secret)])
def schedule_callback_endpoint(req: CallbackRequest):
    SCHEDULED_CALLBACKS.append(req.model_dump())
    result = {"ok": True}
    log_event("schedule_callback", req.model_dump(), result)
    return result


class OptOutRequest(BaseModel):
    customer_name: str
    reason: str


@app.post("/record_opt_out", dependencies=[Depends(verify_tool_secret)])
def record_opt_out_endpoint(req: OptOutRequest):
    OPT_OUTS.append(req.model_dump())
    result = {"ok": True}
    log_event("record_opt_out", req.model_dump(), result)
    return result


class CustomerContextRequest(BaseModel):
    lead_id: str


@app.post("/get_customer_context", dependencies=[Depends(verify_tool_secret)])
def get_customer_context_endpoint(req: CustomerContextRequest):
    # Phase 2 (CLAUDE.md Part 5.3a) builds data/crm.sqlite and wires this up
    # for real, reading visible fields only, never truth fields.
    result = {
        "ok": False,
        "error": "customer CRM is not built yet (CLAUDE.md Phase 2 / Part 5.3a)",
    }
    log_event("get_customer_context", req.model_dump(), result)
    return result
