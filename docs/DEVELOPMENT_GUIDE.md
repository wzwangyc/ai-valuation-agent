# Development Guide

## Project Priorities

1. Keep valuation arithmetic deterministic.
2. Validate inputs before valuation.
3. Treat every external API as unstable.
4. Prefer explicit fallbacks over silent failure.
5. Keep modules separated by responsibility.

## Module Boundaries

### `data_collection`

Responsible for:

- API access
- raw data extraction
- normalization
- basic data validation before valuation

Not responsible for:

- valuation arithmetic
- final report rendering

### `valuation_engine`

Responsible for:

- WACC
- DCF
- comparable multiples
- sensitivity analysis

### `validation`

Responsible for:

- valuation rule checks
- confidence scoring
- evidence audit

### `report_generator`

Responsible for:

- JSON and Markdown output formatting

### `api.py`

Responsible for:

- HTTP surface
- request validation
- returning existing pipeline results

## Development Workflow

### 1. Install dependencies

```bash
pip install -r requirements.txt
cd frontend
npm install
cd ..
```

### 2. Configure environment

Use `.env.example` as the template.

### 3. Run tests

```bash
pytest -q
```

### 4. Run static checks

```bash
python -m flake8 . --select=F,E9,E7,E8 --statistics
```

### 5. Start the backend

```bash
python -m uvicorn api:app --host 127.0.0.1 --port 8080
```

## Implementation Notes

### Data-source strategy

- Use live API data first.
- Use controlled fallback paths when the primary source fails.
- Use local snapshots only as the final fallback for demo-critical cases.
- Do not infer endpoint semantics from trial-and-error when an official API reference is available.
- Keep the actual endpoint usage aligned with official documentation:
  - Finnhub peers, profile, and metrics docs
  - FRED API and `fredapi`
  - `yfinance` documented ticker methods

### Financial code expectations

- Every major formula should be readable in code.
- UFCF, WACC, and terminal value logic should not be hidden behind opaque helper behavior.
- When assumptions are used, the source or rationale must be explicit.

### Chat expectations

- Chat must remain report-grounded.
- Answers must remain source-aware.
- Unsupported answers should be refused rather than hallucinated.
