from __future__ import annotations

from config import TARGET_TICKERS
from data_collection.peer_finder import INDUSTRY_TICKER_MAP
from data_collection.yahoo_client import warm_raw_snapshots


DEMO_TICKERS = TARGET_TICKERS[:4]


def main():
    warm_set = set(DEMO_TICKERS)
    for tickers in INDUSTRY_TICKER_MAP.values():
        if any(ticker in DEMO_TICKERS for ticker in tickers):
            warm_set.update(tickers)

    ordered = [ticker for ticker in TARGET_TICKERS if ticker in warm_set]
    ordered.extend([ticker for ticker in sorted(warm_set) if ticker not in ordered])

    print("Warming raw snapshots for demo universe:", ", ".join(ordered))
    for ticker in ordered:
        result = warm_raw_snapshots(ticker, news_count=5)
        print(ticker, result)


if __name__ == "__main__":
    main()
