"""
Phase D validation with explicit rules, evidence mapping, and confidence breakdown.
"""
from typing import Dict

from config import MIN_PEER_COUNT


class ValuationValidator:
    def __init__(
        self,
        dcf_result: Dict,
        comparable_result: Dict = None,
        financial_summary: Dict = None,
        market_data: Dict = None,
    ):
        self.dcf = dcf_result or {}
        self.comp = comparable_result or {}
        self.fin_summary = financial_summary or {}
        self.market = market_data or {}

    def _pass_fail(self, passed: bool, detail: str) -> Dict:
        return {"passed": passed, "detail": detail}

    def run_full_validation(self) -> Dict:
        wacc = self.dcf.get("wacc_details", {}).get("wacc", 0)
        rf = self.dcf.get("wacc_details", {}).get("risk_free_rate", 0)
        terminal_growth = self.dcf.get("terminal_value_details", {}).get("terminal_growth", 0)
        tv_pct = self.dcf.get("tv_as_pct_of_ev", 0)
        ebit_margin = self.dcf.get("key_assumptions", {}).get("ebit_margin", 0)
        tax_rate = self.dcf.get("wacc_details", {}).get("effective_tax_rate", 0)
        peer_count = self.comp.get("peer_count", 0)
        growth_schedule = self.dcf.get("key_assumptions", {}).get("revenue_growth_schedule", [])
        forecast_table = self.dcf.get("forecast_table", {})
        ufcf_values = list((forecast_table.get("UFCF") or {}).values())

        rules = [
            {
                "rule": "Terminal growth must be <= 3.5% and below WACC.",
                **self._pass_fail(terminal_growth <= 0.035 and terminal_growth < wacc, f"g={terminal_growth:.2%}, WACC={wacc:.2%}"),
            },
            {
                "rule": "EBIT margin must remain in a reasonable range.",
                **self._pass_fail(-0.1 <= ebit_margin <= 0.5, f"EBIT margin={ebit_margin:.2%}"),
            },
            {
                "rule": "WACC must be at least 100bp above risk-free rate.",
                **self._pass_fail(wacc >= rf + 0.01, f"WACC={wacc:.2%}, Rf={rf:.2%}"),
            },
            {
                "rule": f"Comparable peer count must be at least {MIN_PEER_COUNT}.",
                **self._pass_fail(peer_count >= MIN_PEER_COUNT, f"Peer count={peer_count}"),
            },
            {
                "rule": "Forecast growth should not contain abnormal spikes.",
                **self._pass_fail(not growth_schedule or max(growth_schedule) - min(growth_schedule) <= 0.25, f"Growth schedule={growth_schedule}"),
            },
            {
                "rule": "Terminal value should not dominate EV above 70%.",
                **self._pass_fail(tv_pct <= 70, f"TV as % of EV={tv_pct:.1f}%"),
            },
            {
                "rule": "Negative UFCF should not persist for more than 2 years.",
                **self._pass_fail(sum(1 for item in ufcf_values if item < 0) <= 2, f"Negative UFCF years={sum(1 for item in ufcf_values if item < 0)}"),
            },
            {
                "rule": "Effective tax rate should remain in a reasonable range.",
                **self._pass_fail(0.05 <= tax_rate <= 0.35, f"Tax rate={tax_rate:.2%}"),
            },
        ]

        issues = [f"{row['rule']} {row['detail']}" for row in rules if not row["passed"]]
        risk_factors = []
        if tv_pct > 70:
            risk_factors.append("Terminal value contributes more than 70% of EV, so long-duration assumptions drive the outcome.")
        if peer_count < MIN_PEER_COUNT:
            risk_factors.append("Comparable valuation is under-supported because the peer set is below the required minimum.")
        if not self.market.get("business_summary"):
            risk_factors.append("Qualitative context is sparse, which weakens the narrative-to-quant bridge.")

        evidence_mapping = [
            {
                "assumption": "Year 1 revenue growth",
                "supporting_evidence": f"Revenue growth schedule starts at {growth_schedule[0]:.2%}" if growth_schedule else "Growth schedule unavailable",
                "source": self.market.get("source_url"),
            },
            {
                "assumption": "EBIT margin",
                "supporting_evidence": f"Historical operating margin proxy {self.fin_summary.get('operating_margin')}",
                "source": self.fin_summary.get("source_url"),
            },
            {
                "assumption": "Terminal growth",
                "supporting_evidence": f"Terminal growth anchored at {terminal_growth:.2%}",
                "source": "https://fred.stlouisfed.org/series/GDP",
            },
            {
                "assumption": "WACC",
                "supporting_evidence": f"WACC={wacc:.2%}, beta={self.dcf.get('wacc_details', {}).get('beta')}, ERP={self.dcf.get('wacc_details', {}).get('equity_risk_premium')}",
                "source": "https://fred.stlouisfed.org/series/DGS10",
            },
        ]

        confidence = 10
        breakdown = [{"item": "Base score", "delta": 0, "remaining": 10}]
        penalties = [
            (f"Peer count below {MIN_PEER_COUNT}", -2 if peer_count < MIN_PEER_COUNT else 0),
            ("Terminal value concentration above 70%", -1 if tv_pct > 70 else 0),
            ("Sparse qualitative context", -1 if not self.market.get("business_summary") else 0),
            ("Forecast volatility abnormal", -1 if growth_schedule and max(growth_schedule) - min(growth_schedule) > 0.25 else 0),
        ]
        for label, delta in penalties:
            if delta:
                confidence += delta
                breakdown.append({"item": label, "delta": delta, "remaining": max(confidence, 1)})
        confidence = max(1, min(confidence, 10))
        breakdown.append({"item": "Final confidence", "delta": 0, "remaining": confidence})

        critique_comments = (
            f"Rules passed: {sum(1 for row in rules if row['passed'])}/{len(rules)}. "
            f"Primary issues: {issues if issues else 'No critical rule breaks.'}"
        )
        return {
            "validation_issues": issues,
            "risk_factors": risk_factors,
            "evidence_audit": [f"{row['assumption']} -> {row['supporting_evidence']}" for row in evidence_mapping],
            "evidence_mapping": evidence_mapping,
            "rules": rules,
            "confidence_score": confidence,
            "confidence_label": "HIGH" if confidence >= 8 else "MEDIUM" if confidence >= 5 else "LOW",
            "confidence_breakdown": breakdown,
            "critique_comments": critique_comments,
            "validation_method": "Deterministic rules plus explicit evidence mapping.",
        }

    def generate_llm_critique(self, llm) -> str:
        validation = self.run_full_validation()
        prompt = (
            f"You are a critic agent reviewing a valuation for {self.dcf.get('ticker')}.\n"
            f"Rules: {validation['rules']}\n"
            f"Issues: {validation['validation_issues']}\n"
            f"Confidence: {validation['confidence_score']}/10\n"
            "Write a short review. If confidence is below 8, end with REVISE: and a concrete fix."
        )
        try:
            response = llm.invoke(prompt)
            return response.content if hasattr(response, "content") else str(response)
        except Exception as exc:
            return f"LLM critique unavailable: {exc}"
