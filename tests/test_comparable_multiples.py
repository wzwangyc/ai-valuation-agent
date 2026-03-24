from valuation_engine.comparable_multiples import ComparableMultiples


def test_comparable_multiples_uses_iqr_filtered_positive_values() -> None:
    peers = [
        {"ticker": "A", "pe": 10, "ev_ebitda": 8, "pb": 2, "ev_revenue": 1.5, "roe": 0.10},
        {"ticker": "B", "pe": 12, "ev_ebitda": 9, "pb": 2.2, "ev_revenue": 1.6, "roe": 0.12},
        {"ticker": "C", "pe": 11, "ev_ebitda": 8.5, "pb": 2.1, "ev_revenue": 1.4, "roe": 0.11},
        {"ticker": "D", "pe": 200, "ev_ebitda": 90, "pb": 20, "ev_revenue": 15, "roe": 2.0},
    ]
    company = {
        "trailingEps": 5.0,
        "ebitda": 100.0,
        "sharesOutstanding": 10.0,
        "enterpriseValue": 900.0,
        "marketCap": 700.0,
        "currentPrice": 50.0,
        "trailingPE": 14.0,
        "enterpriseToEbitda": 9.0,
        "priceToBook": 3.0,
        "enterpriseToRevenue": 2.0,
        "returnOnEquity": 0.15,
    }

    result = ComparableMultiples("TEST", peers, company).calculate()

    assert result["peer_median_pe"] == 11.0
    assert result["peer_median_ev_ebitda"] == 8.5
    assert result["data_source"].startswith("Finnhub basic financial metrics")

