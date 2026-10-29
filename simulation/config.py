"""Simulation harness config (CLAUDE.md Part 5.5). Reads env; model names
are never hard-coded here — verify current names/prices in the provider's
docs before the first real run (CLAUDE.md Part 0 rule 5).

Not in the Part 4.1 repository tree; flagged in docs/OPEN_QUESTIONS.md #9.
"""

import os
from dataclasses import dataclass

_DOTENV_LOADED = False


def _load_dotenv():
    """Minimal stdlib .env loader — no python-dotenv dependency (Part 2
    rule 13). Does not override a variable already set in the real
    environment. Silently does nothing if .env doesn't exist."""
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    _DOTENV_LOADED = True

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, ".env")
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if key and key not in os.environ:
                os.environ[key] = value


def _float(name, default):
    raw = os.environ.get(name)
    return float(raw) if raw else default


def _int(name, default):
    raw = os.environ.get(name)
    return int(raw) if raw else default


@dataclass
class Config:
    provider: str = "fake"
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    groq_api_key: str = ""
    llm_base_url: str = ""
    llm_api_key: str = ""
    model_agent: str = ""
    model_customer: str = ""
    model_judge: str = ""
    max_requests_per_minute: int = 20
    max_requests_per_day: int = 200
    max_sim_cost_usd: float = 2.0
    fallback_provider: str = ""
    fallback_model_agent: str = ""
    fallback_model_customer: str = ""
    fallback_model_judge: str = ""

    @classmethod
    def from_env(cls):
        _load_dotenv()
        return cls(
            provider=os.environ.get("LLM_PROVIDER", "fake") or "fake",
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
            groq_api_key=os.environ.get("GROQ_API_KEY", ""),
            llm_base_url=os.environ.get("LLM_BASE_URL", ""),
            llm_api_key=os.environ.get("LLM_API_KEY", ""),
            model_agent=os.environ.get("LLM_MODEL_AGENT", ""),
            model_customer=os.environ.get("LLM_MODEL_CUSTOMER", ""),
            model_judge=os.environ.get("LLM_MODEL_JUDGE", ""),
            max_requests_per_minute=_int("MAX_REQUESTS_PER_MINUTE", 20),
            max_requests_per_day=_int("MAX_REQUESTS_PER_DAY", 200),
            max_sim_cost_usd=_float("MAX_SIM_COST_USD", 2.0),
            fallback_provider=os.environ.get("LLM_FALLBACK_PROVIDER", ""),
            fallback_model_agent=os.environ.get("LLM_FALLBACK_MODEL_AGENT", ""),
            fallback_model_customer=os.environ.get("LLM_FALLBACK_MODEL_CUSTOMER", ""),
            fallback_model_judge=os.environ.get("LLM_FALLBACK_MODEL_JUDGE", ""),
        )
