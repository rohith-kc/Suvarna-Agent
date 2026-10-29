"""Tools webhook server (CLAUDE.md Part 5.2).

FastAPI endpoints the voice platform (or the simulation, which calls the
underlying Python functions directly instead) uses as tools. Every call is
appended to events.jsonl. All endpoints are protected by the X-Tool-Secret
header, except that the check is skipped (with a logged warning) when
TOOL_SECRET is unset, e.g. in local dev.

book_appraisal's doorstep refusal is a PLACEHOLDER: doorstep availability is
a lender fact not yet confirmed (docs/OPEN_QUESTIONS.md item 3).
get_customer_context reads data/crm.sqlite (CLAUDE.md Part 5.3a), built by
data/build_crm.py; it returns a clear error if that file doesn't exist yet.
"""

import itertools
import json
import logging
import os
import time

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from data.build_crm import read_customer_context
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


@app.get("/demo")
def demo_page():
    """A public, no-login page (Phase 9 demo pack) where anyone with the
    link can pick a named scenario and actually talk (voice or text) to
    the UC2 agent - real microphone access needs a real page origin, which
    an embedded Artifact can't give it, so this is served from here
    instead. See scripts/talk_to_agent.html."""
    return FileResponse("scripts/talk_to_agent.html")


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
    db_path = os.environ.get("CRM_DB_PATH", "data/crm.sqlite")
    context = read_customer_context(req.lead_id, db_path)
    if context is None:
        result = {
            "ok": False,
            "error": "lead_id not found in CRM, or CRM not built yet "
                     "(run data/build_crm.py)",
        }
    else:
        result = {"ok": True, **context}
    log_event("get_customer_context", req.model_dump(), result)
    return result
