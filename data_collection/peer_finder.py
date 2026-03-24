"""
Comparable peer selection with Finnhub-first candidate sourcing.

Peer discovery and core peer multiples should be resolved from fast market-data APIs first.
This avoids large batches of expensive Yahoo quote lookups, which were the main source of
timeouts and rate-limit exposure during comparable-company analysis.
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from typing import Dict, List, Tuple

import requests
import yfinance as yf

from data_collection.finnhub_client import get_basic_financials, get_peer_companies
from data_collection.yahoo_client import get_info, get_quote_multiples

logger = logging.getLogger(__name__)

FILTER_CONDITIONS = {
    "min_roe": 0.0,
    "min_market_cap": 0,
}

TIER_RULES = {
    "Tier 1": 1000,
    "Tier 2": 500,
    "Tier 3": 0,
}

INDUSTRY_TICKER_MAP = {
    "Software - Infrastructure": ["ORCL", "PANW", "FTNT", "NOW", "IBM", "CSCO", "ADBE", "SAP", "CRM", "GEN"],
    "Consumer Electronics": ["DELL", "HPQ", "NTAP", "PSTG", "WDC", "SMCI", "GRMN", "STX", "SONY", "VRT"],
    "Semiconductors": ["NVDA", "AMD", "INTC", "TSM", "AVGO", "QCOM", "TXN", "MU", "AMAT", "KLAC"],
    "Banks - Diversified": ["JPM", "BAC", "WFC", "C", "GS", "MS", "USB", "PNC", "TFC", "BK"],
    "Oil & Gas Equipment & Services": ["HAL", "BKR", "NOV", "FTI", "CHX", "LBRT", "OII", "WHD", "DRQ", "RES"],
    "Oil & Gas Integrated": ["XOM", "CVX", "SHEL", "BP", "TTE", "COP", "EOG", "OXY", "MPC", "PSX"],
    "Oil & Gas E&P": ["COP", "EOG", "OXY", "DVN", "APA", "HES", "FANG", "MRO", "EQT", "PXD"],
}

SECTOR_TICKER_MAP = {
    "Technology": ["MSFT", "AAPL", "NVDA", "GOOGL", "META", "ORCL", "ADBE", "CRM", "CSCO", "IBM"],
    "Financial Services": ["JPM", "BAC", "WFC", "C", "GS", "MS", "AXP", "USB", "PNC", "BK"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "HAL", "BKR", "EOG", "OXY", "MPC", "PSX"],
    "Communication Services": ["GOOGL", "META", "NFLX", "DIS", "TMUS", "VZ", "T", "CMCSA", "CHTR", "EA"],
    "Consumer Cyclical": ["AMZN", "TSLA", "HD", "LOW", "MCD", "NKE", "SBUX", "BKNG", "RCL", "GM"],
}


def _safe_round(value, digits=2):
    try:
        if value is None:
            return None
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


class PeerFinder:
    """Find comparable companies using Finnhub-first logic and deterministic filters."""

    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.stock = yf.Ticker(self.ticker)
        self._info = None
        self.last_run: Dict[str, object] = {
            "target": {},
            "rules": [],
            "selected_peers": [],
            "selection_log": [],
            "warning": None,
        }

    @property
    def info(self) -> Dict:
        if self._info is None:
            try:
                self._info = get_info(self.stock, self.ticker)
            except Exception as exc:
                logger.warning("[%s] Target info lookup failed: %s", self.ticker, exc)
                self._info = {}
        return self._info

    def _fallback_industry(self) -> str:
        for industry, tickers in INDUSTRY_TICKER_MAP.items():
            if self.ticker in tickers:
                return industry
        return "Unknown"

    def _get_company_industry(self) -> Tuple[str, str]:
        industry = self.info.get("industry") or self.info.get("industryKey") or self._fallback_industry()
        sector = self.info.get("sector") or self.info.get("sectorKey") or "Unknown"
        return industry, sector

    def _get_candidate_tickers(self, industry_name: str, sector_name: str, top_n: int = 10, min_peers: int = 6) -> List[str]:
        candidates: List[str] = []
        curated = [symbol for symbol in INDUSTRY_TICKER_MAP.get(industry_name, []) if symbol != self.ticker]
        finnhub_peers: List[str] = []

        try:
            finnhub_peers = [symbol for symbol in get_peer_companies(self.ticker) if symbol != self.ticker]
        except requests.RequestException as exc:
            logger.warning("[%s] Finnhub peer lookup failed: %s", self.ticker, exc)

        # Evaluate the overlap between curated peers and Finnhub-discovered peers first.
        # This captures the most relevant and most likely available candidates within
        # the fixed wall-clock budget.
        for symbol in curated:
            if symbol in finnhub_peers and symbol not in candidates:
                candidates.append(symbol)

        for symbol in curated:
            if symbol not in candidates:
                candidates.append(symbol)

        for symbol in finnhub_peers:
            if symbol not in candidates:
                candidates.append(symbol)

        if len(candidates) < top_n:
            for symbol in SECTOR_TICKER_MAP.get(sector_name, []):
                if symbol != self.ticker and symbol not in candidates:
                    candidates.append(symbol)

        return candidates[: max(top_n, min_peers)]

    def _market_cap_tier(self, market_cap_billions: float | None) -> str:
        if market_cap_billions is None:
            return "Tier 3"
        if market_cap_billions >= TIER_RULES["Tier 1"]:
            return "Tier 1"
        if market_cap_billions >= TIER_RULES["Tier 2"]:
            return "Tier 2"
        return "Tier 3"

    def _extract_metrics(self, ticker_symbol: str) -> Dict | None:
        try:
            basic_financials = get_basic_financials(ticker_symbol, timeout=3.0) or {}
            metric = basic_financials.get("metric") if isinstance(basic_financials, dict) else {}
            finnhub_market_cap = metric.get("marketCapitalization")
            market_cap = float(finnhub_market_cap) * 1e6 if finnhub_market_cap else None
            market_cap_billions = _safe_round(market_cap / 1e9, 2) if market_cap else None
            roe = None
            roe_from_finnhub = metric.get("roeTTM")
            if roe_from_finnhub is None:
                roe_from_finnhub = metric.get("roeRfy")
            if roe_from_finnhub is not None:
                try:
                    roe = float(roe_from_finnhub) / 100.0
                except (TypeError, ValueError):
                    roe = None

            needs_yahoo_fallback = any(
                value is None
                for value in (
                    market_cap,
                    metric.get("peTTM"),
                    metric.get("evEbitdaTTM"),
                    metric.get("pbQuarterly"),
                    metric.get("psTTM"),
                    roe,
                )
            )
            info: Dict = {}
            if needs_yahoo_fallback:
                info = get_quote_multiples(yf.Ticker(ticker_symbol), ticker_symbol, ttl_seconds=300)
                if market_cap is None:
                    market_cap = info.get("marketCap")
                    market_cap_billions = _safe_round(market_cap / 1e9, 2) if market_cap else None
                if roe is None:
                    roe = info.get("returnOnEquity")

            metrics = {
                "ticker": ticker_symbol,
                "name": info.get("longName") or info.get("shortName") or ticker_symbol,
                "industry": info.get("industry") or info.get("industryKey"),
                "sector": info.get("sector") or info.get("sectorKey"),
                "market_cap": market_cap,
                "market_cap_billions": market_cap_billions,
                "pe": _safe_round(metric.get("peTTM") or info.get("trailingPE")),
                "ev_ebitda": _safe_round(metric.get("evEbitdaTTM") or info.get("enterpriseToEbitda")),
                "pb": _safe_round(metric.get("pbQuarterly") or info.get("priceToBook")),
                "ev_revenue": _safe_round(metric.get("psTTM") or info.get("enterpriseToRevenue")),
                "roe": roe,
                "tier": self._market_cap_tier(market_cap_billions),
                "source": {
                    "quote_fallback": f"https://finance.yahoo.com/quote/{ticker_symbol}",
                    "metrics_fallback": f"https://finnhub.io/api/v1/stock/metric?symbol={ticker_symbol}&metric=all",
                },
            }
            return metrics
        except (requests.RequestException, TypeError, ValueError, KeyError) as exc:
            logger.warning("[%s] Failed to process peer %s: %s", self.ticker, ticker_symbol, exc)
            return None

    def _passes_filter(self, metrics: Dict) -> Tuple[bool, str]:
        roe = metrics.get("roe")
        market_cap = metrics.get("market_cap") or 0

        if roe is None or roe < FILTER_CONDITIONS["min_roe"]:
            return False, f"Rejected: ROE below {FILTER_CONDITIONS['min_roe']:.0%}."
        if market_cap < FILTER_CONDITIONS["min_market_cap"]:
            return False, "Rejected: Market cap below minimum threshold."
        return True, "Accepted by valuation filter."

    def _score_peer(self, metrics: Dict, target_industry: str, target_sector: str, target_market_cap: float | None) -> Tuple[int, str]:
        peer_market_cap = metrics.get("market_cap") or 0
        ratio = (peer_market_cap / target_market_cap) if target_market_cap and peer_market_cap else 0
        industry_match = metrics.get("industry") == target_industry
        sector_match = metrics.get("sector") == target_sector

        if industry_match and 0.3 <= ratio <= 3.0:
            return 100, "Exact industry match with market cap within 30% to 300%."
        if industry_match:
            return 80, "Exact industry match outside preferred market-cap band."
        if sector_match and 0.2 <= ratio <= 5.0:
            return 60, "Sector match with market cap within 20% to 500%."
        if sector_match:
            return 40, "Sector match used as fallback."
        return 10, "Fallback comparable from curated industry map."

    def find_peers(self, min_peers: int = 6, max_peers: int = 8, max_seconds: float = 8.0) -> List[Dict]:
        started_at = time.monotonic()
        target_industry, target_sector = self._get_company_industry()
        target_market_cap = self.info.get("marketCap")
        if not target_market_cap:
            try:
                target_market_cap = self.stock.fast_info.get("market_cap")
            except (AttributeError, KeyError, TypeError, ValueError) as exc:
                logger.warning("[%s] fast_info market_cap lookup failed: %s", self.ticker, exc)
                target_market_cap = 0
        candidate_tickers = self._get_candidate_tickers(target_industry, target_sector, top_n=max(max_peers + 2, 10), min_peers=min_peers)

        selection_log: List[Dict] = []
        selected: List[Dict] = []

        # A slightly wider pool improves completion odds within the fixed
        # collection budget without overwhelming upstream free-tier APIs.
        max_workers = min(4, max(1, len(candidate_tickers)))
        executor = ThreadPoolExecutor(max_workers=max_workers)
        try:
            future_map = {
                executor.submit(self._extract_metrics, symbol): symbol
                for symbol in candidate_tickers
                if symbol != self.ticker
            }
            pending = set(future_map.keys())

            while pending and time.monotonic() - started_at < max_seconds:
                remaining = max_seconds - (time.monotonic() - started_at)
                done, pending = wait(
                    pending,
                    timeout=max(0.0, remaining),
                    return_when=FIRST_COMPLETED,
                )
                if not done:
                    break

                for future in done:
                    symbol = future_map[future]
                    metrics = future.result()
                    if not metrics:
                        selection_log.append({
                            "ticker": symbol,
                            "company_name": symbol,
                            "tier": "Rejected",
                            "score": 0,
                            "reason": "Rejected: Unable to retrieve financial metrics.",
                        })
                        continue

                    passed, filter_reason = self._passes_filter(metrics)
                    if not passed:
                        selection_log.append({
                            "ticker": symbol,
                            "company_name": metrics["name"],
                            "tier": "Rejected",
                            "score": 0,
                            "reason": filter_reason,
                        })
                        continue

                    score, score_reason = self._score_peer(metrics, target_industry, target_sector, target_market_cap)
                    peer_row = {
                        "ticker": metrics["ticker"],
                        "name": metrics["name"],
                        "match_tier": metrics["tier"],
                        "market_cap_billions": metrics["market_cap_billions"],
                        "market_cap": metrics["market_cap"],
                        "pe": metrics["pe"],
                        "ev_ebitda": metrics["ev_ebitda"],
                        "pb": metrics["pb"],
                        "ev_revenue": metrics["ev_revenue"],
                        "roe": metrics["roe"],
                        "match_score": score,
                        "source": metrics["source"],
                    }
                    selected.append(peer_row)
                    selection_log.append({
                        "ticker": metrics["ticker"],
                        "company_name": metrics["name"],
                        "tier": metrics["tier"],
                        "score": score,
                        "reason": f"{filter_reason} {score_reason}",
                    })

                    if len(selected) >= max_peers:
                        for leftover in pending:
                            leftover.cancel()
                        pending.clear()
                        break

            if pending:
                logger.warning("[%s] Peer collection stopped at %.2fs due to time budget.", self.ticker, max_seconds)
                for leftover in pending:
                    leftover.cancel()
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        selected.sort(key=lambda item: ((item.get("market_cap") or 0), item.get("match_score") or 0), reverse=True)
        selected = selected[:max_peers]
        warning = None
        if len(selected) < min_peers:
            warning = f"Only found {len(selected)} comparable companies after valuation filters. Minimum required is {min_peers}."
            logger.warning("[%s] %s", self.ticker, warning)

        candidate_source = "Curated industry map, then Finnhub peer companies API, then sector fallback"
        if not candidate_tickers:
            candidate_source = "Curated industry and sector fallback maps"

        self.last_run = {
            "target": {
                "ticker": self.ticker,
                "industry": target_industry,
                "sector": target_sector,
                "market_cap": target_market_cap,
            },
            "rules": [
                f"Candidate universe starts with {candidate_source}.",
                "Finnhub provides peer discovery while Yahoo Finance provides comparable multiples and company metrics.",
                f"ROE filter: must be at least {FILTER_CONDITIONS['min_roe']:.0%}.",
                "Tier 1: market cap >= 1000 USD bn, Tier 2: 500 to 999 USD bn, Tier 3: below 500 USD bn.",
                "Target output is 6 to 10 comparable companies with auditable rejection reasons.",
            ],
            "selected_peers": selected,
            "selection_log": selection_log[:100],
            "warning": warning,
        }
        return selected
