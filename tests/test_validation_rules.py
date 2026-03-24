from config import MIN_PEER_COUNT
from validation.validator import ValuationValidator


def test_validation_flags_peer_shortfall_and_terminal_value_concentration() -> None:
    validator = ValuationValidator(
        dcf_result={
            "ticker": "TEST",
            "wacc_details": {"wacc": 0.10, "risk_free_rate": 0.04, "effective_tax_rate": 0.22, "beta": 1.1, "equity_risk_premium": 0.055},
            "terminal_value_details": {"terminal_growth": 0.035},
            "tv_as_pct_of_ev": 82.0,
            "key_assumptions": {"ebit_margin": 0.25, "revenue_growth_schedule": [0.10, 0.08, 0.06]},
            "forecast_table": {"UFCF": {"1": 100.0, "2": 110.0}},
        },
        comparable_result={"peer_count": max(MIN_PEER_COUNT - 1, 0)},
        financial_summary={"operating_margin": 0.25, "source_url": "https://example.com/financials"},
        market_data={"source_url": "https://example.com/quote", "business_summary": "Test summary"},
    )

    result = validator.run_full_validation()

    assert result["confidence_score"] < 10
    assert any("Comparable peer count" in row["rule"] and not row["passed"] for row in result["rules"])
    assert any("Terminal value should not dominate EV above 70%" in row["rule"] and not row["passed"] for row in result["rules"])
