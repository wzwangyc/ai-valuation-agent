from data_collection.data_validation import CollectedDataValidator


def test_collected_data_validator_accepts_complete_inputs() -> None:
    result = CollectedDataValidator(
        ticker="AAPL",
        market_data={
            "current_price": 100.0,
            "market_cap": 1_000_000_000.0,
            "shares_outstanding": 10_000_000.0,
            "beta": 1.1,
        },
        financial_summary={
            "revenue": 500_000_000.0,
            "ebit": 100_000_000.0,
            "operating_cash_flow": 120_000_000.0,
            "capex": 20_000_000.0,
            "effective_tax_rate": 0.22,
        },
        macro_data={
            "risk_free_rate": 0.04,
            "inflation_rate": 0.025,
            "terminal_growth_anchor": 0.03,
        },
    ).run()

    assert result["passed"] is True
    assert result["errors"] == []


def test_collected_data_validator_rejects_missing_or_invalid_core_inputs() -> None:
    result = CollectedDataValidator(
        ticker="AAPL",
        market_data={
            "current_price": 0.0,
            "market_cap": None,
            "shares_outstanding": -1.0,
            "beta": 8.0,
        },
        financial_summary={
            "revenue": None,
            "ebit": None,
            "operating_cash_flow": None,
            "capex": None,
            "effective_tax_rate": 0.9,
        },
        macro_data={
            "risk_free_rate": None,
            "inflation_rate": 0.3,
            "terminal_growth_anchor": 0.2,
        },
    ).run()

    assert result["passed"] is False
    assert len(result["errors"]) >= 6
