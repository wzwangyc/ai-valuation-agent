"""
Market Data Collector — 100% yfinance real-time data, zero hardcoded values.
Covers: current price, market cap, P/E, EV/EBITDA, beta, analyst targets, etc.
"""
import yfinance as yf
import pandas as pd
from typing import Dict, Optional

from data_collection.yahoo_client import get_history, get_info


class MarketDataCollector:
    """Dynamically collects all market data from Yahoo Finance API."""

    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.stock = yf.Ticker(self.ticker)
        self._info: Optional[dict] = None

    @property
    def info(self) -> dict:
        if self._info is None:
            self._info = get_info(self.stock, self.ticker)
        return self._info

    def get_current_price(self) -> float:
        """Get real-time current stock price."""
        try:
            hist = get_history(self.stock, self.ticker, period="1d")
            if not hist.empty:
                return float(hist["Close"].iloc[-1])
        except Exception:
            pass
        return float(self.info.get("currentPrice", self.info.get("regularMarketPrice", 0)))

    def get_market_data(self) -> Dict:
        """
        One-stop collection of all Phase-A market data fields.
        Every value is dynamically fetched — zero hardcoded numbers.
        """
        return {
            "ticker": self.ticker,
            "company_name": self.info.get("longName", self.ticker),
            "sector": self.info.get("sector"),
            "industry": self.info.get("industry"),
            "current_price": self.get_current_price(),
            "market_cap": self.info.get("marketCap"),
            "enterprise_value": self.info.get("enterpriseValue"),
            "shares_outstanding": self.info.get("sharesOutstanding"),
            # Valuation multiples — all dynamic
            "pe_trailing": self.info.get("trailingPE"),
            "pe_forward": self.info.get("forwardPE"),
            "ev_ebitda": self.info.get("enterpriseToEbitda"),
            "ev_revenue": self.info.get("enterpriseToRevenue"),
            "price_to_book": self.info.get("priceToBook"),
            "price_to_sales": self.info.get("priceToSalesTrailing12Months"),
            # Risk
            "beta": self.info.get("beta"),
            # Dividends
            "dividend_yield": self.info.get("dividendYield"),
            # 52-week range
            "fifty_two_week_high": self.info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": self.info.get("fiftyTwoWeekLow"),
            # Analyst consensus
            "target_mean_price": self.info.get("targetMeanPrice"),
            "target_high_price": self.info.get("targetHighPrice"),
            "target_low_price": self.info.get("targetLowPrice"),
            "recommendation": self.info.get("recommendationKey"),
            "number_of_analysts": self.info.get("numberOfAnalystOpinions"),
            # Contextual (Phase A)
            "business_summary": self.info.get("longBusinessSummary"),
            # Provenance
            "data_source": "Yahoo Finance Real-Time API (yfinance)",
            "source_url": f"https://finance.yahoo.com/quote/{self.ticker}",
        }

    def get_historical_prices(self, period: str = "5y") -> pd.DataFrame:
        """Historical price data for backtesting (Bonus)."""
        return self.stock.history(period=period)
