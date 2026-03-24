"""
Macro data collector for risk-free rate, inflation, long-term GDP growth, and ERP.

Primary source is live FRED and Damodaran data. If upstream requests fail, the
collector falls back to the most recent locally saved snapshot instead of using
hardcoded financial assumptions.
"""

from __future__ import annotations

import json
import time
from io import StringIO
from pathlib import Path
from typing import Dict

import pandas as pd
import requests
from fredapi import Fred

from data_collection.http_client import HttpClient

MARKET_RISK_PREMIUM_TIMEOUT_SECONDS = 2
MACRO_CACHE_TTL_SECONDS = 3600
DAMODARAN_CTRY_PREM_URL = "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html"
SNAPSHOT_PATH = (
    Path(__file__).resolve().parents[1]
    / "snapshots"
    / "raw_market_data"
    / "MACRO"
    / "macro_summary.json"
)
_HTTP = HttpClient(
    base_headers={"User-Agent": "AI Valuation Terminal research contact@localhost.com"},
    default_timeout=MARKET_RISK_PREMIUM_TIMEOUT_SECONDS,
    max_retries=1,
    backoff_seconds=0.35,
)


class MacroDataCollector:
    """Fetch macroeconomic parameters used by the valuation engine."""

    _summary_cache: Dict | None = None
    _summary_cache_ts: float = 0.0

    def __init__(self, fred_api_key: str):
        self.fred = Fred(api_key=fred_api_key)

    def _save_snapshot(self, summary: Dict) -> None:
        SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    def _load_snapshot(self) -> Dict | None:
        if not SNAPSHOT_PATH.exists():
            return None
        try:
            return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def get_snapshot_summary(self) -> Dict | None:
        """Return the latest persisted macro snapshot without attempting live collection."""
        snapshot = self._load_snapshot()
        if not snapshot:
            return None
        return {**snapshot, "source_mode": "local_snapshot"}

    def get_risk_free_rate(self) -> float:
        """Return the latest 10-year U.S. Treasury yield from FRED (DGS10)."""
        series = self.fred.get_series("DGS10")
        rate = float(series.dropna().iloc[-1]) / 100.0
        if rate <= 0:
            raise ValueError("Risk-free rate from FRED is non-positive.")
        return rate

    def get_long_term_gdp_growth(self) -> float:
        """Return the 20-year nominal GDP CAGR using FRED GDP history."""
        gdp = self.fred.get_series("GDP")
        annual = gdp.resample("YE").last().dropna()
        if len(annual) < 21:
            raise ValueError("GDP series does not have enough annual history.")
        return (float(annual.iloc[-1]) / float(annual.iloc[-21])) ** (1 / 20) - 1

    def get_inflation_rate(self) -> float:
        """Return the latest annual CPI inflation rate from FRED CPIAUCSL."""
        cpi = self.fred.get_series("CPIAUCSL")
        annual = cpi.resample("YE").last().dropna()
        if len(annual) < 2:
            raise ValueError("Inflation series does not have enough annual history.")
        return float(annual.iloc[-1] / annual.iloc[-2] - 1)

    def get_market_risk_premium(self) -> float:
        """Return Damodaran's current U.S. equity risk premium."""
        response = _HTTP.session.get(
            DAMODARAN_CTRY_PREM_URL,
            headers=_HTTP.base_headers,
            timeout=MARKET_RISK_PREMIUM_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        tables = pd.read_html(StringIO(response.text))
        if len(tables) < 2:
            raise ValueError("Damodaran country risk premium table was not found.")

        table = tables[1].copy()
        if table.empty or len(table) < 2:
            raise ValueError("Damodaran country risk premium table is empty.")

        # The published HTML table uses the first data row as column labels.
        header_row = table.iloc[0]
        table = table.iloc[1:].copy()
        table.columns = [str(value).strip() for value in header_row]

        country_col = next((col for col in table.columns if "country" in col.lower()), None)
        erp_col = next(
            (
                col
                for col in table.columns
                if "equity risk" in col.lower() and "premium" in col.lower()
            ),
            None,
        )
        if not country_col or not erp_col:
            raise ValueError("Damodaran country risk premium columns could not be identified.")

        matches = table[table[country_col].astype(str).str.strip().str.lower() == "united states"]
        if matches.empty:
            raise ValueError("Unable to locate the United States row in Damodaran country risk premium data.")

        erp_text = str(matches.iloc[0][erp_col]).strip().replace("%", "")
        erp_value = round(float(erp_text) / 100.0, 4)
        if not 0.02 <= erp_value <= 0.15:
            raise ValueError(f"Parsed United States ERP is outside the expected range: {erp_value:.4f}")
        return erp_value

    def get_macro_summary(self) -> Dict:
        """Return the macro package used by the valuation pipeline."""
        if self.__class__._summary_cache and (
            time.monotonic() - self.__class__._summary_cache_ts
        ) < MACRO_CACHE_TTL_SECONDS:
            return dict(self.__class__._summary_cache)

        try:
            summary = {
                "risk_free_rate": self.get_risk_free_rate(),
                "equity_risk_premium": self.get_market_risk_premium(),
                "long_term_gdp_growth": self.get_long_term_gdp_growth(),
                "inflation_rate": self.get_inflation_rate(),
                "data_source": "Federal Reserve Economic Data (FRED) + Damodaran",
                "source_urls": [
                    "https://fred.stlouisfed.org/series/DGS10",
                    "https://fred.stlouisfed.org/series/GDP",
                    "https://fred.stlouisfed.org/series/CPIAUCSL",
                    "https://pages.stern.nyu.edu/~adamodar/",
                ],
                "source_mode": "live_api",
            }
            self._save_snapshot(summary)
        except (requests.RequestException, RuntimeError, ValueError, OSError):
            summary = self._load_snapshot()
            if not summary:
                raise
            summary = {**summary, "source_mode": "local_snapshot"}

        self.__class__._summary_cache = dict(summary)
        self.__class__._summary_cache_ts = time.monotonic()
        return summary
