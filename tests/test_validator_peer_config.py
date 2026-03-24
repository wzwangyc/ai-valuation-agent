from validation.validator import ValuationValidator


def test_validator_uses_configured_min_peer_count() -> None:
    validator = ValuationValidator(
        dcf_result={
            "wacc_details": {"wacc": 0.10, "risk_free_rate": 0.04, "effective_tax_rate": 0.2},
            "terminal_value_details": {"terminal_growth": 0.03},
            "tv_as_pct_of_ev": 50,
            "key_assumptions": {"ebit_margin": 0.2, "revenue_growth_schedule": [0.1, 0.08, 0.06]},
            "forecast_table": {"UFCF": {"1": 1, "2": 2}},
        },
        comparable_result={"peer_count": 3},
        financial_summary={"operating_margin": 0.2, "source_url": "https://example.com"},
        market_data={"source_url": "https://example.com", "business_summary": "ok"},
    )

    result = validator.run_full_validation()

    peer_rule = next(rule for rule in result["rules"] if "Comparable peer count" in rule["rule"])
    assert peer_rule["passed"] is True
