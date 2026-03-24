"""Validation gates for raw collected inputs before they enter valuation logic."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


def _safe_float(value: Any) -> float | None:
    if _is_missing(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class CollectedDataValidator:
    """Validate market and financial inputs before valuation consumes them."""

    def __init__(self, ticker: str, market_data: Dict[str, Any], financial_summary: Dict[str, Any], macro_data: Dict[str, Any]):
        self.ticker = ticker.upper()
        self.market_data = market_data or {}
        self.financial_summary = financial_summary or {}
        self.macro_data = macro_data or {}

    def _market_rules(self) -> List[Tuple[str, bool, str]]:
        current_price = _safe_float(self.market_data.get("current_price"))
        market_cap = _safe_float(self.market_data.get("market_cap"))
        shares = _safe_float(self.market_data.get("shares_outstanding"))
        beta = _safe_float(self.market_data.get("beta"))
        return [
            ("Current price must be present and positive.", current_price is not None and current_price > 0, f"current_price={current_price}"),
            ("Market capitalization must be present and positive.", market_cap is not None and market_cap > 0, f"market_cap={market_cap}"),
            ("Shares outstanding must be present and positive.", shares is not None and shares > 0, f"shares_outstanding={shares}"),
            ("Beta must be within a reasonable range.", beta is None or 0 <= beta <= 5, f"beta={beta}"),
        ]

    def _financial_rules(self) -> List[Tuple[str, bool, str]]:
        revenue = _safe_float(self.financial_summary.get("revenue"))
        ebit = _safe_float(self.financial_summary.get("ebit"))
        ocf = _safe_float(self.financial_summary.get("operating_cash_flow"))
        capex = _safe_float(self.financial_summary.get("capex"))
        tax_rate = _safe_float(self.financial_summary.get("effective_tax_rate"))
        return [
            ("Revenue must be present and positive.", revenue is not None and revenue > 0, f"revenue={revenue}"),
            ("EBIT must be present.", ebit is not None, f"ebit={ebit}"),
            ("Operating cash flow must be present.", ocf is not None, f"operating_cash_flow={ocf}"),
            ("CapEx must be present.", capex is not None, f"capex={capex}"),
            ("Effective tax rate must be between 0% and 50%.", tax_rate is not None and 0 <= tax_rate <= 0.5, f"effective_tax_rate={tax_rate}"),
        ]

    def _macro_rules(self) -> List[Tuple[str, bool, str]]:
        risk_free = _safe_float(self.macro_data.get("risk_free_rate"))
        inflation = _safe_float(self.macro_data.get("inflation_rate"))
        terminal_anchor = _safe_float(self.macro_data.get("terminal_growth_anchor"))
        return [
            ("Risk-free rate must be present and non-negative.", risk_free is not None and risk_free >= 0, f"risk_free_rate={risk_free}"),
            ("Inflation rate must be present and bounded.", inflation is not None and -0.05 <= inflation <= 0.2, f"inflation_rate={inflation}"),
            ("Terminal growth anchor must be present and bounded.", terminal_anchor is not None and 0 <= terminal_anchor <= 0.08, f"terminal_growth_anchor={terminal_anchor}"),
        ]

    def run(self) -> Dict[str, Any]:
        rule_rows = []
        errors: List[str] = []

        for scope, rules in (
            ("market_data", self._market_rules()),
            ("financial_summary", self._financial_rules()),
            ("macro_data", self._macro_rules()),
        ):
            for rule, passed, detail in rules:
                row = {
                    "scope": scope,
                    "rule": rule,
                    "passed": passed,
                    "detail": detail,
                }
                rule_rows.append(row)
                if not passed:
                    errors.append(f"{scope}: {rule} {detail}")

        return {
            "passed": not errors,
            "rules": rule_rows,
            "errors": errors,
        }
