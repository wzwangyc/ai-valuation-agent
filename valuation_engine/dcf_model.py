"""
Two-stage UFCF DCF with display-friendly calculation detail output.
"""
from typing import Dict

import numpy as np
import pandas as pd

from data_collection.financial_statements import FinancialStatementsExtractor
from data_collection.macro_data import MacroDataCollector
from valuation_engine.wacc_calculator import WACCCalculator


class DCFModel:
    """Run deterministic DCF and expose all intermediate logic."""

    def __init__(
        self,
        ticker: str,
        macro: MacroDataCollector,
        fin: FinancialStatementsExtractor,
        wacc_calc: WACCCalculator,
        forecast_years: int = 5,
    ):
        self.ticker = ticker.upper()
        self.fin = fin
        self.macro = macro
        self.wacc_data = wacc_calc.calculate()
        self.wacc = self.wacc_data["wacc"]
        self.n = forecast_years
        self.info = fin.stock.info

    def _terminal_growth(self) -> float:
        gdp_growth = self.macro.get_long_term_gdp_growth()
        anchored = max(float(gdp_growth) * 0.9, 0.015)
        bounded = min(anchored, 0.035, self.wacc - 0.01)
        return bounded

    def _growth_schedule(self) -> np.ndarray:
        terminal_growth = self._terminal_growth()
        first_year_growth = self.info.get("revenueGrowth")
        if first_year_growth is None:
            revenue = self.fin.get_revenue()
            if revenue is not None and len(revenue) >= 3:
                latest = float(revenue.iloc[0])
                earlier = float(revenue.iloc[2])
                first_year_growth = (latest / earlier) ** 0.5 - 1 if earlier > 0 else terminal_growth + 0.03
            else:
                first_year_growth = terminal_growth + 0.03
        first_year_growth = float(np.clip(first_year_growth, -0.15, 0.40))
        return np.linspace(first_year_growth, terminal_growth, self.n)

    def _ebit_margin(self) -> float:
        ebit = self.fin.get_ebit()
        revenue = self.fin.get_revenue()
        if ebit is None or revenue is None:
            margin = self.info.get("operatingMargins")
            return float(margin) if margin is not None else 0.15
        margins = []
        for period in self.fin.periods[:3]:
            rev = float(revenue[period])
            if rev == 0:
                continue
            ratio = float(ebit[period]) / rev
            if -0.1 < ratio < 0.6:
                margins.append(ratio)
        return float(np.mean(margins)) if margins else 0.15

    def _operating_ratios(self) -> Dict[str, float]:
        revenue = self.fin.get_revenue()
        depreciation = self.fin.get_depreciation()
        capex = self.fin.get_capex()
        working_capital = self.fin.get_working_capital()
        buckets = {"da": [], "capex": [], "wc": []}
        if revenue is not None:
            for period in self.fin.periods[:3]:
                rev = float(revenue[period])
                if rev == 0:
                    continue
                if depreciation is not None:
                    buckets["da"].append(abs(float(depreciation[period])) / rev)
                if capex is not None:
                    buckets["capex"].append(float(capex[period]) / rev)
                if working_capital is not None:
                    buckets["wc"].append(float(working_capital[period]) / rev)
        return {
            "da_rev": float(np.mean(buckets["da"])) if buckets["da"] else 0.04,
            "capex_rev": float(np.mean(buckets["capex"])) if buckets["capex"] else 0.05,
            "wc_rev": float(np.mean(buckets["wc"])) if buckets["wc"] else 0.10,
        }

    def forecast(self) -> pd.DataFrame:
        growth = self._growth_schedule()
        margin = self._ebit_margin()
        tax_rate = self.fin.get_effective_tax_rate()
        ratios = self._operating_ratios()
        revenue = self.fin.get_revenue()
        base_revenue = float(revenue.iloc[0]) if revenue is not None else 0

        rows = []
        prior_revenue = base_revenue
        for idx in range(self.n):
            # Forecast revenue by applying the year-specific growth assumption to the prior year.
            projected_revenue = prior_revenue * (1 + growth[idx])
            # EBIT is operating income before financing effects and taxes.
            ebit_value = projected_revenue * margin
            # NOPAT converts EBIT into after-tax operating profit for UFCF purposes.
            nopat = ebit_value * (1 - tax_rate)
            # D&A is added back because it is non-cash.
            da_value = projected_revenue * ratios["da_rev"]
            # CapEx is deducted because it represents cash reinvestment into long-lived assets.
            capex_value = projected_revenue * ratios["capex_rev"]
            # Working capital scales with revenue in the base forecast; the period-over-period
            # increase is a cash outflow and must be subtracted from UFCF.
            wc_current = projected_revenue * ratios["wc_rev"]
            wc_previous = prior_revenue * ratios["wc_rev"]
            delta_wc = wc_current - wc_previous
            # Standard UFCF formula:
            # UFCF = NOPAT + D&A - CapEx - Delta NWC
            ufcf = nopat + da_value - delta_wc - capex_value
            rows.append(
                {
                    "Year": idx + 1,
                    "Revenue": projected_revenue,
                    "Revenue_Growth": growth[idx],
                    "EBIT": ebit_value,
                    "EBIT_Margin": margin,
                    "NOPAT": nopat,
                    "DA": da_value,
                    "CapEx": capex_value,
                    "Delta_WC": delta_wc,
                    "UFCF": ufcf,
                }
            )
            prior_revenue = projected_revenue
        return pd.DataFrame(rows).set_index("Year")

    def terminal_value(self, forecast_df: pd.DataFrame) -> Dict:
        terminal_growth = self._terminal_growth()
        last_ufcf = float(forecast_df["UFCF"].iloc[-1])
        last_ebitda = float(forecast_df["EBIT"].iloc[-1] + forecast_df["DA"].iloc[-1])
        # Gordon growth perpetuity using steady-state UFCF.
        tv_gordon = last_ufcf * (1 + terminal_growth) / (self.wacc - terminal_growth)

        company_multiple = self.info.get("enterpriseToEbitda")
        fallback_used = False
        if company_multiple is None or not (1 < company_multiple < 50):
            enterprise_value = self.info.get("enterpriseValue")
            ebitda = self.info.get("ebitda")
            if enterprise_value and ebitda and ebitda > 0:
                company_multiple = enterprise_value / ebitda
            else:
                company_multiple = 12.0
                fallback_used = True

        tv_exit = last_ebitda * company_multiple
        return {
            "tv_gordon": tv_gordon,
            "tv_exit_multiple": tv_exit,
            "exit_multiple_used": company_multiple,
            "terminal_growth": terminal_growth,
            "tv_composite": (tv_gordon + tv_exit) / 2,
            "assumption_audit": {
                "terminal_growth": {
                    "value": terminal_growth,
                    "source": "FRED long-term GDP growth anchor",
                    "fallback_used": False,
                },
                "exit_multiple": {
                    "value": company_multiple,
                    "source": "Yahoo Finance EV/EBITDA" if not fallback_used else "Emergency fallback multiple",
                    "fallback_used": fallback_used,
                },
            },
        }

    def run(self) -> Dict:
        forecast_df = self.forecast()
        terminal = self.terminal_value(forecast_df)

        # Mid-year convention discounts each forecast cash flow by half a year less than
        # end-of-year discounting, which is common in professional DCF practice.
        discount_factors = np.array([1 / (1 + self.wacc) ** (i + 0.5) for i in range(self.n)])
        # Present value of explicit forecast-period UFCF.
        pv_ufcf = float(np.sum(forecast_df["UFCF"].values * discount_factors))
        # Present value of the composite terminal value.
        pv_tv = terminal["tv_composite"] / (1 + self.wacc) ** self.n
        # Enterprise value is the value of operating assets before financing claims.
        enterprise_value = pv_ufcf + pv_tv
        net_debt = self.fin.get_net_debt()
        # Equity value is enterprise value less net debt.
        equity_value = enterprise_value - net_debt
        shares = self.fin.get_shares_outstanding()
        # Intrinsic value per share is equity value divided by diluted shares outstanding.
        fair_price = equity_value / shares if shares > 0 else 0
        current_price = float(self.info.get("currentPrice", self.info.get("regularMarketPrice", 0)) or 0)
        upside = ((fair_price / current_price) - 1) * 100 if current_price > 0 else 0

        terminal_high = terminal["tv_composite"] * 1.15
        terminal_low = terminal["tv_composite"] * 0.85
        fair_price_high = ((pv_ufcf + terminal_high / (1 + self.wacc) ** self.n) - net_debt) / shares if shares > 0 else 0
        fair_price_low = ((pv_ufcf + terminal_low / (1 + self.wacc) ** self.n) - net_debt) / shares if shares > 0 else 0

        return {
            "ticker": self.ticker,
            "company_name": self.info.get("longName", self.ticker),
            "valuation_method": "Two-Stage Unlevered FCF DCF (Mid-Year Convention)",
            "fair_price_per_share": round(fair_price, 2),
            "valuation_range": [round(min(fair_price_low, fair_price_high), 2), round(max(fair_price_low, fair_price_high), 2)],
            "current_price": round(current_price, 2),
            "upside_downside_pct": round(upside, 1),
            "enterprise_value": round(enterprise_value, 0),
            "equity_value": round(equity_value, 0),
            "pv_explicit_fcf": round(pv_ufcf, 0),
            "pv_terminal_value": round(pv_tv, 0),
            "tv_as_pct_of_ev": round(pv_tv / enterprise_value * 100, 1) if enterprise_value > 0 else 0,
            "net_debt": round(net_debt, 0),
            "shares_outstanding": shares,
            "wacc_details": self.wacc_data,
            "terminal_value_details": terminal,
            "forecast_table": forecast_df.to_dict(),
            "key_assumptions": {
                "forecast_years": self.n,
                "revenue_growth_schedule": self._growth_schedule().tolist(),
                "ebit_margin": self._ebit_margin(),
                "operating_ratios": self._operating_ratios(),
                "terminal_growth_rate": self._terminal_growth(),
                "exit_multiple": terminal["exit_multiple_used"],
            },
            "calculation_trace": {
                "formulae": [
                    "Revenue_t = Revenue_(t-1) * (1 + growth_t)",
                    "EBIT_t = Revenue_t * EBIT Margin",
                    "NOPAT_t = EBIT_t * (1 - tax_rate)",
                    "UFCF_t = NOPAT_t + D&A_t - CapEx_t - Delta Working Capital_t",
                    "Enterprise Value = PV(UFCF) + PV(Terminal Value)",
                ],
                "discount_factors": [round(x, 6) for x in discount_factors.tolist()],
            },
            "data_sources": [
                "Yahoo Finance (Market Data, Financials, Analyst Estimates)",
                "FRED (Risk-Free Rate, GDP Growth)",
                "Damodaran (Equity Risk Premium)",
            ],
            "methodology_note": "All calculations are deterministic Python. LLM is not used for arithmetic.",
        }
