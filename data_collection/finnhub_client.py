"""
Finnhub client helpers for peer discovery and lightweight peer-metric enrichment.

Finnhub is used as the primary source for:
- peer candidate discovery
- company profile metadata
- basic market multiples needed by comparable-company analysis

Yahoo Finance remains available as a secondary source elsewhere in the project,
but peer selection should avoid heavy quote/fundamental calls whenever Finnhub can
provide the necessary fields directly.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List

import requests

from config import FINNHUB_API_KEY
from data_collection.http_client import HttpClient

_BASE_URL = "https://finnhub.io/api/v1"
_HEADERS = {"User-Agent": "AI Valuation Terminal research contact@localhost.com"}
_CACHE: Dict[tuple[str, str], tuple[float, Any]] = {}
_SNAPSHOT_ROOT = Path(__file__).resolve().parent.parent / "snapshots" / "raw_market_data"
_HTTP = HttpClient(
    base_headers=_HEADERS,
    default_timeout=4.0,
    max_retries=1,
    backoff_seconds=0.35,
)


def _normalize_symbol(symbol: str) -> str:
    return (symbol or "").strip().upper().replace(".", "-")


def _get_cached(cache_key: tuple[str, str], ttl_seconds: float) -> Any:
    cached = _CACHE.get(cache_key)
    if not cached:
        return None
    expires_at, value = cached
    if expires_at < time.monotonic():
        _CACHE.pop(cache_key, None)
        return None
    return value


def _set_cached(cache_key: tuple[str, str], ttl_seconds: float, value: Any) -> Any:
    _CACHE[cache_key] = (time.monotonic() + ttl_seconds, value)
    return value


def _snapshot_path(symbol: str, key: str) -> Path:
    return _SNAPSHOT_ROOT / _normalize_symbol(symbol) / f"{key}.json"


def _save_snapshot(symbol: str, key: str, payload: Any) -> None:
    path = _snapshot_path(symbol, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_snapshot(symbol: str, key: str) -> Any:
    path = _snapshot_path(symbol, key)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _get_json(path: str, params: Dict[str, Any]) -> Dict[str, Any] | List[Any]:
    return _HTTP.get_json(
        f"{_BASE_URL}/{path.lstrip('/')}",
        params={**params, "token": FINNHUB_API_KEY},
    )


def get_peer_companies(symbol: str, timeout: float = 4.0, ttl_seconds: float = 300.0) -> List[str]:
    """Return a normalized peer-symbol list from Finnhub."""
    if not FINNHUB_API_KEY:
        return []
    cache_key = ("peers", _normalize_symbol(symbol))
    cached = _get_cached(cache_key, ttl_seconds)
    if cached is not None:
        return cached
    try:
        payload = _HTTP.get_json(
            f"{_BASE_URL}/stock/peers",
            params={"symbol": _normalize_symbol(symbol), "token": FINNHUB_API_KEY},
            timeout=timeout,
            retries=1,
        )
    except requests.RequestException:
        payload = _load_snapshot(symbol, "finnhub_peers") or []
    if isinstance(payload, list):
        _save_snapshot(symbol, "finnhub_peers", payload)
    else:
        payload = _load_snapshot(symbol, "finnhub_peers") or []

    normalized = []
    seen = set()
    for item in payload:
        peer = _normalize_symbol(str(item))
        if not peer or peer in seen:
            continue
        seen.add(peer)
        normalized.append(peer)
    return _set_cached(cache_key, ttl_seconds, normalized)


def get_company_profile(symbol: str, timeout: float = 4.0, ttl_seconds: float = 300.0) -> Dict[str, Any]:
    """Return Finnhub company profile data for a ticker."""
    if not FINNHUB_API_KEY:
        return {}
    cache_key = ("profile", _normalize_symbol(symbol))
    cached = _get_cached(cache_key, ttl_seconds)
    if cached is not None:
        return cached
    try:
        payload = _HTTP.get_json(
            f"{_BASE_URL}/stock/profile2",
            params={"symbol": _normalize_symbol(symbol), "token": FINNHUB_API_KEY},
            timeout=timeout,
            retries=1,
        )
    except requests.RequestException:
        payload = _load_snapshot(symbol, "finnhub_profile2") or {}
    if isinstance(payload, dict):
        _save_snapshot(symbol, "finnhub_profile2", payload)
        value = payload
    else:
        value = _load_snapshot(symbol, "finnhub_profile2") or {}
    return _set_cached(cache_key, ttl_seconds, value)


def get_basic_financials(symbol: str, timeout: float = 4.0, ttl_seconds: float = 300.0) -> Dict[str, Any]:
    """Return Finnhub basic-financial metrics payload for a ticker."""
    if not FINNHUB_API_KEY:
        return {}
    cache_key = ("metric", _normalize_symbol(symbol))
    cached = _get_cached(cache_key, ttl_seconds)
    if cached is not None:
        return cached
    try:
        payload = _HTTP.get_json(
            f"{_BASE_URL}/stock/metric",
            params={"symbol": _normalize_symbol(symbol), "metric": "all", "token": FINNHUB_API_KEY},
            timeout=timeout,
            retries=1,
        )
    except requests.RequestException:
        payload = _load_snapshot(symbol, "finnhub_basic_financials") or {}
    if isinstance(payload, dict):
        _save_snapshot(symbol, "finnhub_basic_financials", payload)
        value = payload
    else:
        value = _load_snapshot(symbol, "finnhub_basic_financials") or {}
    return _set_cached(cache_key, ttl_seconds, value)
