"""Tests for simulation/llm.py's provider fallback (CLAUDE.md Part 5.5).

These never touch the network: _PROVIDERS entries are monkeypatched with
fake functions so the retry/fallback logic can be tested deterministically
and fast.
"""

import requests

from simulation import llm
from simulation.config import Config


def _http_error(status):
    response = requests.Response()
    response.status_code = status
    return requests.HTTPError(response=response)


def _reset_module_state():
    llm._PROVIDER_DOWN.clear()
    llm._rate_limiters.clear()


def _config(provider="gemini", fallback_provider="", **overrides):
    base = Config(
        provider=provider,
        model_agent="primary-model",
        model_customer="primary-model",
        model_judge="primary-model",
        max_requests_per_minute=1000,
        max_requests_per_day=1000,
        fallback_provider=fallback_provider,
        fallback_model_agent="fallback-model",
        fallback_model_customer="fallback-model",
        fallback_model_judge="fallback-model",
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_no_fallback_configured_raises_after_retries(monkeypatch):
    _reset_module_state()
    monkeypatch.setattr(llm.time, "sleep", lambda _: None)
    calls = []

    def always_fails(config, role, messages):
        calls.append(config.provider)
        raise _http_error(429)

    monkeypatch.setitem(llm._PROVIDERS, "gemini", always_fails)

    config = _config(provider="gemini", fallback_provider="")
    try:
        llm.complete("agent", [], config=config, max_retries=3)
        assert False, "expected an HTTPError"
    except requests.HTTPError:
        pass
    assert calls == ["gemini", "gemini", "gemini"]


def test_falls_back_after_primary_exhausts_retries(monkeypatch):
    _reset_module_state()
    monkeypatch.setattr(llm.time, "sleep", lambda _: None)
    primary_calls = []
    fallback_calls = []

    def primary_fails(config, role, messages):
        primary_calls.append(config.model_agent)
        raise _http_error(429)

    def fallback_succeeds(config, role, messages):
        fallback_calls.append(config.model_agent)
        return "ok from fallback"

    monkeypatch.setitem(llm._PROVIDERS, "gemini", primary_fails)
    monkeypatch.setitem(llm._PROVIDERS, "groq", fallback_succeeds)

    config = _config(provider="gemini", fallback_provider="groq")
    result = llm.complete("agent", [], config=config, max_retries=2)

    assert result == "ok from fallback"
    assert primary_calls == ["primary-model", "primary-model"]
    assert fallback_calls == ["fallback-model"]


def test_provider_marked_down_skips_straight_to_fallback_next_time(monkeypatch):
    _reset_module_state()
    monkeypatch.setattr(llm.time, "sleep", lambda _: None)
    primary_calls = []
    fallback_calls = []

    def primary_fails(config, role, messages):
        primary_calls.append(1)
        raise _http_error(429)

    def fallback_succeeds(config, role, messages):
        fallback_calls.append(1)
        return "ok"

    monkeypatch.setitem(llm._PROVIDERS, "gemini", primary_fails)
    monkeypatch.setitem(llm._PROVIDERS, "groq", fallback_succeeds)

    config = _config(provider="gemini", fallback_provider="groq")
    llm.complete("agent", [], config=config, max_retries=2)
    assert len(primary_calls) == 2

    # Second call: primary is already known-down, should not be retried at all.
    llm.complete("customer", [], config=config, max_retries=2)
    assert len(primary_calls) == 2
    assert len(fallback_calls) == 2


def test_non_retryable_status_does_not_retry_but_still_falls_back(monkeypatch):
    _reset_module_state()
    monkeypatch.setattr(llm.time, "sleep", lambda _: None)
    primary_calls = []

    def primary_fails_auth(config, role, messages):
        primary_calls.append(1)
        raise _http_error(401)

    def fallback_succeeds(config, role, messages):
        return "ok"

    monkeypatch.setitem(llm._PROVIDERS, "gemini", primary_fails_auth)
    monkeypatch.setitem(llm._PROVIDERS, "groq", fallback_succeeds)

    config = _config(provider="gemini", fallback_provider="groq")
    result = llm.complete("agent", [], config=config, max_retries=5)

    assert result == "ok"
    assert len(primary_calls) == 1  # 401 isn't retryable - one attempt, then fall back
