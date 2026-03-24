import pandas as pd

from data_collection.financial_statements import FinancialStatementsExtractor


def _build_extractor(balance_sheet: pd.DataFrame) -> FinancialStatementsExtractor:
    extractor = FinancialStatementsExtractor.__new__(FinancialStatementsExtractor)
    extractor.ticker = "TEST"
    extractor.stock = None
    extractor.periods = list(balance_sheet.columns)
    extractor.balance_sheet = balance_sheet
    extractor.financials = pd.DataFrame()
    extractor.cashflow = pd.DataFrame()
    return extractor


def test_operating_working_capital_excludes_cash_and_short_term_debt() -> None:
    periods = [pd.Timestamp("2025-12-31"), pd.Timestamp("2024-12-31")]
    balance_sheet = pd.DataFrame(
        {
            periods[0]: {
                "Current Assets": 300.0,
                "Cash And Cash Equivalents": 50.0,
                "Current Liabilities": 180.0,
                "Current Debt": 20.0,
            },
            periods[1]: {
                "Current Assets": 260.0,
                "Cash And Cash Equivalents": 40.0,
                "Current Liabilities": 150.0,
                "Current Debt": 10.0,
            },
        }
    )
    extractor = _build_extractor(balance_sheet)

    working_capital = extractor.get_working_capital()

    assert float(working_capital.iloc[0]) == 90.0
    assert float(working_capital.iloc[1]) == 80.0


def test_delta_working_capital_is_positive_when_operating_nwc_increases() -> None:
    periods = [
        pd.Timestamp("2025-12-31"),
        pd.Timestamp("2024-12-31"),
        pd.Timestamp("2023-12-31"),
    ]
    balance_sheet = pd.DataFrame(
        {
            periods[0]: {
                "Current Assets": 300.0,
                "Cash And Cash Equivalents": 50.0,
                "Current Liabilities": 180.0,
                "Current Debt": 20.0,
            },
            periods[1]: {
                "Current Assets": 260.0,
                "Cash And Cash Equivalents": 40.0,
                "Current Liabilities": 150.0,
                "Current Debt": 10.0,
            },
            periods[2]: {
                "Current Assets": 220.0,
                "Cash And Cash Equivalents": 35.0,
                "Current Liabilities": 145.0,
                "Current Debt": 10.0,
            },
        }
    )
    extractor = _build_extractor(balance_sheet)

    delta_wc = extractor.get_delta_working_capital()

    assert float(delta_wc.iloc[0]) == 10.0
    assert float(delta_wc.iloc[1]) == 30.0
