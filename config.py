"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _get_required_env(name: str) -> str:
    """Return a required environment variable or fail fast with a clear message."""
    value = os.getenv(name)
    if value:
        return value
    raise RuntimeError(f"Missing required environment variable: {name}")


def _get_optional_env(name: str) -> str | None:
    """Return an optional environment variable without applying insecure defaults."""
    value = os.getenv(name)
    return value if value else None


# Required data-source credentials.
FRED_API_KEY = _get_required_env("FRED_API_KEY")
FINNHUB_API_KEY = _get_required_env("FINNHUB_API_KEY")

# Optional LLM credentials. These remain blank-safe because chat and narrative critique
# can fall back to deterministic retrieval when no model key is configured.
GEMINI_API_KEY = _get_optional_env("GEMINI_API_KEY")
OPENAI_API_KEY = _get_optional_env("OPENAI_API_KEY")
ANTHROPIC_API_KEY = _get_optional_env("ANTHROPIC_API_KEY")

# Default analysis scope. This is a demonstration universe definition, not financial data.
TARGET_TICKERS = [
    "AAPL",
    "MSFT",
    "NVDA",
    "GOOGL",
    "AMZN",
    "META",
    "BRK-B",
    "LLY",
    "AVGO",
    "TSM",
    "JPM",
    "WMT",
    "V",
    "UNH",
    "MA",
    "XOM",
    "ORCL",
    "COST",
    "HD",
    "PG",
]

# Non-sensitive runtime behavior.
DCF_FORECAST_YEARS = int(os.getenv("DCF_FORECAST_YEARS", "5"))
SENSITIVITY_STEP_BP = int(os.getenv("SENSITIVITY_STEP_BP", "100"))
MIN_PEER_COUNT = int(os.getenv("MIN_PEER_COUNT", "3"))
MAX_PEER_COUNT = int(os.getenv("MAX_PEER_COUNT", "8"))
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")
