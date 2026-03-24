# AI Valuation Agent with Evidence and Validation

Agent-based equity valuation system with deterministic DCF, comparable-company analysis, validation rules, structured reporting, and a terminal-style web UI.

## Scope

The project is organized around four major stages:

1. Data collection
2. Valuation
3. Validation and critique
4. Structured report generation

The implementation prioritizes deterministic financial calculations and source traceability over cosmetic output.

## Core Design Principles

- Financial arithmetic is performed in Python, not delegated to an LLM.
- Collected inputs are validated before valuation runs.
- External APIs are treated as unreliable and must degrade safely.
- Every major output should have a source path or an explicit fallback path.
- The chat layer is constrained to report-grounded answers.

## Architecture

### Phase A: Data Collection

- `data_collection/market_data.py`
  - current price, market cap, beta, shares outstanding
- `data_collection/financial_statements.py`
  - income statement, balance sheet, cash flow extraction
  - operating NWC and delta NWC handling
- `data_collection/macro_data.py`
  - risk-free rate, inflation, long-term GDP growth, ERP
- `data_collection/context_data.py`
  - business description, news, filings
- `data_collection/peer_finder.py`
  - Finnhub-first peer discovery
  - comparable metrics with controlled fallback paths
- `data_collection/data_validation.py`
  - validates collected inputs before valuation

### Phase B: Valuation Engine

- `valuation_engine/wacc_calculator.py`
- `valuation_engine/dcf_model.py`
- `valuation_engine/comparable_multiples.py`
- `valuation_engine/sensitivity.py`

### Phase C: Structured Output

- `report_generator/memo_builder.py`
  - JSON report
  - Markdown report

### Phase D: Validation

- `validation/validator.py`
  - inconsistency detection
  - evidence audit
  - uncertainty and confidence scoring

### Application Layer

- `main.py`
  - orchestration pipeline
- `api.py`
  - FastAPI endpoints
- `chat_agent.py`
  - report-grounded semantic retrieval, local vector indexing, and answer generation

## Data Sources

- Yahoo Finance
  - market data
  - chart history
  - quote-level multiples
  - news and filings
- Finnhub
  - peer candidate discovery
  - peer metrics fallback
- FRED
  - risk-free rate
  - GDP growth
  - inflation
- Damodaran
  - equity risk premium

## Financial Methodology

### UFCF

The project uses:

`UFCF = EBIT * (1 - tax rate) + D&A - CapEx - Delta Operating NWC`

Operating NWC is defined as:

`(Current Assets - Cash and Equivalents) - (Current Liabilities - Short-Term Debt)`

If the preferred balance-sheet fields are incomplete, the extractor falls back to a narrower working-capital proxy with explicit logic in code.

### WACC

WACC is built from:

- risk-free rate
- beta
- equity risk premium
- pre-tax cost of debt
- effective tax rate
- capital structure weights

### Comparable Multiples

The comparable-company module uses peer sets plus:

- P/E
- EV/EBITDA
- P/B
- EV/Sales

### Validation

The validator checks:

- terminal growth vs. WACC
- margin sanity
- tax-rate sanity
- terminal value concentration
- peer-count sufficiency
- growth path stability
- evidence mapping
- confidence deductions

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
cd frontend
npm install
cd ..
```

### 2. Configure environment

Create `.env` from `.env.example` and set at least:

- `FRED_API_KEY`
- `FINNHUB_API_KEY`

Optional:

- `GEMINI_API_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

### 3. Run the backend

```bash
python -m uvicorn api:app --host 127.0.0.1 --port 8080
```

### 4. Run the frontend in development

```bash
cd frontend
npm run dev
```

### 5. Open the app

- backend: `http://127.0.0.1:8080`
- frontend dev server: Vite default URL shown in terminal

## Chat Retrieval Stack

The chat assistant now uses:

- local sentence-transformer embeddings
- a persisted local vector index in `output/chat_index/`
- cosine-similarity retrieval over report chunks
- lexical fallback if semantic retrieval is unavailable

This keeps answers grounded in the generated valuation report while avoiding external embedding-service dependence during normal local use.

## Tests and Checks

### Run unit tests

```bash
pytest -q
```

### Run static checks

```bash
python -m flake8 . --select=F,E9,E7,E8 --statistics
```

## Output Files

Generated reports are written to `output/`:

- `{TICKER}_valuation.json`
- `{TICKER}_valuation.md`
- `valuation_summary.json`

## Additional Documentation

- [DCF sanity check](docs/DCF_SANITY_CHECK.md)
- [RAG chat architecture](docs/RAG_CHAT_ARCHITECTURE.md)
- [API documentation](docs/API_DOCUMENTATION.md)
- [Development guide](docs/DEVELOPMENT_GUIDE.md)
- [Take-home requirements mapping](docs/TAKEHOME_REQUIREMENTS_MAPPING.md)
- [Data source strategy](docs/DATA_SOURCE_STRATEGY.md)
