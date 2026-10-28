"""Thin LLM provider layer (CLAUDE.md Part 5.5): one complete() function,
dispatched by LLM_PROVIDER. Talks to providers with plain `requests`
(Part 2 rule 13) — no provider SDKs. Model names come from
LLM_MODEL_AGENT/CUSTOMER/JUDGE, never hard-coded; verify current names and
prices in each provider's docs before a real run (Part 0 rule 5).
"""

import subprocess
import time

import requests

from simulation.config import Config


class RequestBudgetExceeded(Exception):
    pass


class RateLimiter:
    """A simple per-minute + per-day budget, shared across calls in a run."""

    def __init__(self, per_minute, per_day):
        self.per_minute = per_minute
        self.per_day = per_day
        self._minute_window = []
        self._day_count = 0

    def before_request(self):
        now = time.time()
        self._minute_window = [t for t in self._minute_window if now - t < 60]
        if len(self._minute_window) >= self.per_minute:
            sleep_for = 60 - (now - self._minute_window[0])
            if sleep_for > 0:
                time.sleep(sleep_for)
        if self._day_count >= self.per_day:
            raise RequestBudgetExceeded(f"MAX_REQUESTS_PER_DAY ({self.per_day}) reached")
        self._minute_window.append(time.time())
        self._day_count += 1


def _model_for_role(config, role):
    return {
        "agent": config.model_agent,
        "customer": config.model_customer,
        "judge": config.model_judge,
    }[role]


def _complete_anthropic(config, role, messages):
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    turns = [m for m in messages if m["role"] != "system"]
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": config.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": _model_for_role(config, role),
            "max_tokens": 1024,
            "system": system,
            "messages": turns,
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return "".join(block.get("text", "") for block in data.get("content", []))


def _complete_gemini(config, role, messages):
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    contents = [
        {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
        for m in messages if m["role"] != "system"
    ]
    model = _model_for_role(config, role)
    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": config.gemini_api_key, "content-type": "application/json"},
        json={"contents": contents, "systemInstruction": {"parts": [{"text": system}]}},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    candidates = data.get("candidates", [])
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts)


def _complete_openai_style(base_url, api_key, model, messages):
    resp = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "content-type": "application/json"},
        json={"model": model, "messages": messages},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _complete_groq(config, role, messages):
    return _complete_openai_style(
        "https://api.groq.com/openai/v1", config.groq_api_key, _model_for_role(config, role), messages,
    )


def _complete_openai_compatible(config, role, messages):
    return _complete_openai_style(
        config.llm_base_url.rstrip("/"), config.llm_api_key, _model_for_role(config, role), messages,
    )


def _complete_claude_cli(config, role, messages):
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    conversation = "\n\n".join(
        f"{m['role']}: {m['content']}" for m in messages if m["role"] != "system"
    )
    prompt = f"{system}\n\n{conversation}" if system else conversation
    result = subprocess.run(
        ["claude", "-p", prompt], capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude -p failed: {result.stderr}")
    return result.stdout.strip()


_PROVIDERS = {
    "anthropic": _complete_anthropic,
    "gemini": _complete_gemini,
    "groq": _complete_groq,
    "openai_compatible": _complete_openai_compatible,
    "claude_cli": _complete_claude_cli,
}

_rate_limiters = {}


def _rate_limiter_for(config):
    key = (config.max_requests_per_minute, config.max_requests_per_day)
    if key not in _rate_limiters:
        _rate_limiters[key] = RateLimiter(*key)
    return _rate_limiters[key]


def complete(role, messages, json_schema=None, config=None, max_retries=3):
    """role is "agent", "customer", or "judge". Returns raw text; callers
    that need JSON parse and validate it themselves (CLAUDE.md Part 5.5's
    JSON action protocol handles its own retry-on-invalid-JSON).
    """
    config = config or Config.from_env()
    if config.provider not in _PROVIDERS:
        raise ValueError(
            f"unknown LLM_PROVIDER: {config.provider!r} (expected one of "
            f"{sorted(_PROVIDERS)} or 'fake' for --dry-run)"
        )

    limiter = _rate_limiter_for(config)
    fn = _PROVIDERS[config.provider]

    retryable_statuses = {429, 500, 502, 503, 504}
    backoff = 1
    last_exc = None
    for attempt in range(max_retries):
        limiter.before_request()
        try:
            return fn(config, role, messages)
        except requests.HTTPError as exc:
            last_exc = exc
            status = exc.response.status_code if exc.response is not None else None
            if status in retryable_statuses and attempt < max_retries - 1:
                time.sleep(backoff)
                backoff *= 2
                continue
            raise
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                time.sleep(backoff)
                backoff *= 2
                continue
            raise
    raise last_exc
