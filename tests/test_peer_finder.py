from data_collection.peer_finder import PeerFinder


def test_peer_finder_builds_comparable_set_with_finnhub_metrics_and_yahoo_identity(monkeypatch) -> None:
    monkeypatch.setattr(
        "data_collection.peer_finder.get_info",
        lambda stock, symbol: {
            "industry": "Consumer Electronics",
            "sector": "Technology",
            "marketCap": 2_000_000_000_000,
        },
    )
    monkeypatch.setattr(
        "data_collection.peer_finder.get_peer_companies",
        lambda symbol: ["DELL", "WDC", "PSTG", "NTAP", "HPQ", "SMCI"],
    )

    metric_map = {
        "DELL": {"metric": {"marketCapitalization": 80_000, "peTTM": 16, "evEbitdaTTM": 10, "pbQuarterly": 3, "psTTM": 1.2, "roeTTM": 18}},
        "WDC": {"metric": {"marketCapitalization": 60_000, "peTTM": 14, "evEbitdaTTM": 9, "pbQuarterly": 2, "psTTM": 1.0, "roeTTM": 12}},
        "PSTG": {"metric": {"marketCapitalization": 20_000, "peTTM": 21, "evEbitdaTTM": 15, "pbQuarterly": 6, "psTTM": 4.0, "roeTTM": 11}},
        "NTAP": {"metric": {"marketCapitalization": 25_000, "peTTM": 19, "evEbitdaTTM": 12, "pbQuarterly": 7, "psTTM": 3.0, "roeTTM": 20}},
        "HPQ": {"metric": {"marketCapitalization": 30_000, "peTTM": 13, "evEbitdaTTM": 8, "pbQuarterly": 1.5, "psTTM": 0.8, "roeTTM": 15}},
        "SMCI": {"metric": {"marketCapitalization": 50_000, "peTTM": 25, "evEbitdaTTM": 18, "pbQuarterly": 5, "psTTM": 2.5, "roeTTM": 10}},
    }
    monkeypatch.setattr(
        "data_collection.peer_finder.get_basic_financials",
        lambda symbol, timeout=3.0: metric_map[symbol],
    )
    monkeypatch.setattr(
        "data_collection.peer_finder.get_quote_multiples",
        lambda ticker, symbol, ttl_seconds=300: {
            "longName": f"{symbol} Inc.",
            "industry": "Consumer Electronics",
            "sector": "Technology",
            "trailingPE": None,
            "enterpriseToEbitda": None,
            "priceToBook": None,
            "enterpriseToRevenue": None,
            "returnOnEquity": None,
            "marketCap": None,
        },
    )

    finder = PeerFinder("AAPL")
    peers = finder.find_peers(max_seconds=7.5)

    assert len(peers) == 6
    assert finder.last_run["warning"] is None
    assert [peer["ticker"] for peer in peers] == ["DELL", "WDC", "SMCI", "HPQ", "NTAP", "PSTG"]
