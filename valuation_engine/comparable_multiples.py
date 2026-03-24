"""
Comparable company valuation for Phase B cross-checking.

The implementation avoids fixed cutoffs such as "P/E < 100" or
"EV/EBITDA < 50". Instead, it keeps positive values and trims outliers using an
interquartile-range filter when enough peers are available.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np


class ComparableMultiples:
    """Peer-based valuation using traceable market multiples."""

    def __init__(self, ticker: str, peers: List[Dict], company_info: dict):
        self.ticker = ticker.upper()
        self.peers = peers
        self.info = company_info

    def _get_first(self, *keys, default=None):
        for key in keys:
            value = self.info.get(key)
            if value is not None:
                return value
        return default

    def _clean_positive_multiples(self, values: List[float]) -> List[float]:
        cleaned: List[float] = []
        for value in values:
            if value is None:
                continue
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                continue
            if numeric > 0:
                cleaned.append(numeric)

        if len(cleaned) < 4:
            return cleaned

        q1 = float(np.percentile(cleaned, 25))
        q3 = float(np.percentile(cleaned, 75))
        iqr = q3 - q1
        lower = max(0.0, q1 - 1.5 * iqr)
        upper = q3 + 1.5 * iqr
        trimmed = [value for value in cleaned if lower <= value <= upper]
        return trimmed or cleaned

    def calculate(self) -> Dict:
        """
        Comparable-multiples valuation:
        1. P/E method: peer median P/E times company EPS
        2. EV/EBITDA method: peer median EV/EBITDA times company EBITDA
        """
        pe_vals = self._clean_positive_multiples([peer.get("pe") for peer in self.peers])
        ev_vals = self._clean_positive_multiples([peer.get("ev_ebitda") for peer in self.peers])

        result = {
            "ticker": self.ticker,
            "valuation_method": "Comparable Company Multiples (P/E + EV/EBITDA)",
            "peer_count": len(self.peers),
        }

        if pe_vals:
            median_pe = float(np.median(pe_vals))
            eps = self._get_first("trailingEps", default=0)
            if eps and eps > 0:
                result["pe_fair_price"] = round(median_pe * eps, 2)
                result["peer_median_pe"] = round(median_pe, 2)
                result["company_eps"] = round(float(eps), 2)

        if ev_vals:
            median_ev = float(np.median(ev_vals))
            ebitda = self._get_first("ebitda", default=0)
            shares = self._get_first("sharesOutstanding", "shares_outstanding", default=1)
            ev = self._get_first("enterpriseValue", "enterprise_value", default=0)
            mcap = self._get_first("marketCap", "market_cap", default=0)
            net_debt_approx = ev - mcap if ev and mcap else 0
            if ebitda and ebitda > 0 and shares:
                implied_ev = median_ev * ebitda
                equity_value = implied_ev - net_debt_approx
                result["ev_ebitda_fair_price"] = round(equity_value / shares, 2)
                result["peer_median_ev_ebitda"] = round(median_ev, 2)
                result["company_ebitda"] = ebitda

        fair_prices = []
        if "pe_fair_price" in result:
            fair_prices.append(result["pe_fair_price"])
        if "ev_ebitda_fair_price" in result:
            fair_prices.append(result["ev_ebitda_fair_price"])
        result["composite_fair_price"] = round(float(np.mean(fair_prices)), 2) if fair_prices else None

        range_lows = []
        range_highs = []
        eps = self._get_first("trailingEps", default=0)
        if pe_vals and eps:
            pe_25 = float(np.percentile(pe_vals, 25))
            pe_75 = float(np.percentile(pe_vals, 75))
            range_lows.append(pe_25 * eps)
            range_highs.append(pe_75 * eps)

        ebitda = self._get_first("ebitda", default=0)
        shares = self._get_first("sharesOutstanding", "shares_outstanding", default=1)
        ev = self._get_first("enterpriseValue", "enterprise_value", default=0)
        mcap = self._get_first("marketCap", "market_cap", default=0)
        net_debt_approx = ev - mcap if ev and mcap else 0
        if ev_vals and ebitda and shares:
            ev_25 = float(np.percentile(ev_vals, 25))
            ev_75 = float(np.percentile(ev_vals, 75))
            range_lows.append((ev_25 * ebitda - net_debt_approx) / shares)
            range_highs.append((ev_75 * ebitda - net_debt_approx) / shares)

        if range_lows and range_highs:
            result["valuation_range"] = [
                round(float(np.mean(range_lows)), 2),
                round(float(np.mean(range_highs)), 2),
            ]
        else:
            result["valuation_range"] = [result["composite_fair_price"], result["composite_fair_price"]]

        current_price = self._get_first("currentPrice", "regularMarketPrice", "current_price", default=0)
        result["current_price"] = current_price
        if result["composite_fair_price"] and current_price:
            result["upside_downside_pct"] = round((result["composite_fair_price"] / current_price - 1) * 100, 1)

        result["peer_details"] = [
            {
                "ticker": peer["ticker"],
                "name": peer.get("name"),
                "pe": peer.get("pe"),
                "ev_ebitda": peer.get("ev_ebitda"),
                "pb": peer.get("pb"),
                "ev_revenue": peer.get("ev_revenue"),
                "match_tier": peer.get("match_tier"),
                "match_score": peer.get("match_score"),
            }
            for peer in self.peers
        ]

        pb_vals = self._clean_positive_multiples([peer.get("pb") for peer in self.peers])
        ev_sales_vals = self._clean_positive_multiples([peer.get("ev_revenue") for peer in self.peers])
        roe_vals = self._clean_positive_multiples([peer.get("roe") for peer in self.peers])

        result["peer_statistics"] = {
            "median_pe": round(float(np.median(pe_vals)), 2) if pe_vals else None,
            "mean_pe": round(float(np.mean(pe_vals)), 2) if pe_vals else None,
            "median_ev_ebitda": round(float(np.median(ev_vals)), 2) if ev_vals else None,
            "mean_ev_ebitda": round(float(np.mean(ev_vals)), 2) if ev_vals else None,
            "mean_pb": round(float(np.mean(pb_vals)), 2) if pb_vals else None,
            "mean_ev_sales": round(float(np.mean(ev_sales_vals)), 2) if ev_sales_vals else None,
            "mean_roe": round(float(np.mean(roe_vals)), 4) if roe_vals else None,
        }

        result["target_metrics"] = {
            "ticker": self.ticker,
            "name": self._get_first("longName", "shortName", "company_name", default=self.ticker),
            "market_cap_billions": round((self._get_first("marketCap", "market_cap", default=0) or 0) / 1e9, 2)
            if self._get_first("marketCap", "market_cap")
            else None,
            "pe": round(float(self._get_first("trailingPE", "pe_trailing")), 2)
            if self._get_first("trailingPE", "pe_trailing")
            else None,
            "ev_ebitda": round(float(self._get_first("enterpriseToEbitda", "ev_ebitda")), 2)
            if self._get_first("enterpriseToEbitda", "ev_ebitda")
            else None,
            "pb": round(float(self._get_first("priceToBook", "price_to_book")), 2)
            if self._get_first("priceToBook", "price_to_book")
            else None,
            "ev_revenue": round(float(self._get_first("enterpriseToRevenue", "ev_revenue")), 2)
            if self._get_first("enterpriseToRevenue", "ev_revenue")
            else None,
            "roe": round(float(self._get_first("returnOnEquity", "roe")), 4)
            if self._get_first("returnOnEquity", "roe") is not None
            else None,
            "match_tier": "Current Company",
            "match_score": 100,
        }

        result["comparison_vs_peer_stats"] = {
            "pe_vs_median_pct": round((result["target_metrics"]["pe"] / result["peer_statistics"]["median_pe"] - 1) * 100, 1)
            if result["target_metrics"].get("pe") and result["peer_statistics"].get("median_pe")
            else None,
            "ev_ebitda_vs_median_pct": round(
                (result["target_metrics"]["ev_ebitda"] / result["peer_statistics"]["median_ev_ebitda"] - 1) * 100, 1
            )
            if result["target_metrics"].get("ev_ebitda") and result["peer_statistics"].get("median_ev_ebitda")
            else None,
            "pb_vs_peer_mean_pct": round((result["target_metrics"]["pb"] / result["peer_statistics"]["mean_pb"] - 1) * 100, 1)
            if result["target_metrics"].get("pb") and result["peer_statistics"].get("mean_pb")
            else None,
            "ev_sales_vs_peer_mean_pct": round(
                (result["target_metrics"]["ev_revenue"] / result["peer_statistics"]["mean_ev_sales"] - 1) * 100, 1
            )
            if result["target_metrics"].get("ev_revenue") and result["peer_statistics"].get("mean_ev_sales")
            else None,
            "roe_vs_peer_mean_pct": round((result["target_metrics"]["roe"] / result["peer_statistics"]["mean_roe"] - 1) * 100, 1)
            if result["target_metrics"].get("roe") is not None and result["peer_statistics"].get("mean_roe")
            else None,
        }

        result["data_source"] = "Finnhub basic financial metrics with Yahoo Finance fallback for missing quote fields"
        return result
