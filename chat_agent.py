"""Report-grounded chat agent with explicit retrieval, embeddings, and source citations."""

from __future__ import annotations

import json
import logging
import os
import re
from functools import lru_cache
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import requests

logger = logging.getLogger(__name__)


@dataclass
class ChatDocument:
    """Single retrievable document unit for report-grounded QA."""

    doc_id: str
    section: str
    text: str
    citations: List[Dict[str, Any]]


@dataclass
class ChatChunk:
    """Smaller retrievable chunk derived from a report document."""

    chunk_id: str
    section: str
    text: str
    citations: List[Dict[str, Any]]


@dataclass
class VectorSearchResult:
    """Retrieved chunk with vector similarity score."""

    chunk: ChatChunk
    score: float


EMBEDDING_MODEL_NAME = os.getenv("CHAT_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
VECTOR_INDEX_DIR = os.path.join(os.path.dirname(__file__), "output", "chat_index")
VECTOR_SCORE_THRESHOLD = float(os.getenv("CHAT_VECTOR_SCORE_THRESHOLD", "0.18"))


def _load_report(ticker: str) -> Dict[str, Any]:
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    json_path = os.path.join(output_dir, f"{ticker.upper()}_valuation.json")
    if not os.path.exists(json_path):
        return {}
    with open(json_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _normalize_text(text: Any) -> str:
    if text is None:
        return ""
    if isinstance(text, str):
        return text
    return json.dumps(text, ensure_ascii=False)


def _report_hash(report: Dict[str, Any]) -> str:
    normalized = json.dumps(report or {}, ensure_ascii=False, sort_keys=True)
    return str(abs(hash(normalized)))


def _tokenize(text: str) -> List[str]:
    text = (text or "").lower()
    return re.findall(r"[\u4e00-\u9fff]|[a-z0-9_]+", text)


def _make_document(section: str, text: Any, citations: Optional[List[Dict[str, Any]]] = None) -> Optional[ChatDocument]:
    normalized = _normalize_text(text).strip()
    if normalized in {"", "[]", "{}", "null"}:
        return None
    return ChatDocument(
        doc_id=section,
        section=section,
        text=normalized,
        citations=citations or [],
    )


@lru_cache(maxsize=2)
def _get_embedding_model() -> Any:
    """Load a local sentence-transformer model for semantic retrieval."""
    os.environ.setdefault("USE_TF", "0")
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def _index_paths(ticker: str) -> Dict[str, str]:
    safe = (ticker or "UNKNOWN").upper()
    return {
        "meta": os.path.join(VECTOR_INDEX_DIR, f"{safe}_index_meta.json"),
        "vectors": os.path.join(VECTOR_INDEX_DIR, f"{safe}_index_vectors.npy"),
    }


def _vectorize_texts(texts: List[str]) -> np.ndarray:
    model = _get_embedding_model()
    vectors = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
    return np.asarray(vectors, dtype=np.float32)


def _write_vector_index(ticker: str, report_hash: str, chunks: List[ChatChunk]) -> tuple[np.ndarray, List[Dict[str, Any]]]:
    os.makedirs(VECTOR_INDEX_DIR, exist_ok=True)
    vectors = _vectorize_texts([chunk.text for chunk in chunks])
    metadata = [
        {
            "chunk_id": chunk.chunk_id,
            "section": chunk.section,
            "text": chunk.text,
            "citations": chunk.citations,
        }
        for chunk in chunks
    ]
    paths = _index_paths(ticker)
    with open(paths["meta"], "w", encoding="utf-8") as handle:
        json.dump(
            {
                "report_hash": report_hash,
                "embedding_model": EMBEDDING_MODEL_NAME,
                "chunks": metadata,
            },
            handle,
            ensure_ascii=False,
        )
    np.save(paths["vectors"], vectors)
    return vectors, metadata


def _load_vector_index(ticker: str, report_hash: str) -> Optional[tuple[np.ndarray, List[Dict[str, Any]]]]:
    paths = _index_paths(ticker)
    if not os.path.exists(paths["meta"]) or not os.path.exists(paths["vectors"]):
        return None
    with open(paths["meta"], "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("report_hash") != report_hash or payload.get("embedding_model") != EMBEDDING_MODEL_NAME:
        return None
    vectors = np.load(paths["vectors"])
    chunks = payload.get("chunks", [])
    if len(vectors) != len(chunks):
        return None
    return np.asarray(vectors, dtype=np.float32), chunks


def _get_or_build_vector_index(ticker: str, report: Dict[str, Any], chunks: List[ChatChunk]) -> tuple[np.ndarray, List[Dict[str, Any]]]:
    report_hash = _report_hash(report)
    cached = _load_vector_index(ticker, report_hash)
    if cached is not None:
        return cached
    return _write_vector_index(ticker, report_hash, chunks)


def _restore_chunk(payload: Dict[str, Any]) -> ChatChunk:
    return ChatChunk(
        chunk_id=payload["chunk_id"],
        section=payload["section"],
        text=payload["text"],
        citations=payload.get("citations", []),
    )


def load_report_documents(report: Dict[str, Any]) -> List[ChatDocument]:
    """Build structured report documents for retrieval."""
    if not report:
        return []

    citations = report.get("citations", [])
    calculation = report.get("calculation_details", {})
    validation = report.get("validation_agents", {})
    contextual = report.get("contextual_data", {})
    report_agent = report.get("report_agent", {})

    docs = [
        _make_document(
            "assistant.identity",
            (
                "You are AI Valuation Terminal. You explain the valuation workflow, DCF mechanics, comparable-company analysis, "
                "validation findings, evidence provenance, and risk factors shown in the report."
            ),
            [],
        ),
        _make_document("meta", report.get("meta"), citations[:2]),
        _make_document("company_info", report.get("company_info"), citations[:2]),
        _make_document("market_snapshot", report.get("market_snapshot"), citations[:2]),
        _make_document("financial_data", report.get("financial_data"), citations[:2]),
        _make_document("report_agent.summary", report_agent.get("summary"), citations[:2]),
        _make_document("report_agent.core_assumptions", report_agent.get("core_assumptions"), citations[:2]),
        _make_document("calculation.formulae", calculation.get("formulae"), citations[:2]),
        _make_document("calculation.step_by_step", calculation.get("step_by_step"), citations[:2]),
        _make_document("calculation.wacc", calculation.get("wacc_details"), citations[:2]),
        _make_document("calculation.forecast", calculation.get("forecast_table"), citations[:2]),
        _make_document("calculation.discount_schedule", calculation.get("discount_schedule"), citations[:2]),
        _make_document("calculation.terminal_value", calculation.get("terminal_value"), citations[:2]),
        _make_document("calculation.valuation_bridge", calculation.get("valuation_bridge"), citations[:2]),
        _make_document("scenario_analysis", report.get("scenario_analysis"), citations[:2]),
        _make_document("sensitivity_analysis", report.get("sensitivity_analysis"), citations[:2]),
        _make_document("peer_group_analysis", report.get("peer_group_analysis"), citations),
        _make_document("comparable_analysis", report.get("comparable_analysis"), citations[:2]),
        _make_document("validation_agents", validation, citations[:2]),
        _make_document("risk_factors", report.get("risk_factors"), citations[:2]),
        _make_document("context.business_description", contextual.get("business_description"), citations[:2]),
        _make_document("context.recent_news", contextual.get("recent_news"), citations[2:]),
        _make_document("context.filing_excerpts", contextual.get("filing_excerpts"), citations[2:]),
        _make_document("context.call_excerpts", contextual.get("call_excerpts"), citations[2:]),
        _make_document("full_report_context", report, citations),
    ]
    return [doc for doc in docs if doc is not None]


def chunk_documents(
    documents: Iterable[ChatDocument],
    chunk_size: int = 1400,
    overlap: int = 160,
) -> List[ChatChunk]:
    """Split documents into retrievable chunks with overlap."""
    chunks: List[ChatChunk] = []
    for doc in documents:
        text = doc.text
        if len(text) <= chunk_size:
            chunks.append(ChatChunk(chunk_id=f"{doc.doc_id}#0", section=doc.section, text=text, citations=doc.citations))
            continue

        start = 0
        index = 0
        while start < len(text):
            end = min(len(text), start + chunk_size)
            chunk_text = text[start:end]
            chunks.append(
                ChatChunk(
                    chunk_id=f"{doc.doc_id}#{index}",
                    section=doc.section,
                    text=chunk_text,
                    citations=doc.citations,
                )
            )
            if end >= len(text):
                break
            start = max(0, end - overlap)
            index += 1
    return chunks


def _retrieve_lexical_chunks(report: Dict[str, Any], question: str, top_k: int = 8) -> List[ChatChunk]:
    """Fallback lexical retrieval against the current report."""
    documents = load_report_documents(report)
    chunks = chunk_documents(documents)
    q_terms = set(_tokenize(question))
    scored: List[tuple[int, ChatChunk]] = []

    for chunk in chunks:
        chunk_terms = set(_tokenize(chunk.text))
        overlap = len(q_terms & chunk_terms)
        substring_bonus = 1 if any(term and term in chunk.text.lower() for term in q_terms if len(term) > 1) else 0
        section_bonus = 1 if chunk.section in {
            "assistant.identity",
            "calculation.forecast",
            "calculation.wacc",
            "calculation.valuation_bridge",
            "full_report_context",
        } else 0
        score = overlap + substring_bonus + section_bonus
        if score > 0:
            scored.append((score, chunk))

    if not scored:
        priority_sections = {
            "assistant.identity",
            "calculation.formulae",
            "calculation.wacc",
            "calculation.forecast",
            "calculation.valuation_bridge",
            "validation_agents",
            "company_info",
            "financial_data",
            "full_report_context",
        }
        fallback = [chunk for chunk in chunks if chunk.section in priority_sections]
        return fallback[:top_k]

    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]


def retrieve_relevant_chunks(report: Dict[str, Any], ticker: str, question: str, top_k: int = 8) -> List[ChatChunk]:
    """Retrieve relevant chunks using sentence embeddings and a persisted local vector index."""
    documents = load_report_documents(report)
    chunks = chunk_documents(documents)
    if not chunks:
        return []

    try:
        vectors, metadata = _get_or_build_vector_index(ticker, report, chunks)
        query_vector = _vectorize_texts([question])[0]
        scores = vectors @ query_vector
        ranked_indices = np.argsort(scores)[::-1]

        results: List[VectorSearchResult] = []
        for idx in ranked_indices[:top_k * 2]:
            score = float(scores[idx])
            if score < VECTOR_SCORE_THRESHOLD:
                continue
            results.append(VectorSearchResult(chunk=_restore_chunk(metadata[int(idx)]), score=score))
            if len(results) >= top_k:
                break

        if results:
            return [result.chunk for result in results[:top_k]]
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as exc:
        # Semantic retrieval should degrade to lexical retrieval rather than break chat.
        logger.warning("Semantic retrieval unavailable for %s: %s", ticker, exc)

    return _retrieve_lexical_chunks(report, question, top_k=top_k)


def _base_citations(report: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
    return report.get("citations", [])[:limit]


def _find_forecast_row(report: Dict[str, Any], year: int) -> Optional[Dict[str, Any]]:
    rows = report.get("calculation_details", {}).get("forecast_table", []) or []
    for row in rows:
        if int(row.get("year", -1)) == year:
            return row
    return None


def _direct_answer(report: Dict[str, Any], question: str) -> Optional[Dict[str, Any]]:
    """Answer deterministic report questions without external LLM usage."""
    if not report:
        return None

    q = (question or "").strip().lower()
    q_compact = re.sub(r"\s+", "", q)
    company = report.get("company_info", {}).get("name") or report.get("meta", {}).get("ticker")
    ticker = report.get("meta", {}).get("ticker")
    wacc = report.get("calculation_details", {}).get("wacc_details", {}).get("wacc")
    valuation_bridge = report.get("calculation_details", {}).get("valuation_bridge", {})
    summary = report.get("report_agent", {}).get("summary", {})
    citations = _base_citations(report, 4)

    if any(token in q_compact for token in {"whoareyou", "whatcanyoudo"}) or "who are you" in q or "what can you do" in q:
        return {
            "answer": (
                "I am the AI Valuation Terminal report explainer. I answer questions about the full valuation report, "
                "including company context, financial data, DCF assumptions, WACC, UFCF forecasts, terminal value, "
                "valuation bridge, peer analysis, validation findings, risk factors, and source citations."
            ),
            "citations": citations[:2],
            "retrieved_sections": ["assistant.identity", "full_report_context"],
        }

    if "wacc" in q_compact:
        if wacc is None:
            return None
        detail = report.get("calculation_details", {}).get("wacc_details", {})
        return {
            "answer": (
                f"The report WACC is {round(float(wacc) * 100, 2):.2f}%. "
                f"It uses a risk-free rate of {round(float(detail.get('risk_free_rate', 0)) * 100, 2):.2f}%, "
                f"beta of {detail.get('beta', 'N/A')}, equity risk premium of {round(float(detail.get('equity_risk_premium', 0)) * 100, 2):.2f}%, "
                f"cost of equity of {round(float(detail.get('cost_of_equity', 0)) * 100, 2):.2f}%, "
                f"and cost of debt of {round(float(detail.get('cost_of_debt', 0)) * 100, 2):.2f}%."
            ),
            "citations": citations[:2],
            "retrieved_sections": ["calculation.wacc"],
        }

    for year in range(1, 6):
        if f"year{year}" in q_compact or f"year {year}" in q or f"ufcf{year}" in q_compact:
            row = _find_forecast_row(report, year)
            if row and "ufcf" in q_compact and row.get("ufcf") is not None:
                return {
                    "answer": (
                        f"Forecast Year {year} UFCF is {row['ufcf']:,.0f}. "
                        f"Revenue is {row.get('revenue', 0):,.0f}, EBIT is {row.get('ebit', 0):,.0f}, "
                        f"and NOPAT is {row.get('nopat', 0):,.0f}."
                    ),
                    "citations": citations[:2],
                    "retrieved_sections": ["calculation.forecast"],
                }

    if "targetprice" in q_compact or "fairprice" in q_compact or "target price" in q:
        target_price = summary.get("target_price") or valuation_bridge.get("fair_price_per_share")
        if target_price is not None:
            return {
                "answer": f"{company} ({ticker}) has a target price of {float(target_price):.2f}.",
                "citations": citations[:2],
                "retrieved_sections": ["report_agent.summary", "calculation.valuation_bridge"],
            }

    if any(token in q_compact for token in {"dcf", "algorithm", "methodology"}) or "how" in q:
        steps = report.get("calculation_details", {}).get("step_by_step", []) or []
        formulae = report.get("calculation_details", {}).get("formulae", []) or []
        if steps:
            return {
                "answer": (
                    "The report uses deterministic DCF logic. "
                    + " ".join(steps[:4])
                    + " The final equity value is converted into per-share value using "
                    + (formulae[-1] if formulae else "Target Price = Equity Value / Shares Outstanding")
                    + "."
                ),
                "citations": citations[:2],
                "retrieved_sections": ["calculation.step_by_step", "calculation.formulae"],
            }

    if "peer" in q_compact:
        peer_count = report.get("comparable_analysis", {}).get("peer_count")
        if peer_count is not None:
            return {
                "answer": f"The report currently includes {peer_count} comparable companies in the comparable analysis section.",
                "citations": citations[:2],
                "retrieved_sections": ["peer_group_analysis", "comparable_analysis"],
            }

    return None


def _fallback_response(report: Dict[str, Any], chunks: List[ChatChunk]) -> Dict[str, Any]:
    if not report:
        return {"answer": "No valuation report is available yet.", "citations": [], "retrieved_sections": []}
    if not chunks:
        return {
            "answer": "I cannot answer this as the data is not present in the valuation report.",
            "citations": [],
            "retrieved_sections": [],
        }
    return {
        "answer": (
            "I do not have an active external LLM call for this response, but I can still retrieve the most relevant "
            "sections from the valuation report."
        ),
        "citations": [citation for chunk in chunks for citation in chunk.citations][:6],
        "retrieved_sections": [chunk.section for chunk in chunks],
    }


def _call_openai_compatible(api_key: str, model: str, base_url: Optional[str], messages: List[Dict[str, str]]) -> str:
    endpoint = (base_url or "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
    response = requests.post(
        endpoint,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "temperature": 0},
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    return payload["choices"][0]["message"]["content"]


def _call_anthropic(api_key: str, model: str, messages: List[Dict[str, str]]) -> str:
    system = messages[0]["content"]
    user = messages[-1]["content"]
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": 1000,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    return "".join(block.get("text", "") for block in payload.get("content", []))


def _call_gemini(api_key: str, model: str, messages: List[Dict[str, str]]) -> str:
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    prompt = f"{messages[0]['content']}\n\n{messages[-1]['content']}"
    response = requests.post(
        endpoint,
        headers={"Content-Type": "application/json", "X-goog-api-key": api_key},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    candidates = payload.get("candidates", [])
    parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
    return "".join(part.get("text", "") for part in parts)


def _generate_answer(
    question: str,
    chunks: List[ChatChunk],
    api_key: Optional[str],
    model: Optional[str],
    base_url: Optional[str],
) -> Optional[str]:
    """Generate an answer strictly from retrieved evidence."""
    if not api_key or not model or not chunks:
        return None

    evidence = "\n\n".join(
        f"Section: {chunk.section}\nContent: {chunk.text}\nCitations: {json.dumps(chunk.citations, ensure_ascii=False)}"
        for chunk in chunks
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You are the AI Valuation Terminal chat explainer. "
                "Answer only from the retrieved report evidence. "
                "Always answer in English. "
                "Cite report sections and source URLs. "
                "If the evidence is insufficient, answer exactly: "
                "'I cannot answer this as the data is not present in the valuation report.'"
            ),
        },
        {
            "role": "user",
            "content": f"Question: {question}\n\nRetrieved evidence:\n{evidence}",
        },
    ]

    model_lower = model.lower()
    if "claude" in model_lower:
        return _call_anthropic(api_key, model, messages)
    if "gemini" in model_lower:
        return _call_gemini(api_key, model, messages)
    return _call_openai_compatible(api_key, model, base_url, messages)


def chat_with_report(
    ticker: str,
    question: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Run report-grounded QA with deterministic retrieval and optional LLM generation."""
    report = _load_report(ticker)

    direct = _direct_answer(report, question)
    if direct:
        return direct

    chunks = retrieve_relevant_chunks(report, ticker, question)
    fallback = _fallback_response(report, chunks)
    if not api_key or not model or not chunks:
        return fallback

    try:
        answer = _generate_answer(question, chunks, api_key, model, base_url)
        return {
            "answer": answer,
            "citations": [citation for chunk in chunks for citation in chunk.citations][:6],
            "retrieved_sections": [chunk.section for chunk in chunks],
        }
    except (requests.RequestException, KeyError, ValueError, TypeError) as exc:
        response = fallback.copy()
        response["answer"] = f"{fallback['answer']}\n\nLLM request failed: {exc}"
        return response
