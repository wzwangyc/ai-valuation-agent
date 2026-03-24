import math

from valuation_engine.dcf_model import DCFModel


class _StubMacro:
    def get_long_term_gdp_growth(self) -> float:
        return 0.03


class _StubFin:
    periods = ["2025", "2024", "2023"]
    stock = type("Stock", (), {"info": {"revenueGrowth": 0.10, "currentPrice": 100.0}})()

    def get_revenue(self):
        import pandas as pd
        return pd.Series({"2025": 1000.0, "2024": 900.0, "2023": 810.0})

    def get_ebit(self):
        import pandas as pd
        return pd.Series({"2025": 200.0, "2024": 180.0, "2023": 162.0})

    def get_effective_tax_rate(self) -> float:
        return 0.25

    def get_depreciation(self):
        import pandas as pd
        return pd.Series({"2025": 40.0, "2024": 36.0, "2023": 32.4})

    def get_capex(self):
        import pandas as pd
        return pd.Series({"2025": 50.0, "2024": 45.0, "2023": 40.5})

    def get_working_capital(self):
        import pandas as pd
        return pd.Series({"2025": 100.0, "2024": 90.0, "2023": 81.0})

    def get_net_debt(self) -> float:
        return 100.0

    def get_shares_outstanding(self) -> float:
        return 10.0


class _StubWacc:
    def calculate(self):
        return {
            "wacc": 0.10,
            "risk_free_rate": 0.04,
            "cost_of_equity": 0.10,
            "cost_of_debt": 0.05,
            "effective_tax_rate": 0.25,
        }


def test_forecast_uses_standard_ufcf_formula() -> None:
    model = DCFModel("TEST", _StubMacro(), _StubFin(), _StubWacc(), forecast_years=1)

    forecast = model.forecast()
    row = forecast.iloc[0]
    expected = row["NOPAT"] + row["DA"] - row["CapEx"] - row["Delta_WC"]

    assert math.isclose(row["UFCF"], expected, rel_tol=1e-9)


def test_increasing_working_capital_reduces_ufcf() -> None:
    model = DCFModel("TEST", _StubMacro(), _StubFin(), _StubWacc(), forecast_years=1)

    forecast = model.forecast()
    row = forecast.iloc[0]

    assert row["Delta_WC"] > 0
    assert row["UFCF"] < (row["NOPAT"] + row["DA"] - row["CapEx"])
