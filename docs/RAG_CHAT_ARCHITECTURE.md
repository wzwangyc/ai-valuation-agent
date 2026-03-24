# RAG Chat Architecture

This project uses a report-grounded retrieval workflow for the chat assistant.

## Objective

The chat agent must explain the valuation report, DCF mechanics, peer analysis, validation findings, and evidence sources without inventing facts outside the generated report.

## Retrieval Pipeline

1. **Report Load**
   - Input source: generated valuation report JSON in `output/<TICKER>_valuation.json`
   - The chat layer does not read arbitrary external documents at answer time.

2. **Document Build**
   - The report is transformed into structured retrieval documents:
     - company info
     - market snapshot
     - financial data
     - DCF formulae
     - WACC details
     - forecast table
     - valuation bridge
     - comparable analysis
     - validation agents
     - contextual evidence
     - full report context

3. **Chunking**
   - Documents are split into overlapping chunks.
   - Current implementation uses:
     - chunk size: 1400 characters
     - overlap: 160 characters
   - This keeps local retrieval simple while preserving neighboring context.

4. **Retrieval**
   - The primary retrieval path is embedding-based semantic search.
   - Chunk vectors are generated with a local `sentence-transformers` model.
   - Vectors are persisted under `output/chat_index/` as a local vector store keyed by ticker and report hash.
   - Query-to-chunk ranking uses cosine similarity on normalized embeddings.
   - A lexical fallback remains in place when semantic retrieval is unavailable.

5. **Answer Generation**
   - If the answer can be resolved deterministically from the report, the system responds directly without an LLM call.
   - If an external LLM is configured, the model receives only the retrieved chunks.
   - The system prompt requires:
     - English-only output
     - source-grounded responses
     - no hallucinated facts
     - explicit refusal when the report lacks evidence

## Anti-Hallucination Guardrails

- The agent answers only from retrieved report evidence.
- When evidence is insufficient, the required fallback answer is:
  - `I cannot answer this as the data is not present in the valuation report.`
- Citations and retrieved report sections are returned with each answer payload.
- Deterministic direct answers are used for common questions such as:
  - WACC
  - target price
  - Year-N UFCF
  - valuation methodology
  - assistant identity

## Current Implementation Boundaries

- The vector store is a local persisted index, not an external distributed database.
- The current stack does not yet add a separate reranking stage after top-k retrieval.
- This is a valid semantic RAG design for a single-report workstation workflow, but not yet a multi-tenant production search service.

## Recommended Upgrade Path

To reach a fuller production RAG design:

1. Add reranking on retrieved top-k chunks.
2. Replace the local persisted store with a dedicated vector database when multi-user scale is needed.
3. Add regression tests for answer faithfulness and citation coverage.
