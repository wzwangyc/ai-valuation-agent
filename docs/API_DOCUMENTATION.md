# API Documentation

## Base URL

`http://127.0.0.1:8080`

## Endpoints

### `GET /api/health`

Returns service health status.

### `GET /api/chart/{ticker}`

Returns chart data for the requested ticker.

Primary use:

- candlestick chart rendering
- price overlays for target and valuation range

### `GET /api/evaluate/{ticker}`

Runs the valuation pipeline for the ticker and returns the current pipeline result.

Behavior:

- validates ticker
- collects market, financial, macro, peer, and context inputs
- blocks Phase B if collected inputs fail validation
- runs valuation, validation, and report generation

### `GET /api/report/{ticker}`

Returns the generated report payload for the ticker if available.

### `GET /api/download/{ticker}/json`

Downloads the JSON valuation report.

### `GET /api/download/{ticker}/md`

Downloads the Markdown valuation report.

Alias also supported:

- `GET /api/download/{ticker}/markdown`

### `POST /api/chat/{ticker}`

Chat endpoint for report-grounded question answering.

Expected behavior:

- answers in English
- uses report-grounded retrieval
- rejects unsupported answers when evidence is absent

## Error Handling

- invalid ticker input returns an English validation error
- upstream timeouts are surfaced as explicit degradation messages
- missing report data produces a report-not-available style response

## Notes

- The API is designed for local demo and development use.
- External data-source availability still affects latency and completeness of non-core modules such as filings and news.

## External Source References

- Finnhub peers:
  - `https://finnhub.io/docs/api/company-peers`
- Finnhub basic financials:
  - `https://finnhub.io/docs/api/company-basic-financials`
- Finnhub company profile:
  - `https://finnhub.io/docs/api/company-profile2`
- FRED API:
  - `https://fred.stlouisfed.org/docs/api/fred/`
- `fredapi` package:
  - `https://pypi.org/project/fredapi/`
- `yfinance` API reference:
  - `https://ranaroussi.github.io/yfinance/reference/index.html`
