"""
WACC calculator with explicit assumption audit metadata.
"""
from typing import Dict

from data_collection.financial_statements import FinancialStatementsExtractor
from data_collection.macro_data import MacroDataCollector


class WACCCalculator:
    """Compute WACC and expose the internal mechanics for the frontend."""

    def __init__(self, ticker: str, macro: MacroDataCollector, fin: FinancialStatementsExtractor):
        self.ticker = ticker.upper()
        self.macro = macro
        self.fin = fin
        self.info = fin.info

    def get_beta(self) -> float:
        beta = self.info.get("beta")
        if beta and 0.1 < beta < 5.0:
            return float(beta)
        return 1.0

    def get_cost_of_equity(self) -> Dict[str, float]:
        rf = self.macro.get_risk_free_rate()
        beta = self.get_beta()
        erp = self.macro.get_market_risk_premium()
        re = max(rf + beta * erp, rf + 0.02)
        return {"re": re, "rf": rf, "beta": beta, "erp": erp}

    def get_cost_of_debt(self) -> float:
        int_exp = self.fin._find(self.fin.income_stmt, ["interest", "expense"])
        total_debt = self.fin._find(self.fin.balance_sheet, ["total", "debt"])
        rf = self.macro.get_risk_free_rate()
        if int_exp is not None and total_debt is not None:
            ie = abs(float(int_exp[self.fin.ltm_period]))
            td = abs(float(total_debt[self.fin.ltm_period]))
            if td > 0 and ie > 0:
                rd = ie / td
                return rd if rd > rf else rf + 0.015
        return rf + 0.02

    def get_capital_structure(self) -> Dict[str, float]:
        market_cap = self.info.get("marketCap", 0)
        net_debt = max(self.fin.get_net_debt(), 0)
        total_value = market_cap + net_debt if market_cap else 1
        return {
            "market_cap": market_cap,
            "net_debt": net_debt,
            "equity_weight": market_cap / total_value if market_cap else 1.0,
            "debt_weight": net_debt / total_value,
        }

    def calculate(self) -> Dict[str, float]:
        equity = self.get_cost_of_equity()
        rd = self.get_cost_of_debt()
        tax_rate = self.fin.get_effective_tax_rate()
        cap = self.get_capital_structure()

        wacc = cap["equity_weight"] * equity["re"] + cap["debt_weight"] * rd * (1 - tax_rate)
        wacc = max(wacc, equity["rf"] + 0.02)
        wacc = min(wacc, 0.20)

        return {
            "wacc": round(wacc, 6),
            "cost_of_equity": round(equity["re"], 6),
            "cost_of_debt": round(rd, 6),
            "risk_free_rate": round(equity["rf"], 6),
            "beta": round(equity["beta"], 4),
            "equity_risk_premium": round(equity["erp"], 6),
            "effective_tax_rate": round(tax_rate, 4),
            "equity_weight": round(cap["equity_weight"], 4),
            "debt_weight": round(cap["debt_weight"], 4),
            "market_cap": cap["market_cap"],
            "net_debt": cap["net_debt"],
            "formula": "WACC = (E/V)*Re + (D/V)*Rd*(1-Tc); Re = Rf + Beta*ERP",
            "assumption_audit": {
                "beta": {
                    "value": round(equity["beta"], 4),
                    "source": "Yahoo Finance beta" if self.info.get("beta") else "Fallback market beta",
                    "fallback_used": self.info.get("beta") is None,
                },
                "cost_of_debt": {
                    "value": round(rd, 6),
                    "source": "Interest expense / total debt" if self.fin._find(self.fin.income_stmt, ["interest", "expense"]) is not None else "Fallback spread over risk-free rate",
                    "fallback_used": self.fin._find(self.fin.income_stmt, ["interest", "expense"]) is None,
                },
                "capital_structure": {
                    "equity_weight": round(cap["equity_weight"], 4),
                    "debt_weight": round(cap["debt_weight"], 4),
                    "source": "Yahoo Finance market cap and extracted net debt",
                    "fallback_used": not bool(cap["market_cap"]),
                },
            },
            "data_sources": [
                "FRED DGS10 (Risk-Free Rate)",
                "Damodaran / FRED (ERP)",
                "Yahoo Finance (Beta, Market Cap, Debt)",
                "Company Financials (Tax Rate, Interest Expense)",
            ],
        }
