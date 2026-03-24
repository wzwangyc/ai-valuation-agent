"""
Structured report builder for the AI Valuation Agent.

The output contract is intentionally rich so the same object can power:
1. the report agent view,
2. JSON / Markdown downloads,
3. the TradingView-style frontend,
4. the RAG chat agent retrieval corpus.
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional


def _safe_number(value: Any, digits: int = 2) -> Optional[float]:
    if value is None:
        return None
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def _metric(label: str, value: Any, source: str, citation: str, unit: str = "USD") -> Dict[str, Any]:
    return {
        "label": label,
        "value": value,
        "unit": unit,
        "source": {
            "provider": source,
            "citation": citation,
        },
    }


class MemoBuilder:
    """Build a demo-ready, audit-friendly valuation report."""

    def __init__(
        self,
        ticker: str,
        dcf_result: Dict,
        comparable_result: Dict = None,
        peer_analysis: Dict = None,
        validation_result: Dict = None,
        market_data: Dict = None,
        financial_summary: Dict = None,
        news_data: Dict = None,
        context_data: Dict = None,
        sensitivity_data: Dict = None,
        backtesting_data: Dict = None,
        llm_critique: str = None,
        pipeline_errors: List[str] = None,
    ):
        self.ticker = ticker.upper()
        self.dcf = dcf_result or {}
        self.comp = comparable_result or {}
        self.peer_analysis = peer_analysis or {}
        self.valid = validation_result or {}
        self.market = market_data or {}
        self.fin = financial_summary or {}
        self.news = news_data or {}
        self.context = context_data or {}
        self.sensitivity = sensitivity_data or {}
        self.backtest = backtesting_data or {}
        self.llm_critique = llm_critique or ""
        self.pipeline_errors = pipeline_errors or []
        self.generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _status_for_module(self, name: str, has_data: bool, note: str = "") -> Dict[str, Any]:
        matched_errors = [err for err in self.pipeline_errors if name.lower() in err.lower()]
        if has_data and not matched_errors:
            return {"module": name, "status": "Primary API", "note": note or "Live API data loaded successfully."}
        if has_data and matched_errors:
            return {"module": name, "status": "Fallback Used", "note": matched_errors[0]}
        if matched_errors:
            return {"module": name, "status": "Timed Out", "note": matched_errors[0]}
        return {"module": name, "status": "Unavailable", "note": note or "No data returned for this module."}

    def _data_availability(self) -> Dict[str, Any]:
        modules = [
            self._status_for_module("Market", bool(self.market), "Quote, price history, and market profile."),
            self._status_for_module("Financials", bool(self.fin), "Income statement, balance sheet, and cash flow anchors."),
            self._status_for_module("Macro", bool(self.dcf.get("wacc_details")), "Risk-free rate, ERP, GDP growth, and inflation inputs."),
            self._status_for_module("News", bool((self.context.get("recent_news") or self.news.get("recent_news") or [])), "Recent news and headlines for qualitative context."),
            self._status_for_module("Context", bool(self.context.get("filing_excerpts") or self.context.get("call_excerpts")), "Filing excerpts and contextual evidence."),
            self._status_for_module("Peers", bool(self.peer_analysis.get("selected_peers") or self.comp.get("peer_count")), "Comparable company screen and peer statistics."),
        ]
        return {
            "collection_budget_seconds": 10,
            "modules": modules,
            "errors": self.pipeline_errors,
        }

    def _valuation_range(self) -> Dict[str, Optional[float]]:
        dcf_price = _safe_number(self.dcf.get("fair_price_per_share"))
        comp_price = _safe_number(self.comp.get("composite_fair_price"))
        prices = [p for p in [dcf_price, comp_price] if p and p > 0]
        if not prices:
            return {"low": None, "mid": None, "high": None}
        return {
            "low": round(min(prices) * 0.92, 2),
            "mid": round(sum(prices) / len(prices), 2),
            "high": round(max(prices) * 1.08, 2),
        }

    def _forecast_rows(self) -> List[Dict[str, Any]]:
        table = self.dcf.get("forecast_table", {}) or {}
        if not table:
            return []
        years = sorted({int(year) for metric in table.values() for year in metric.keys()})
        rows = []
        for year in years:
            rows.append(
                {
                    "year": year,
                    "revenue": _safe_number(table.get("Revenue", {}).get(year), 0),
                    "growth": _safe_number(table.get("Revenue_Growth", {}).get(year), 4),
                    "ebit": _safe_number(table.get("EBIT", {}).get(year), 0),
                    "ebit_margin": _safe_number(table.get("EBIT_Margin", {}).get(year), 4),
                    "nopat": _safe_number(table.get("NOPAT", {}).get(year), 0),
                    "da": _safe_number(table.get("DA", {}).get(year), 0),
                    "capex": _safe_number(table.get("CapEx", {}).get(year), 0),
                    "delta_wc": _safe_number(table.get("Delta_WC", {}).get(year), 0),
                    "ufcf": _safe_number(table.get("UFCF", {}).get(year), 0),
                }
            )
        return rows

    def _discount_schedule(self, forecast_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        wacc = float(self.dcf.get("wacc_details", {}).get("wacc", 0) or 0)
        schedule = []
        for idx, row in enumerate(forecast_rows, start=1):
            factor = 1 / ((1 + wacc) ** (idx - 0.5)) if wacc > -1 else None
            schedule.append(
                {
                    "year": row["year"],
                    "mid_year_exponent": round(idx - 0.5, 2),
                    "discount_factor": _safe_number(factor, 6),
                    "discounted_ufcf": _safe_number((row["ufcf"] or 0) * (factor or 0), 0),
                }
            )
        return schedule

    def _company_info(self) -> Dict[str, Any]:
        desc = self.context.get("business_description", {}) or {}
        return {
            "ticker": self.ticker,
            "name": self.market.get("company_name") or self.dcf.get("company_name") or self.ticker,
            "sector": self.market.get("sector"),
            "industry": self.market.get("industry"),
            "price": _safe_number(self.market.get("current_price")),
            "market_cap": _safe_number(self.market.get("market_cap"), 0),
            "enterprise_value": _safe_number(self.market.get("enterprise_value"), 0),
            "shares_outstanding": _safe_number(self.market.get("shares_outstanding"), 0),
            "summary": self.market.get("business_summary") or desc.get("description"),
            "business_description": {
                "text": desc.get("description") or self.market.get("business_summary"),
                "positioning": desc.get("industry_positioning"),
                "source": {
                    "provider": "Yahoo Finance Profile",
                    "citation": desc.get("source_url") or self.market.get("source_url"),
                    "timestamp": desc.get("timestamp"),
                },
            },
        }

    def _market_snapshot(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.market.get("company_name") or self._company_info().get("name"),
            "current_price": _safe_number(self.market.get("current_price")),
            "market_cap_billions": _safe_number((self.market.get("market_cap") or 0) / 1e9, 2) if self.market.get("market_cap") else None,
            "pe_trailing": _safe_number(self.market.get("pe_trailing")),
            "ev_ebitda": _safe_number(self.market.get("ev_ebitda")),
            "price_to_book": _safe_number(self.market.get("price_to_book")),
            "ev_revenue": _safe_number(self.market.get("ev_revenue")),
            "roe": _safe_number(self.fin.get("roe"), 4),
            "source_url": self.market.get("source_url"),
        }

    def _financial_cards(self) -> List[Dict[str, Any]]:
        source = self.fin.get("data_source", "Yahoo Finance Financial Statements API")
        citation = self.fin.get("source_url", f"https://finance.yahoo.com/quote/{self.ticker}/financials")
        return [
            _metric("Revenue (LTM)", _safe_number(self.fin.get("revenue"), 0), source, citation),
            _metric("EBIT (LTM)", _safe_number(self.fin.get("ebit"), 0), source, citation),
            _metric("Net Income (LTM)", _safe_number(self.fin.get("net_income"), 0), source, citation),
            _metric("Operating Cash Flow", _safe_number(self.fin.get("operating_cash_flow"), 0), source, citation),
            _metric("CapEx", _safe_number(self.fin.get("capex"), 0), source, citation),
            _metric("Unlevered FCF", _safe_number(self.fin.get("unlevered_free_cash_flow"), 0), source, citation),
            _metric("Net Debt", _safe_number(self.fin.get("net_debt"), 0), source, citation),
            _metric("Gross Margin", _safe_number(self.fin.get("gross_margin"), 4), source, citation, unit="ratio"),
            _metric("Operating Margin", _safe_number(self.fin.get("operating_margin"), 4), source, citation, unit="ratio"),
            _metric("ROE", _safe_number(self.fin.get("roe"), 4), source, citation, unit="ratio"),
        ]

    def _contextual_data(self) -> Dict[str, Any]:
        news_items = self.context.get("recent_news") or self.news.get("recent_news") or []
        business_description = self.context.get("business_description", {}) or {}
        return {
            "business_description": business_description,
            "recent_news": news_items,
            "call_excerpts": self.context.get("call_excerpts", []),
            "filing_excerpts": self.context.get("filing_excerpts", []),
            "news_sentiment": self.news.get("sentiment_analysis"),
        }

    def _validation_agents(self) -> Dict[str, Any]:
        issues = self.valid.get("validation_issues", [])
        risks = self.valid.get("risk_factors", [])
        evidence_audit = self.valid.get("evidence_audit", [])
        uncertainty_flags = []
        if self.market.get("beta") in [None, 1.0]:
            uncertainty_flags.append("Beta may be using a fallback or market-average proxy.")
        if not self.context.get("recent_news"):
            uncertainty_flags.append("Recent news coverage is sparse; qualitative evidence depth is limited.")
        if not self.comp or self.comp.get("peer_count", 0) < 6:
            uncertainty_flags.append("Peer set is thinner than target depth, so comparable valuation has lower confidence.")
        return {
            "confidence_score": self.valid.get("confidence_score"),
            "confidence_label": self.valid.get("confidence_label"),
            "inconsistency_agent": {
                "title": "Inconsistency Detection",
                "goal": "Flag impossible or conflicting values such as broken DCF math, impossible margins, or insufficient peers.",
                "findings": issues,
            },
            "evidence_audit_agent": {
                "title": "Evidence Audit",
                "goal": "Verify that quantitative conclusions are supported by cited financial and contextual evidence.",
                "findings": evidence_audit,
            },
            "uncertainty_agent": {
                "title": "Uncertainty Flagging",
                "goal": "Highlight fallback assumptions, sparse evidence, and low-confidence areas for the interviewer.",
                "findings": uncertainty_flags + risks,
            },
            "rule_results": self.valid.get("rules", []),
            "evidence_mapping": self.valid.get("evidence_mapping", []),
            "confidence_breakdown": self.valid.get("confidence_breakdown", []),
            "critic_summary": self.valid.get("critique_comments"),
            "llm_critic": self.llm_critique or None,
        }

    def _report_agent(self) -> Dict[str, Any]:
        val_range = self._valuation_range()
        dcf_price = _safe_number(self.dcf.get("fair_price_per_share"))
        comp_price = _safe_number(self.comp.get("composite_fair_price"))
        return {
            "module": "Report Agent",
            "summary": {
                "target_price": dcf_price,
                "valuation_range": val_range,
                "current_price": _safe_number(self.dcf.get("current_price") or self.market.get("current_price")),
                "upside_downside_pct": _safe_number(self.dcf.get("upside_downside_pct"), 1),
                "confidence_score": self.valid.get("confidence_score"),
            },
            "core_assumptions": {
                "wacc": _safe_number(self.dcf.get("wacc_details", {}).get("wacc"), 6),
                "risk_free_rate": _safe_number(self.dcf.get("wacc_details", {}).get("risk_free_rate"), 6),
                "equity_risk_premium": _safe_number(self.dcf.get("wacc_details", {}).get("equity_risk_premium"), 6),
                "cost_of_equity": _safe_number(self.dcf.get("wacc_details", {}).get("cost_of_equity"), 6),
                "cost_of_debt": _safe_number(self.dcf.get("wacc_details", {}).get("cost_of_debt"), 6),
                "terminal_growth_rate": _safe_number(self.dcf.get("terminal_value_details", {}).get("terminal_growth"), 6),
                "exit_multiple": _safe_number(self.dcf.get("terminal_value_details", {}).get("exit_multiple_used"), 2),
                "forecast_years": self.dcf.get("key_assumptions", {}).get("forecast_years"),
            },
            "methods": {
                "dcf": {
                    "fair_price": dcf_price,
                    "value_range": self.dcf.get("valuation_range"),
                },
                "comparable_multiples": {
                    "fair_price": comp_price,
                    "value_range": self.comp.get("valuation_range"),
                    "peer_count": self.comp.get("peer_count"),
                },
                "analyst_narrative": {
                    "thesis": self.valid.get("critique_comments"),
                    "risk_factors": self.valid.get("risk_factors", []),
                    "mapping_note": "Qualitative evidence is converted into growth, margin, and risk assumptions through deterministic report synthesis.",
                },
            },
        }

    def _calculation_details(self) -> Dict[str, Any]:
        forecast_rows = self._forecast_rows()
        return {
            "module": "Calculation Details",
            "headline": "Detailed DCF mechanics",
            "formulae": [
                "Revenue_t = Revenue_(t-1) * (1 + growth_t)",
                "EBIT_t = Revenue_t * EBIT Margin",
                "NOPAT_t = EBIT_t * (1 - Tax Rate)",
                "UFCF_t = NOPAT_t + D&A_t - CapEx_t - Delta Working Capital_t",
                "EV = Sum(PV of UFCF) + PV of Terminal Value",
                "Equity Value = Enterprise Value - Net Debt",
                "Target Price = Equity Value / Shares Outstanding",
            ],
            "step_by_step": [
                "Project revenue using a dynamic growth fade from near-term assumptions toward terminal growth.",
                "Apply the normalized EBIT margin to derive operating profit.",
                "Tax-effect EBIT into NOPAT using the effective tax rate.",
                "Convert NOPAT into UFCF by adding D&A and subtracting CapEx plus working-capital investment.",
                "Discount explicit UFCF with mid-year convention using WACC.",
                "Estimate terminal value using Gordon Growth and exit multiple, then cross-check the result.",
                "Bridge enterprise value to equity value through net debt and share count.",
            ],
            "forecast_table": forecast_rows,
            "discount_schedule": self._discount_schedule(forecast_rows),
            "valuation_bridge": {
                "pv_explicit_fcf": _safe_number(self.dcf.get("pv_explicit_fcf"), 0),
                "pv_terminal_value": _safe_number(self.dcf.get("pv_terminal_value"), 0),
                "enterprise_value": _safe_number(self.dcf.get("enterprise_value"), 0),
                "net_debt": _safe_number(self.dcf.get("net_debt"), 0),
                "equity_value": _safe_number(self.dcf.get("equity_value"), 0),
                "shares_outstanding": _safe_number(self.dcf.get("shares_outstanding"), 0),
                "fair_price_per_share": _safe_number(self.dcf.get("fair_price_per_share")),
            },
            "terminal_value": self.dcf.get("terminal_value_details"),
            "wacc_details": self.dcf.get("wacc_details"),
            "sensitivity_matrix": self.sensitivity,
        }

    def _citations(self) -> List[Dict[str, Any]]:
        citations = [
            {"label": "Yahoo Finance Quote", "url": self.market.get("source_url")},
            {"label": "Yahoo Finance Financials", "url": self.fin.get("source_url")},
        ]
        citations.extend(
            {"label": item.get("title", "News"), "url": item.get("url") or item.get("link")}
            for item in (self.context.get("recent_news") or self.news.get("recent_news") or [])
            if item.get("url") or item.get("link")
        )
        citations.extend(
            {"label": filing.get("title", filing.get("type", "Filing")), "url": filing.get("edgar_url") or filing.get("primary_doc_url")}
            for filing in self.context.get("filing_excerpts", [])
            if filing.get("edgar_url") or filing.get("primary_doc_url")
        )
        return [item for item in citations if item.get("url")]

    def _retrieval_documents(self, report: Dict[str, Any]) -> List[Dict[str, Any]]:
        citations = self._citations()
        docs = [
            {
                "id": "assistant-identity",
                "section": "assistant.identity",
                "text": (
                    "You are AI Valuation Terminal. You explain the valuation report, DCF mechanics, peer analysis, "
                    "validation findings, evidence sources, and the multi-agent workflow shown on the page."
                ),
                "citations": [],
            },
            {
                "id": "report-summary",
                "section": "report_agent.summary",
                "text": json.dumps(report["report_agent"]["summary"], ensure_ascii=False),
                "citations": citations[:2],
            },
            {
                "id": "dcf-calculation",
                "section": "calculation_details.step_by_step",
                "text": " ".join(report["calculation_details"]["step_by_step"]),
                "citations": citations[:2],
            },
            {
                "id": "dcf-formulae",
                "section": "calculation_details.formulae",
                "text": " ".join(report["calculation_details"]["formulae"]),
                "citations": citations[:2],
            },
            {
                "id": "dcf-wacc-details",
                "section": "calculation_details.wacc_details",
                "text": json.dumps(report["calculation_details"]["wacc_details"], ensure_ascii=False),
                "citations": citations[:2],
            },
            {
                "id": "dcf-forecast-table",
                "section": "calculation_details.forecast_table",
                "text": json.dumps(report["calculation_details"]["forecast_table"], ensure_ascii=False),
                "citations": citations[:2],
            },
            {
                "id": "dcf-terminal-value",
                "section": "calculation_details.terminal_value",
                "text": json.dumps(report["calculation_details"]["terminal_value"], ensure_ascii=False),
                "citations": citations[:2],
            },
            {
                "id": "dcf-valuation-bridge",
                "section": "calculation_details.valuation_bridge",
                "text": json.dumps(report["calculation_details"]["valuation_bridge"], ensure_ascii=False),
                "citations": citations[:2],
            },
            {
                "id": "peer-analysis",
                "section": "peer_group_analysis",
                "text": json.dumps(report.get("peer_group_analysis", {}), ensure_ascii=False),
                "citations": citations,
            },
            {
                "id": "comparable-analysis",
                "section": "comparable_analysis",
                "text": json.dumps(report.get("comparable_analysis", {}), ensure_ascii=False),
                "citations": citations[:2],
            },
            {
                "id": "validation",
                "section": "validation_agents",
                "text": json.dumps(report["validation_agents"], ensure_ascii=False),
                "citations": citations[:2],
            },
            {
                "id": "context-news",
                "section": "contextual_data.recent_news",
                "text": json.dumps(report["contextual_data"]["recent_news"], ensure_ascii=False),
                "citations": citations[2:],
            },
            {
                "id": "context-filings",
                "section": "contextual_data.filing_excerpts",
                "text": json.dumps(report["contextual_data"]["filing_excerpts"], ensure_ascii=False),
                "citations": citations[2:],
            },
            {
                "id": "risk-factors",
                "section": "risk_factors",
                "text": json.dumps(report.get("risk_factors", []), ensure_ascii=False),
                "citations": citations[:2],
            },
            {
                "id": "full-report",
                "section": "full_report_context",
                "text": json.dumps(report, ensure_ascii=False),
                "citations": citations,
            },
        ]
        return docs

    def build_structured_output(self) -> Dict[str, Any]:
        report_agent = self._report_agent()
        citations = self._citations()
        val_range = self._valuation_range()
        report = {
            "meta": {
                "ticker": self.ticker,
                "generated_at": self.generated_at,
                "system_note": "Deterministic Python performs financial calculations; LLM reasoning is limited to narrative critique and chat interpretation.",
            },
            "data_availability": self._data_availability(),
            "structured_output": {
                "Company Name": self._company_info().get("name"),
                "Valuation Method": "DCF + Comparable Multiples + Analyst Narrative",
                "Key Inputs": self.fin,
                "Assumptions": report_agent["core_assumptions"],
                "Evidence Sources": citations,
                "Target Price/Range": {
                    "target_price": report_agent["summary"].get("target_price"),
                    "valuation_range": val_range,
                },
                "Confidence Level": self.valid.get("confidence_score"),
                "Risk Factors": self.valid.get("risk_factors", []),
                "Critique Comments": self.valid.get("critique_comments"),
            },
            "report_agent": report_agent,
            "company_info": self._company_info(),
            "market_snapshot": self._market_snapshot(),
            "financial_data": self._financial_cards(),
            "contextual_data": self._contextual_data(),
            "calculation_details": self._calculation_details(),
            "validation_agents": self._validation_agents(),
            "peer_group_analysis": self.peer_analysis,
            "comparable_analysis": self.comp,
            "backtesting": self.backtest,
            "risk_factors": self.valid.get("risk_factors", []),
            "scenario_analysis": {
                "bull": {"description": "Revenue +1%, WACC -1%", "fair_price": val_range.get("high")},
                "base": {"description": "Base assumptions", "fair_price": val_range.get("mid")},
                "bear": {"description": "Revenue -1%, WACC +1%", "fair_price": val_range.get("low")},
            },
            "citations": citations,
        }
        report["chat_context"] = {
            "anti_hallucination_rules": [
                "Answer only from retrieved report evidence.",
                "Cite at least one supporting source or report section.",
                "If the answer is missing from the report, say so explicitly.",
            ],
            "documents": self._retrieval_documents(report),
        }
        return report

    def to_json(self) -> str:
        return json.dumps(self.build_structured_output(), indent=2, ensure_ascii=False, default=str)

    def to_markdown(self) -> str:
        report = self.build_structured_output()
        summary = report["report_agent"]["summary"]
        assumptions = report["report_agent"]["core_assumptions"]
        lines = [
            f"# Valuation Memo: {report['company_info']['name']} ({self.ticker})",
            f"_Generated: {self.generated_at}_",
            "",
            "## Report Agent",
            f"- Target Price: ${summary.get('target_price')}",
            f"- Current Price: ${summary.get('current_price')}",
            f"- Valuation Range: {summary.get('valuation_range')}",
            f"- Confidence: {summary.get('confidence_score')}",
            "",
            "## Core Assumptions",
        ]
        for key, value in assumptions.items():
            lines.append(f"- {key}: {value}")

        lines.extend(["", "## DCF Step-by-Step"])
        for step in report["calculation_details"]["step_by_step"]:
            lines.append(f"- {step}")

        lines.extend(["", "## Validation Agents"])
        for agent_key in ["inconsistency_agent", "evidence_audit_agent", "uncertainty_agent"]:
            agent = report["validation_agents"][agent_key]
            lines.append(f"### {agent['title']}")
            lines.append(agent["goal"])
            for finding in agent["findings"] or ["No material findings recorded."]:
                lines.append(f"- {finding}")

        lines.extend(["", "## Evidence Sources"])
        for citation in report["citations"]:
            lines.append(f"- {citation['label']}: {citation['url']}")
        return "\n".join(lines)
