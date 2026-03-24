from valuation_engine.wacc_calculator import WACCCalculator


class _StubMacro:
    def get_risk_free_rate(self) -> float:
        return 0.04

    def get_market_risk_premium(self) -> float:
        return 0.055


class _StubSeries:
    def __init__(self, value):
        self.value = value

    def __getitem__(self, key):
        return self.value


class _StubFin:
    ltm_period = "LTM"

    def __init__(self):
        self.info = {"beta": 1.2, "marketCap": 1000.0}
        self.income_stmt = object()
        self.balance_sheet = object()

    def _find(self, source, keywords):
        if "interest" in keywords:
            return _StubSeries(30.0)
        if "total" in keywords and "debt" in keywords:
            return _StubSeries(300.0)
        return None

    def get_net_debt(self) -> float:
        return 200.0

    def get_effective_tax_rate(self) -> float:
        return 0.25


def test_wacc_calculation_returns_traceable_components() -> None:
    result = WACCCalculator("TEST", _StubMacro(), _StubFin()).calculate()

    assert result["risk_free_rate"] == 0.04
    assert result["beta"] == 1.2
    assert result["equity_risk_premium"] == 0.055
    assert result["cost_of_equity"] > result["risk_free_rate"]
    assert result["wacc"] >= result["risk_free_rate"] + 0.02
