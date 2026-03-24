from pathlib import Path

import pandas as pd

from data_collection.macro_data import MacroDataCollector


def test_macro_summary_uses_live_values_and_marks_live_api(monkeypatch, tmp_path: Path) -> None:
    collector = MacroDataCollector("dummy-key")
    collector.__class__._summary_cache = None
    collector.__class__._summary_cache_ts = 0.0

    snapshot_path = tmp_path / "macro_summary.json"
    monkeypatch.setattr("data_collection.macro_data.SNAPSHOT_PATH", snapshot_path)
    monkeypatch.setattr(collector, "get_risk_free_rate", lambda: 0.043)
    monkeypatch.setattr(collector, "get_market_risk_premium", lambda: 0.047)
    monkeypatch.setattr(collector, "get_long_term_gdp_growth", lambda: 0.035)
    monkeypatch.setattr(collector, "get_inflation_rate", lambda: 0.024)

    summary = collector.get_macro_summary()

    assert summary["risk_free_rate"] == 0.043
    assert summary["equity_risk_premium"] == 0.047
    assert summary["source_mode"] == "live_api"
    assert snapshot_path.exists()


def test_macro_summary_falls_back_to_snapshot_when_live_calls_fail(monkeypatch, tmp_path: Path) -> None:
    collector = MacroDataCollector("dummy-key")
    collector.__class__._summary_cache = None
    collector.__class__._summary_cache_ts = 0.0

    snapshot_path = tmp_path / "macro_summary.json"
    snapshot_path.write_text(
        (
            '{"risk_free_rate": 0.04, "equity_risk_premium": 0.05, '
            '"long_term_gdp_growth": 0.03, "inflation_rate": 0.02}'
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("data_collection.macro_data.SNAPSHOT_PATH", snapshot_path)
    monkeypatch.setattr(collector, "get_risk_free_rate", lambda: (_ for _ in ()).throw(RuntimeError("fail")))

    summary = collector.get_macro_summary()

    assert summary["risk_free_rate"] == 0.04
    assert summary["equity_risk_premium"] == 0.05
    assert summary["source_mode"] == "local_snapshot"


def test_get_market_risk_premium_uses_equity_risk_premium_column(monkeypatch) -> None:
    collector = MacroDataCollector("dummy-key")

    class DummyResponse:
        text = "<html></html>"

        @staticmethod
        def raise_for_status() -> None:
            return None

    monkeypatch.setattr("data_collection.macro_data._HTTP.session.get", lambda *args, **kwargs: DummyResponse())
    monkeypatch.setattr(
        pd,
        "read_html",
        lambda _html: [
            pd.DataFrame([[1, 2]]),
            pd.DataFrame(
                [
                    ["Country", "Adj. Default Spread", "Country Risk Premium", "Equity Risk Premium", "Corporate Tax Rate"],
                    ["United States", "0.00%", "0.00%", "4.69%", "21.00%"],
                    ["Brazil", "2.50%", "3.80%", "8.49%", "34.00%"],
                ]
            ),
        ],
    )

    assert collector.get_market_risk_premium() == 0.0469


def test_get_market_risk_premium_rejects_missing_columns(monkeypatch) -> None:
    collector = MacroDataCollector("dummy-key")

    class DummyResponse:
        text = "<html></html>"

        @staticmethod
        def raise_for_status() -> None:
            return None

    monkeypatch.setattr("data_collection.macro_data._HTTP.session.get", lambda *args, **kwargs: DummyResponse())
    monkeypatch.setattr(
        pd,
        "read_html",
        lambda _html: [
            pd.DataFrame([[1, 2]]),
            pd.DataFrame(
                [
                    ["Country", "Adj. Default Spread", "Corporate Tax Rate"],
                    ["United States", "0.00%", "21.00%"],
                ]
            ),
        ],
    )

    try:
        collector.get_market_risk_premium()
    except ValueError as exc:
        assert "columns could not be identified" in str(exc)
    else:
        raise AssertionError("Expected a ValueError when ERP columns are missing.")
