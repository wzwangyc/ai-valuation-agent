"""Financial statement extraction and deterministic operating metric assembly."""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf

from data_collection.yahoo_client import (
    get_balance_sheet,
    get_cashflow,
    get_financials,
    get_info,
)


class FinancialStatementsExtractor:
    """Extract statement line items and build finance-safe derived metrics."""

    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.stock = yf.Ticker(self.ticker)
        self._info: Optional[dict] = None
        self.income_stmt = get_financials(self.stock, self.ticker).fillna(0)
        self.balance_sheet = get_balance_sheet(self.stock, self.ticker).fillna(0)
        self.cash_flow = get_cashflow(self.stock, self.ticker).fillna(0)
        self.periods = self.income_stmt.columns.tolist()
        self.ltm_period = self.periods[0] if self.periods else None

    @property
    def info(self) -> dict:
        if self._info is None:
            self._info = get_info(self.stock, self.ticker)
        return self._info

    def _find(self, df: pd.DataFrame, keywords: List[str], mode: str = "all") -> Optional[pd.Series]:
        """
        Fuzzy-match a statement line item.

        mode='all' requires every keyword to appear.
        mode='any' requires at least one keyword to appear.
        """
        if df.empty:
            return None
        for idx in df.index:
            idx_lower = str(idx).lower()
            if mode == "all" and all(keyword.lower() in idx_lower for keyword in keywords):
                return df.loc[idx]
        for idx in df.index:
            idx_lower = str(idx).lower()
            if any(keyword.lower() in idx_lower for keyword in keywords):
                return df.loc[idx]
        return None

    def get_revenue(self) -> Optional[pd.Series]:
        for keywords in [["total", "revenue"], ["revenue"], ["net", "sales"], ["sales"]]:
            result = self._find(self.income_stmt, keywords)
            if result is not None:
                return result
        return None

    def get_ebit(self) -> Optional[pd.Series]:
        """Lookup EBIT directly first, then reconstruct it from NI + tax + interest if needed."""
        for keywords in [["ebit"], ["operating", "income"]]:
            result = self._find(self.income_stmt, keywords)
            if result is not None:
                return result

        net_income = self._find(self.income_stmt, ["net", "income"])
        tax = self._find(self.income_stmt, ["tax", "provision"])
        if tax is None:
            tax = self._find(self.income_stmt, ["income", "tax"])
        interest = self._find(self.income_stmt, ["interest", "expense"])
        if all(item is not None for item in [net_income, tax, interest]):
            return net_income + tax.abs() + interest.abs()
        return None

    def get_net_income(self) -> Optional[pd.Series]:
        return self._find(self.income_stmt, ["net", "income"])

    def get_effective_tax_rate(self) -> float:
        """Three-year average effective tax rate with outlier filtering."""
        ebt = self._find(self.income_stmt, ["pretax", "income"])
        if ebt is None:
            ebt = self._find(self.income_stmt, ["income", "before", "tax"])
        tax = self._find(self.income_stmt, ["tax", "provision"])
        if tax is None:
            tax = self._find(self.income_stmt, ["income", "tax"])
        if ebt is None or tax is None:
            return 0.21

        rates: List[float] = []
        for period in self.periods[:3]:
            if abs(ebt[period]) > 0:
                rate = abs(tax[period]) / abs(ebt[period])
                if 0.05 < rate < 0.45:
                    rates.append(float(rate))
        return float(np.mean(rates)) if rates else 0.21

    def get_depreciation(self) -> Optional[pd.Series]:
        for keywords in [["depreciation", "amortization"], ["depreciation"]]:
            result = self._find(self.cash_flow, keywords)
            if result is not None:
                return result.abs()
        return None

    def get_capex(self) -> Optional[pd.Series]:
        for keywords in [["capital", "expenditure"], ["capex"], ["purchase", "property"]]:
            result = self._find(self.cash_flow, keywords)
            if result is not None:
                return result.abs()
        return None

    def get_working_capital(self) -> Optional[pd.Series]:
        """
        Approximate operating working capital for DCF use.

        Preferred definition:
            operating NWC = (current assets - cash) - (current liabilities - short-term debt)

        Fallback definition:
            receivables + inventory - payables

        Cash and debt are stripped out of the preferred definition because they are financing items,
        while operating working capital should represent reinvestment tied to the core business.
        """
        current_assets = self._find(self.balance_sheet, ["current", "assets"])
        current_liabilities = self._find(self.balance_sheet, ["current", "liabilities"])
        cash = self._find(self.balance_sheet, ["cash"])
        short_term_debt = self._find(self.balance_sheet, ["short", "term", "debt"])
        if short_term_debt is None:
            short_term_debt = self._find(self.balance_sheet, ["current", "debt"])

        if current_assets is not None and current_liabilities is not None:
            operating_assets = current_assets - (cash if cash is not None else 0)
            operating_liabilities = current_liabilities - (
                short_term_debt if short_term_debt is not None else 0
            )
            return operating_assets - operating_liabilities

        receivables = self._find(self.balance_sheet, ["receivable"])
        inventory = self._find(self.balance_sheet, ["inventor"])
        payables = self._find(self.balance_sheet, ["payable"])
        asset_items = [item for item in [receivables, inventory] if item is not None]
        if not asset_items:
            return None
        operating_assets = sum(asset_items)
        operating_liabilities = payables if payables is not None else 0
        return operating_assets - operating_liabilities

    def get_delta_working_capital(self) -> Optional[pd.Series]:
        """
        Compute period-over-period change in operating working capital.

        Positive delta means the company invested more cash into working capital. That must be
        deducted in UFCF under standard CFA / investment-banking DCF convention.
        """
        working_capital = self.get_working_capital()
        if working_capital is None:
            return None

        deltas: Dict = {}
        for idx, period in enumerate(self.periods):
            previous_period = self.periods[idx + 1] if idx + 1 < len(self.periods) else None
            if previous_period is None:
                deltas[period] = 0.0
                continue
            deltas[period] = float(working_capital[period]) - float(working_capital[previous_period])
        return pd.Series(deltas)

    def get_net_debt(self) -> float:
        """Net interest-bearing debt equals total debt minus cash and cash equivalents."""
        total_debt = self._find(self.balance_sheet, ["total", "debt"])
        if total_debt is None:
            short_term = self._find(self.balance_sheet, ["short", "term", "debt"])
            long_term = self._find(self.balance_sheet, ["long", "term", "debt"])
            debt_value = sum(item[self.ltm_period] for item in [short_term, long_term] if item is not None)
        else:
            debt_value = total_debt[self.ltm_period]

        cash = self._find(self.balance_sheet, ["cash"])
        cash_value = cash[self.ltm_period] if cash is not None else 0
        return float(debt_value - cash_value)

    def get_shares_outstanding(self) -> float:
        shares = self.info.get("sharesOutstanding")
        if shares:
            return float(shares)
        statement_shares = self._find(self.balance_sheet, ["shares", "outstanding"])
        if statement_shares is not None:
            return float(statement_shares[self.ltm_period])
        return 1.0

    def get_ufcf(self) -> Optional[pd.Series]:
        """
        Build UFCF using the standard operating cash-flow formula:

            UFCF = EBIT * (1 - tax rate) + D&A - CapEx - Delta operating NWC

        Delta operating NWC is subtracted because an increase in working capital is a cash outflow.
        """
        ebit = self.get_ebit()
        depreciation = self.get_depreciation()
        capex = self.get_capex()
        if any(item is None for item in [ebit, depreciation, capex]):
            return None

        tax_rate = self.get_effective_tax_rate()
        delta_working_capital = self.get_delta_working_capital()
        if delta_working_capital is None:
            delta_working_capital = 0

        return ebit * (1 - tax_rate) + depreciation - delta_working_capital - capex

    def get_financial_summary(self) -> Dict:
        """Return a report-friendly summary anchored to the latest fiscal period."""
        revenue = self.get_revenue()
        ebit = self.get_ebit()
        net_income = self.get_net_income()
        operating_cash_flow = self._find(self.cash_flow, ["operating"])
        capex = self.get_capex()
        depreciation = self.get_depreciation()
        ufcf = self.get_ufcf()
        period = self.ltm_period

        total_debt = self._find(self.balance_sheet, ["total", "debt"])
        if total_debt is None:
            short_term = self._find(self.balance_sheet, ["short", "term", "debt"])
            long_term = self._find(self.balance_sheet, ["long", "term", "debt"])
            total_debt_value = sum(item[self.ltm_period] for item in [short_term, long_term] if item is not None)
        else:
            total_debt_value = total_debt[self.ltm_period]

        return {
            "revenue": float(revenue[period]) if revenue is not None else None,
            "ebit": float(ebit[period]) if ebit is not None else None,
            "net_income": float(net_income[period]) if net_income is not None else None,
            "operating_cash_flow": float(operating_cash_flow[period]) if operating_cash_flow is not None else None,
            "capex": float(capex[period]) if capex is not None else None,
            "depreciation_and_amortization": float(depreciation[period]) if depreciation is not None else None,
            "unlevered_free_cash_flow": float(ufcf[period]) if ufcf is not None else None,
            "total_debt": float(total_debt_value),
            "gross_margin": self.info.get("grossMargins"),
            "operating_margin": self.info.get("operatingMargins"),
            "net_margin": self.info.get("profitMargins"),
            "roe": self.info.get("returnOnEquity"),
            "effective_tax_rate": self.get_effective_tax_rate(),
            "net_debt": self.get_net_debt(),
            "data_source": "Yahoo Finance Financial Statements API",
            "source_url": f"https://finance.yahoo.com/quote/{self.ticker}/financials",
        }
