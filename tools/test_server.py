"""Tests for tools/server.py.

Calls the FastAPI endpoint functions directly (not over HTTP) so we don't
need to add an HTTP test client dependency (httpx) beyond the approved
stack (CLAUDE.md Part 2 rule 13). The real HTTP path is checked manually
with curl per Phase 1's "done when" criteria in CLAUDE.md Part 6.
"""

import json

import pytest

import tools.server as server


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch, tmp_path):
    server.OPT_OUTS.clear()
    server.SCHEDULED_CALLBACKS.clear()
    server.SENT_WHATSAPP_MESSAGES.clear()
    monkeypatch.setattr(server, "EVENTS_LOG_PATH", str(tmp_path / "events.jsonl"))
    monkeypatch.delenv("TOOL_SECRET", raising=False)


def test_health():
    assert server.health() == {"ok": True}


def test_calculate_eligibility_endpoint_delegates_to_pure_function():
    req = server.EligibilityRequest(grams=20, karat=22)
    result = server.calculate_eligibility_endpoint(req)
    assert result["ok"] is True
    assert result["high"] == 200000


def test_book_appraisal_branch_ok():
    req = server.BookAppraisalRequest(customer_name="Ramesh", mode="branch", slot="Saturday morning")
    result = server.book_appraisal_endpoint(req)
    assert result["ok"] is True
    assert "confirmation_id" in result


def test_book_appraisal_refuses_doorstep_when_not_offered():
    req = server.BookAppraisalRequest(customer_name="Ramesh", mode="doorstep", slot="Saturday morning")
    result = server.book_appraisal_endpoint(req)
    assert result["ok"] is False


def test_send_whatsapp_summary_ok():
    req = server.WhatsappRequest(customer_name="Ramesh", summary="Documents checklist")
    result = server.send_whatsapp_summary_endpoint(req)
    assert result["ok"] is True
    assert server.SENT_WHATSAPP_MESSAGES == [{"customer_name": "Ramesh", "summary": "Documents checklist"}]


def test_schedule_callback_ok():
    req = server.CallbackRequest(customer_name="Ramesh", when="tomorrow 5pm", reason="wants a human")
    result = server.schedule_callback_endpoint(req)
    assert result["ok"] is True
    assert len(server.SCHEDULED_CALLBACKS) == 1


def test_record_opt_out_ok():
    req = server.OptOutRequest(customer_name="Ramesh", reason="stop calling me")
    result = server.record_opt_out_endpoint(req)
    assert result["ok"] is True
    assert len(server.OPT_OUTS) == 1


def test_get_customer_context_missing_crm_returns_clear_error(monkeypatch, tmp_path):
    monkeypatch.setenv("CRM_DB_PATH", str(tmp_path / "does_not_exist.sqlite"))
    req = server.CustomerContextRequest(lead_id="gold_applicant-0001")
    result = server.get_customer_context_endpoint(req)
    assert result["ok"] is False


def test_get_customer_context_reads_real_crm(monkeypatch, tmp_path):
    from data.build_crm import build_crm
    from data.generate_leads import generate_leads, write_outputs

    records = generate_leads(n=4, seed=1)
    write_outputs(records, str(tmp_path))
    db_path = tmp_path / "crm.sqlite"
    build_crm(str(tmp_path / "leads.jsonl"), str(db_path))
    monkeypatch.setenv("CRM_DB_PATH", str(db_path))

    lead_id = records[0]["lead"]["lead_id"]
    req = server.CustomerContextRequest(lead_id=lead_id)
    result = server.get_customer_context_endpoint(req)
    assert result["ok"] is True
    assert result["customer"]["lead_id"] == lead_id


def test_get_customer_context_unknown_lead_id(monkeypatch, tmp_path):
    from data.build_crm import build_crm
    from data.generate_leads import generate_leads, write_outputs

    records = generate_leads(n=2, seed=1)
    write_outputs(records, str(tmp_path))
    db_path = tmp_path / "crm.sqlite"
    build_crm(str(tmp_path / "leads.jsonl"), str(db_path))
    monkeypatch.setenv("CRM_DB_PATH", str(db_path))

    req = server.CustomerContextRequest(lead_id="does-not-exist-0000")
    result = server.get_customer_context_endpoint(req)
    assert result["ok"] is False


def test_verify_tool_secret_skips_check_when_unset(monkeypatch):
    monkeypatch.delenv("TOOL_SECRET", raising=False)
    # Should not raise, regardless of header value.
    server.verify_tool_secret(x_tool_secret=None)
    server.verify_tool_secret(x_tool_secret="anything")


def test_verify_tool_secret_rejects_missing_header_when_set(monkeypatch):
    monkeypatch.setenv("TOOL_SECRET", "s3cret")
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        server.verify_tool_secret(x_tool_secret=None)


def test_verify_tool_secret_rejects_wrong_header_when_set(monkeypatch):
    monkeypatch.setenv("TOOL_SECRET", "s3cret")
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        server.verify_tool_secret(x_tool_secret="wrong")


def test_verify_tool_secret_accepts_correct_header(monkeypatch):
    monkeypatch.setenv("TOOL_SECRET", "s3cret")
    server.verify_tool_secret(x_tool_secret="s3cret")  # should not raise


def test_every_tool_endpoint_is_protected_by_the_secret_dependency():
    protected_paths = {
        "/calculate_eligibility", "/book_appraisal", "/send_whatsapp_summary",
        "/schedule_callback", "/record_opt_out", "/get_customer_context",
    }
    for route in server.app.routes:
        if getattr(route, "path", None) in protected_paths:
            dep_funcs = [d.call for d in route.dependant.dependencies]
            assert server.verify_tool_secret in dep_funcs


def test_events_are_logged_to_jsonl(tmp_path, monkeypatch):
    log_path = tmp_path / "events.jsonl"
    monkeypatch.setattr(server, "EVENTS_LOG_PATH", str(log_path))

    req = server.EligibilityRequest(grams=20, karat=22)
    server.calculate_eligibility_endpoint(req)

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["tool"] == "calculate_eligibility"
    assert "timestamp" in event
    assert event["arguments"]["grams"] == 20
    assert event["result"]["ok"] is True
