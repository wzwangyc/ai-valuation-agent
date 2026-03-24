# Data Source Strategy

This document explains the data-source hierarchy for the valuation pipeline.

## Design Goal

The system should not depend on a single upstream source. Each major input path should have a defined source order, validation gate, and degradation rule.

## Source Hierarchy

### Market data

Primary:

- Yahoo Finance

Fallback:

- local raw chart snapshot for demo-critical symbols

Used for:

- current price
- market cap
- shares outstanding
- beta
- chart history

### Financial statements

Primary:

- Yahoo Finance statement extraction

Fallback:

- raw fundamentals snapshot when available

Used for:

- revenue
- EBIT
- net income
- operating cash flow
- CapEx
- D&A
- balance-sheet fields used in operating NWC

### Macro data

Primary:

- FRED
- Damodaran country risk premium table, parsed by explicit country and ERP column semantics

Fallback:

- local macro summary snapshot

Used for:

- risk-free rate
- inflation
- long-term GDP growth
- equity risk premium

### Peer discovery

Primary:

- Finnhub peer companies API

Fallback:

- curated industry and sector maps
- local raw Finnhub peer snapshot when the live request has succeeded before

Used for:

- candidate universe selection

### Peer metrics

Primary:

- Finnhub basic financial metrics

Fallback:

- Yahoo quote-level multiples
- local raw Finnhub metric snapshot when the live request has succeeded before

Used for:

- P/E
- EV/EBITDA
- P/B
- EV/Sales
- ROE
- market cap fallback

### Contextual evidence

Primary:

- Yahoo Finance news and filings

Fallback:

- local raw snapshots where available

Used for:

- business description
- recent news
- filing excerpts
- call excerpts

### Chat retrieval

Primary:

- local sentence-transformer embeddings
- persisted local vector index under `output/chat_index/`

Fallback:

- lexical retrieval over report chunks

Used for:

- report-grounded chat
- semantic lookup of valuation details
- citation-aware answer generation

## Validation Gate

Collected data must pass `data_collection/data_validation.py` before valuation runs.

The gate currently checks:

- market data sanity
- financial summary completeness and bounded tax rate
- macro-data completeness and bounded values

If validation fails, the valuation engine does not run.

## Operating Principle

- Core valuation data has higher priority than context enrichment.
- Macro and peer inputs are part of the core valuation-support path.
- News and filings may degrade without blocking deterministic valuation.

## Current Practical Limitations

1. Not every category has the same richness of primary and secondary source options.
2. Peer metrics are still subject to upstream rate-limit behavior on free-tier services.
3. Local snapshots are intended as the final fallback for demo continuity, not the preferred production path.
