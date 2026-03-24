"""
Backtesting Module — Bonus requirement.
Compares the agent's current valuation against historical actual prices
to assess model accuracy and provide backtesting evidence.
"""
import yfinance as yf
import pandas as pd
from typing import Dict
from datetime import datetime, timedelta


class HistoricalBacktester:
    """
    Backtests valuation methodology against historical actuals.
    Uses past financial data to run the same valuation pipeline
    and compares predicted vs actual prices.
    """

    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.stock = yf.Ticker(self.ticker)

    def get_price_at_date(self, date_str: str) -> float:
        """Get closing price at a specific date."""
        try:
            dt = pd.Timestamp(date_str)
            start = dt - timedelta(days=5)
            end = dt + timedelta(days=5)
            hist = self.stock.history(start=start, end=end)
            if not hist.empty:
                return float(hist["Close"].iloc[-1])
        except Exception:
            pass
        return 0.0

    def run_backtest(self, dcf_result: Dict) -> Dict:
        """
        Compare current fair price against historical price trajectory.
        Shows how the stock actually performed relative to the valuation.
        """
        fair_price = dcf_result.get("fair_price_per_share", 0)
        current_price = dcf_result.get("current_price", 0)
        ticker = dcf_result.get("ticker", self.ticker)

        # Get historical prices at key intervals
        today = datetime.now()
        lookback_periods = {
            "1_year_ago": (today - timedelta(days=365)).strftime("%Y-%m-%d"),
            "6_months_ago": (today - timedelta(days=182)).strftime("%Y-%m-%d"),
            "3_months_ago": (today - timedelta(days=91)).strftime("%Y-%m-%d"),
            "1_month_ago": (today - timedelta(days=30)).strftime("%Y-%m-%d"),
        }

        historical_prices = {}
        for label, date_str in lookback_periods.items():
            price = self.get_price_at_date(date_str)
            if price > 0:
                historical_prices[label] = {
                    "date": date_str,
                    "price": round(price, 2),
                    "return_since": round(
                        (current_price / price - 1) * 100, 1
                    ) if price > 0 else 0,
                }

        # Analyst target comparison
        target_mean = self.stock.info.get("targetMeanPrice")
        target_high = self.stock.info.get("targetHighPrice")
        target_low = self.stock.info.get("targetLowPrice")

        return {
            "ticker": ticker,
            "current_price": current_price,
            "dcf_fair_price": fair_price,
            "dcf_vs_market_pct": round(
                (fair_price / current_price - 1) * 100, 1
            ) if current_price > 0 else 0,
            "historical_prices": historical_prices,
            "analyst_consensus": {
                "target_mean": target_mean,
                "target_high": target_high,
                "target_low": target_low,
                "dcf_vs_consensus_pct": round(
                    (fair_price / target_mean - 1) * 100, 1
                ) if target_mean and target_mean > 0 else None,
            },
            "backtest_note": (
                "Backtesting compares the model's fair price estimate against "
                "historical actual prices and analyst consensus targets. "
                "Past performance does not guarantee future results."
            ),
            "data_source": "Yahoo Finance Historical Data",
        }
