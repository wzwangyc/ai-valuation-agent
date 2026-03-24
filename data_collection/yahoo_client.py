"""
Shared market-data client with primary, backup, and raw-snapshot fallback paths.
Snapshots store raw source payloads rather than processed outputs.
"""
from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, Tuple
from urllib.parse import quote
from xml.etree import ElementTree as ET

import pandas as pd
import logging
import requests
import yfinance as yf
from data_collection.http_client import HttpClient

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_LAST_REQUEST_TS = 0.0
_CACHE: Dict[Tuple[Any, ...], Tuple[float, Any]] = {}
_MIN_INTERVAL_SECONDS = 0.25
_REQUEST_TIMEOUT_SECONDS = 5
_YFINANCE_TIMEOUT_SECONDS = 2.5
_HEADERS = {"User-Agent": "AI Valuation Terminal research contact@localhost.com"}
_SNAPSHOT_ROOT = Path(__file__).resolve().parent.parent / "snapshots" / "raw_market_data"
_HTTP = HttpClient(
    base_headers=_HEADERS,
    default_timeout=_REQUEST_TIMEOUT_SECONDS,
    max_retries=1,
    backoff_seconds=0.35,
)

_INCOME_TYPES = {
    "annualTotalRevenue": "Total Revenue",
    "annualGrossProfit": "Gross Profit",
    "annualOperatingIncome": "Operating Income",
    "annualNetIncome": "Net Income",
    "annualPretaxIncome": "Pretax Income",
    "annualTaxProvision": "Tax Provision",
    "annualInterestExpense": "Interest Expense",
}

_BALANCE_TYPES = {
    "annualCashAndCashEquivalents": "Cash And Cash Equivalents",
    "annualTotalDebt": "Total Debt",
    "annualCurrentAssets": "Current Assets",
    "annualCurrentLiabilities": "Current Liabilities",
    "annualAccountsReceivable": "Accounts Receivable",
    "annualInventory": "Inventory",
    "annualAccountsPayable": "Accounts Payable",
    "annualBasicAverageShares": "Shares Outstanding",
}

_CASHFLOW_TYPES = {
    "annualOperatingCashFlow": "Operating Cash Flow",
    "annualCapitalExpenditure": "Capital Expenditure",
    "annualDepreciationAndAmortization": "Depreciation And Amortization",
}


def _sleep_if_needed() -> None:
    global _LAST_REQUEST_TS
    with _LOCK:
        now = time.monotonic()
        wait_for = _MIN_INTERVAL_SECONDS - (now - _LAST_REQUEST_TS)
        if wait_for > 0:
            time.sleep(wait_for)
        _LAST_REQUEST_TS = time.monotonic()


def _request_json(url: str) -> Dict:
    _sleep_if_needed()
    return _HTTP.get_json(url)


def _get_cached(cache_key: Tuple[Any, ...], ttl_seconds: float) -> Any:
    cached = _CACHE.get(cache_key)
    if not cached:
        return None
    expires_at, value = cached
    if expires_at < time.monotonic():
        _CACHE.pop(cache_key, None)
        return None
    return value


def _set_cached(cache_key: Tuple[Any, ...], ttl_seconds: float, value: Any) -> Any:
    _CACHE[cache_key] = (time.monotonic() + ttl_seconds, value)
    return value


def _snapshot_path(symbol: str, key: str) -> Path:
    return _SNAPSHOT_ROOT / symbol.upper() / f"{key}.json"


def _snapshot_exists(symbol: str, key: str) -> bool:
    return _snapshot_path(symbol, key).exists()


def save_raw_snapshot(symbol: str, key: str, payload: Any) -> None:
    path = _snapshot_path(symbol, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def load_raw_snapshot(symbol: str, key: str) -> Any:
    path = _snapshot_path(symbol, key)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _coerce_frame(frame) -> pd.DataFrame:
    return frame.fillna(0) if hasattr(frame, "fillna") else pd.DataFrame()


def _safe_yfinance(fetcher, default):
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: (_sleep_if_needed(), fetcher())[1])
            value = future.result(timeout=_YFINANCE_TIMEOUT_SECONDS)
        return default if value is None else value
    except Exception as exc:
        logger.debug("yfinance call failed; using fallback path: %s", exc)
        return default


def _prefer_primary(primary: Any, fallback: Any) -> Any:
    return primary if primary not in (None, "", [], {}, ()) else fallback


def _merge_dict_prefer_primary(primary: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(fallback or {})
    for key, value in (primary or {}).items():
        if value not in (None, "", [], {}, ()):
            merged[key] = value
    return merged


def _merge_frames_prefer_primary(primary: pd.DataFrame, fallback: pd.DataFrame) -> pd.DataFrame:
    if primary is None or primary.empty:
        return fallback.fillna(0) if hasattr(fallback, "fillna") else pd.DataFrame()
    if fallback is None or fallback.empty:
        return primary.fillna(0)
    merged = primary.combine_first(fallback)
    merged = merged.reindex(sorted(merged.columns, reverse=True), axis=1)
    return merged.fillna(0)


def _normalize_news_records(items: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    normalized = []
    for item in items or []:
        content = item.get("content") if isinstance(item, dict) else None
        if content:
            title = content.get("title")
            url = ((content.get("clickThroughUrl") or {}).get("url")) or ((content.get("canonicalUrl") or {}).get("url"))
        else:
            title = item.get("title") if isinstance(item, dict) else None
            url = item.get("url") if isinstance(item, dict) else None
        if title or url:
            normalized.append(item)
    return normalized


def _dedupe_news(items: list[Dict[str, Any]], limit: int) -> list[Dict[str, Any]]:
    merged = []
    seen = set()
    for item in _normalize_news_records(items):
        content = item.get("content", {})
        key = (
            content.get("title") or item.get("title"),
            ((content.get("clickThroughUrl") or {}).get("url")) or ((content.get("canonicalUrl") or {}).get("url")) or item.get("url"),
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
        if len(merged) >= limit:
            break
    return merged


def _dedupe_filings(items: list[Dict[str, Any]], limit: int = 5) -> list[Dict[str, Any]]:
    merged = []
    seen = set()
    for filing in items or []:
        key = (
            filing.get("type"),
            filing.get("date"),
            filing.get("edgarUrl"),
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(filing)
        if len(merged) >= limit:
            break
    return merged


def _fetch_chart_raw(symbol: str, range_value: str = "6mo", interval: str = "1d") -> Dict:
    payload = _request_json(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol.upper()}?range={range_value}&interval={interval}"
    )
    save_raw_snapshot(symbol, f"chart_{range_value}_{interval}", payload)
    return payload


def _load_chart_raw(symbol: str, range_value: str = "6mo", interval: str = "1d") -> Dict:
    try:
        return _fetch_chart_raw(symbol, range_value, interval)
    except Exception:
        snapshot = load_raw_snapshot(symbol, f"chart_{range_value}_{interval}")
        if snapshot is not None:
            return snapshot
        raise


def _chart_meta(symbol: str) -> Dict:
    payload = _load_chart_raw(symbol, "6mo", "1d")
    result = ((payload.get("chart") or {}).get("result") or [{}])[0]
    return result.get("meta", {}) or {}


def _history_from_chart_payload(payload: Dict) -> pd.DataFrame:
    result = ((payload.get("chart") or {}).get("result") or [{}])[0]
    timestamps = result.get("timestamp") or []
    quote = (((result.get("indicators") or {}).get("quote") or [{}])[0]) or {}
    rows = []
    for idx, ts in enumerate(timestamps):
        rows.append(
            {
                "Date": pd.to_datetime(ts, unit="s"),
                "Open": quote.get("open", [None] * len(timestamps))[idx],
                "High": quote.get("high", [None] * len(timestamps))[idx],
                "Low": quote.get("low", [None] * len(timestamps))[idx],
                "Close": quote.get("close", [None] * len(timestamps))[idx],
                "Volume": quote.get("volume", [None] * len(timestamps))[idx],
            }
        )
    frame = pd.DataFrame(rows).dropna(subset=["Close"])
    return frame.set_index("Date") if not frame.empty else frame


def _history_from_chart(symbol: str, period: str) -> pd.DataFrame:
    range_map = {
        "1d": ("5d", "1d"),
        "1mo": ("1mo", "1d"),
        "6mo": ("6mo", "1d"),
        "1y": ("1y", "1d"),
        "5y": ("5y", "1wk"),
    }
    range_value, interval = range_map.get(period, ("6mo", "1d"))
    payload = _load_chart_raw(symbol, range_value, interval)
    return _history_from_chart_payload(payload)


def _fetch_fundamentals_raw(symbol: str) -> Dict:
    all_types = list(_INCOME_TYPES.keys()) + list(_BALANCE_TYPES.keys()) + list(_CASHFLOW_TYPES.keys())
    type_clause = ",".join(all_types)
    payload = _request_json(
        "https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/"
        f"{symbol.upper()}?type={type_clause}&merge=false&period1=1609459200&period2=1893456000"
    )
    save_raw_snapshot(symbol, "fundamentals_timeseries", payload)
    return payload


def _load_fundamentals_raw(symbol: str) -> Dict:
    try:
        return _fetch_fundamentals_raw(symbol)
    except Exception:
        snapshot = load_raw_snapshot(symbol, "fundamentals_timeseries")
        if snapshot is not None:
            return snapshot
        raise


def _frame_from_timeseries(payload: Dict, mapping: Dict[str, str]) -> pd.DataFrame:
    result = ((payload.get("timeseries") or {}).get("result") or [])
    rows = {}
    for item in result:
        type_name = ((item.get("meta") or {}).get("type") or [None])[0]
        if type_name not in mapping:
            continue
        label = mapping[type_name]
        values = item.get(type_name) or []
        row = {}
        for entry in values:
            date_key = entry.get("asOfDate")
            raw_value = ((entry.get("reportedValue") or {}).get("raw"))
            if date_key:
                row[pd.Timestamp(date_key)] = raw_value
        rows[label] = row
    frame = pd.DataFrame.from_dict(rows, orient="index")
    if frame.empty:
        return frame
    frame = frame.reindex(sorted(frame.columns, reverse=True), axis=1)
    return frame.fillna(0)


def _load_frames(symbol: str):
    payload = _load_fundamentals_raw(symbol)
    return {
        "financials": _frame_from_timeseries(payload, _INCOME_TYPES),
        "balance_sheet": _frame_from_timeseries(payload, _BALANCE_TYPES),
        "cashflow": _frame_from_timeseries(payload, _CASHFLOW_TYPES),
    }


def _fetch_sec_company_tickers() -> Dict:
    payload = _request_json("https://www.sec.gov/files/company_tickers.json")
    save_raw_snapshot("SEC", "company_tickers", payload)
    return payload


def _company_tickers() -> Dict:
    cache_key = ("sec_company_tickers",)
    cached = _get_cached(cache_key, 86400)
    if cached is not None:
        return cached
    try:
        value = _fetch_sec_company_tickers()
    except Exception:
        value = load_raw_snapshot("SEC", "company_tickers") or {}
    return _set_cached(cache_key, 86400, value)


def _sec_cik_for_symbol(symbol: str) -> str | None:
    records = _company_tickers()
    upper = symbol.upper()
    for item in records.values():
        if str(item.get("ticker", "")).upper() == upper:
            return str(item.get("cik_str")).zfill(10)
    return None


def _fetch_sec_filings_raw(symbol: str):
    cik = _sec_cik_for_symbol(symbol)
    if not cik:
        return []
    payload = _request_json(f"https://data.sec.gov/submissions/CIK{cik}.json")
    save_raw_snapshot(symbol, "sec_submissions", payload)
    return payload


def _sec_filings_from_payload(payload: Dict):
    recent = ((payload.get("filings") or {}).get("recent") or {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])
    filings = []
    cik = str(payload.get("cik", "")).zfill(10)
    for form, date, accession, doc in zip(forms, dates, accessions, primary_docs):
        accession_clean = str(accession).replace("-", "")
        doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_clean}/{doc}" if cik else None
        filings.append(
            {
                "date": date,
                "type": form,
                "title": f"{form} filing dated {date}",
                "edgarUrl": doc_url,
                "exhibits": {form: doc_url} if doc_url else {},
            }
        )
    return filings


def _fetch_google_news_raw(symbol: str, count: int):
    query = quote(f"{symbol.upper()} stock")
    _sleep_if_needed()
    response = requests.get(
        f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en",
        headers=_HEADERS,
        timeout=20,
    )
    response.raise_for_status()
    payload = {"rss": response.text, "count": count}
    save_raw_snapshot(symbol, f"google_news_{count}", payload)
    return payload


def _google_news_from_payload(payload: Dict, count: int):
    root = ET.fromstring(payload.get("rss", ""))
    items = []
    for item in root.findall(".//item")[:count]:
        items.append(
            {
                "content": {
                    "title": item.findtext("title") or "",
                    "summary": item.findtext("description") or "",
                    "pubDate": item.findtext("pubDate"),
                    "provider": {"displayName": "Google News"},
                    "clickThroughUrl": {"url": item.findtext("link")},
                    "contentType": "STORY",
                }
            }
        )
    return items


def warm_raw_snapshots(symbol: str, news_count: int = 5) -> Dict[str, bool]:
    ticker = get_ticker(symbol)
    results = {}
    for name, fn in {
        "chart": lambda: _fetch_chart_raw(symbol, "6mo", "1d"),
        "chart_1mo": lambda: _fetch_chart_raw(symbol, "1mo", "1d"),
        "fundamentals": lambda: _fetch_fundamentals_raw(symbol),
        "news": lambda: _fetch_google_news_raw(symbol, news_count),
        "sec_filings": lambda: _fetch_sec_filings_raw(symbol),
    }.items():
        try:
            fn()
            results[name] = True
        except Exception:
            results[name] = False
    try:
        _safe_yfinance(lambda: ticker.info, {})
        _safe_yfinance(lambda: ticker.fast_info, {})
    except Exception:
        pass
    return results


def get_ticker(symbol: str) -> yf.Ticker:
    return yf.Ticker(symbol.upper())


def get_info(ticker: yf.Ticker, symbol: str, ttl_seconds: float = 300, retries: int = 1, backoff: float = 0) -> Dict:
    del retries, backoff
    cache_key = ("info", symbol.upper())
    cached = _get_cached(cache_key, ttl_seconds)
    if cached is not None:
        return cached

    info = _safe_yfinance(lambda: ticker.info, {}) or {}
    fast_info = _safe_yfinance(lambda: dict(ticker.fast_info), {})
    meta = _chart_meta(symbol)
    fundamentals = _load_frames(symbol)["balance_sheet"]
    shares = None
    if "Shares Outstanding" in fundamentals.index and not fundamentals.empty:
        shares = float(fundamentals.loc["Shares Outstanding"].iloc[0] or 0)
    price = (
        info.get("currentPrice")
        or info.get("regularMarketPrice")
        or meta.get("regularMarketPrice")
        or fast_info.get("lastPrice")
    )
    market_cap = info.get("marketCap") or fast_info.get("marketCap") or fast_info.get("market_cap")
    if not market_cap and shares and price:
        market_cap = shares * price
    fallback_value = {
        "longName": meta.get("longName") or meta.get("shortName") or symbol.upper(),
        "shortName": meta.get("shortName") or symbol.upper(),
        "currentPrice": price,
        "regularMarketPrice": price,
        "marketCap": market_cap,
        "sharesOutstanding": fast_info.get("shares") or fast_info.get("shares_outstanding") or shares,
        "fiftyTwoWeekHigh": meta.get("fiftyTwoWeekHigh") or fast_info.get("yearHigh"),
        "fiftyTwoWeekLow": meta.get("fiftyTwoWeekLow") or fast_info.get("yearLow"),
        "beta": fast_info.get("beta"),
        "currency": meta.get("currency"),
    }
    value = _merge_dict_prefer_primary(info, fallback_value)
    value["currentPrice"] = _prefer_primary(value.get("currentPrice"), fallback_value.get("currentPrice"))
    value["regularMarketPrice"] = _prefer_primary(value.get("regularMarketPrice"), fallback_value.get("regularMarketPrice"))
    value["marketCap"] = _prefer_primary(value.get("marketCap"), fallback_value.get("marketCap"))
    value["sharesOutstanding"] = _prefer_primary(value.get("sharesOutstanding"), fallback_value.get("sharesOutstanding"))
    value["beta"] = _prefer_primary(value.get("beta"), fallback_value.get("beta"))
    return _set_cached(cache_key, ttl_seconds, value)


def get_quote_multiples(ticker: yf.Ticker, symbol: str, ttl_seconds: float = 300) -> Dict:
    """
    Lightweight company-multiples lookup for peer enrichment.

    This intentionally avoids loading full fundamentals-timeseries payloads. Peer selection only
    needs quote-level market multiples and identity fields, so the heavier statement fallback path
    used by `get_info()` is unnecessary and materially slows candidate enrichment.
    """
    cache_key = ("quote_multiples", symbol.upper())
    cached = _get_cached(cache_key, ttl_seconds)
    if cached is not None:
        return cached

    info = _safe_yfinance(lambda: ticker.info, {}) or {}
    fast_info = _safe_yfinance(lambda: dict(ticker.fast_info), {}) or {}
    meta = _chart_meta(symbol)

    price = (
        info.get("currentPrice")
        or info.get("regularMarketPrice")
        or meta.get("regularMarketPrice")
        or fast_info.get("lastPrice")
    )
    fallback_value = {
        "longName": meta.get("longName") or meta.get("shortName") or symbol.upper(),
        "shortName": meta.get("shortName") or symbol.upper(),
        "currentPrice": price,
        "regularMarketPrice": price,
        "marketCap": info.get("marketCap") or fast_info.get("marketCap") or fast_info.get("market_cap"),
        "sharesOutstanding": info.get("sharesOutstanding") or fast_info.get("shares") or fast_info.get("shares_outstanding"),
        "beta": info.get("beta") or fast_info.get("beta"),
        "trailingPE": info.get("trailingPE"),
        "enterpriseToEbitda": info.get("enterpriseToEbitda"),
        "priceToBook": info.get("priceToBook"),
        "enterpriseToRevenue": info.get("enterpriseToRevenue"),
        "returnOnEquity": info.get("returnOnEquity"),
        "industry": info.get("industry") or info.get("industryKey"),
        "sector": info.get("sector") or info.get("sectorKey"),
    }
    value = _merge_dict_prefer_primary(info, fallback_value)
    return _set_cached(cache_key, ttl_seconds, value)


def get_history(ticker: yf.Ticker, symbol: str, period: str = "1d", ttl_seconds: float = 120):
    cache_key = ("history", symbol.upper(), period)
    cached = _get_cached(cache_key, ttl_seconds)
    if cached is not None:
        return cached
    value = _safe_yfinance(lambda: ticker.history(period=period), None)
    if value is not None and not value.empty:
        return _set_cached(cache_key, ttl_seconds, value)
    fallback = _history_from_chart(symbol, period)
    return _set_cached(cache_key, ttl_seconds, fallback)


def get_news(ticker: yf.Ticker, symbol: str, count: int = 5, tab: str = "news", ttl_seconds: float = 300):
    cache_key = ("news", symbol.upper(), count, tab)
    cached = _get_cached(cache_key, ttl_seconds)
    if cached is not None:
        return cached
    value = _safe_yfinance(lambda: ticker.get_news(count=count, tab=tab), []) or []
    try:
        raw_payload = _fetch_google_news_raw(symbol, count)
    except Exception:
        raw_payload = load_raw_snapshot(symbol, f"google_news_{count}") or {"rss": ""}
    fallback = _google_news_from_payload(raw_payload, count) if raw_payload else []
    merged = _dedupe_news((value or []) + (fallback or []), count)
    return _set_cached(cache_key, ttl_seconds, merged)


def get_sec_filings(ticker: yf.Ticker, symbol: str, ttl_seconds: float = 300):
    cache_key = ("sec_filings", symbol.upper())
    cached = _get_cached(cache_key, ttl_seconds)
    if cached is not None:
        return cached
    value = _safe_yfinance(lambda: ticker.get_sec_filings(), []) or []
    try:
        payload = _fetch_sec_filings_raw(symbol)
    except Exception:
        payload = load_raw_snapshot(symbol, "sec_submissions") or {}
    fallback = _sec_filings_from_payload(payload) if payload else []
    merged = _dedupe_filings((value or []) + (fallback or []), limit=max(50, len(value or [])))
    return _set_cached(cache_key, ttl_seconds, merged)


def get_financials(ticker: yf.Ticker, symbol: str, ttl_seconds: float = 300):
    cache_key = ("financials", symbol.upper())
    cached = _get_cached(cache_key, ttl_seconds)
    if cached is not None:
        return cached
    value = _coerce_frame(_safe_yfinance(lambda: ticker.financials, pd.DataFrame()))
    fallback = _load_frames(symbol)["financials"]
    merged = _merge_frames_prefer_primary(value, fallback)
    return _set_cached(cache_key, ttl_seconds, merged)


def get_balance_sheet(ticker: yf.Ticker, symbol: str, ttl_seconds: float = 300):
    cache_key = ("balance_sheet", symbol.upper())
    cached = _get_cached(cache_key, ttl_seconds)
    if cached is not None:
        return cached
    value = _coerce_frame(_safe_yfinance(lambda: ticker.balance_sheet, pd.DataFrame()))
    fallback = _load_frames(symbol)["balance_sheet"]
    merged = _merge_frames_prefer_primary(value, fallback)
    return _set_cached(cache_key, ttl_seconds, merged)


def get_cashflow(ticker: yf.Ticker, symbol: str, ttl_seconds: float = 300):
    cache_key = ("cashflow", symbol.upper())
    cached = _get_cached(cache_key, ttl_seconds)
    if cached is not None:
        return cached
    value = _coerce_frame(_safe_yfinance(lambda: ticker.cashflow, pd.DataFrame()))
    fallback = _load_frames(symbol)["cashflow"]
    merged = _merge_frames_prefer_primary(value, fallback)
    return _set_cached(cache_key, ttl_seconds, merged)
