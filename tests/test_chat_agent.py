import numpy as np

from chat_agent import chunk_documents, chat_with_report, load_report_documents, retrieve_relevant_chunks


def _sample_report():
    return {
        "meta": {"ticker": "TEST"},
        "company_info": {"name": "Test Corp"},
        "citations": [{"label": "Yahoo", "url": "https://example.com"}],
        "calculation_details": {
            "wacc_details": {
                "wacc": 0.1033,
                "risk_free_rate": 0.0425,
                "beta": 1.1,
                "equity_risk_premium": 0.055,
                "cost_of_equity": 0.103,
                "cost_of_debt": 0.06,
            },
            "forecast_table": [
                {"year": 2, "ufcf": 2000, "revenue": 10000, "ebit": 3000, "nopat": 2400},
            ],
            "step_by_step": ["Forecast revenue", "Forecast EBIT", "Forecast UFCF", "Discount cash flows"],
            "formulae": ["Target Price = Equity Value / Shares Outstanding"],
            "valuation_bridge": {"fair_price_per_share": 123.45},
        },
        "report_agent": {"summary": {"target_price": 123.45}},
    }


def test_load_and_chunk_report_documents() -> None:
    documents = load_report_documents(_sample_report())
    chunks = chunk_documents(documents, chunk_size=120, overlap=20)
    assert documents
    assert chunks


def test_chat_direct_answer_for_wacc(monkeypatch) -> None:
    monkeypatch.setattr("chat_agent._load_report", lambda ticker: _sample_report())
    response = chat_with_report("TEST", "what is the wacc")
    assert "10.33%" in response["answer"]
    assert response["retrieved_sections"] == ["calculation.wacc"]


def test_chat_direct_answer_for_identity(monkeypatch) -> None:
    monkeypatch.setattr("chat_agent._load_report", lambda ticker: _sample_report())
    response = chat_with_report("TEST", "who are you")
    assert "AI Valuation Terminal" in response["answer"]


def test_retrieve_relevant_chunks_uses_vector_index(monkeypatch) -> None:
    report = _sample_report()
    fake_vectors = np.array(
        [
            [0.0, 1.0],
            [1.0, 0.0],
        ],
        dtype=np.float32,
    )
    fake_metadata = [
        {
            "chunk_id": "assistant.identity#0",
            "section": "assistant.identity",
            "text": "Identity section",
            "citations": [],
        },
        {
            "chunk_id": "calculation.wacc#0",
            "section": "calculation.wacc",
            "text": "WACC section",
            "citations": [],
        },
    ]

    monkeypatch.setattr("chat_agent._get_or_build_vector_index", lambda ticker, report, chunks: (fake_vectors, fake_metadata))
    monkeypatch.setattr("chat_agent._vectorize_texts", lambda texts: np.array([[1.0, 0.0]], dtype=np.float32))

    chunks = retrieve_relevant_chunks(report, "TEST", "what is the wacc", top_k=1)
    assert len(chunks) == 1
    assert chunks[0].section == "calculation.wacc"


def test_retrieve_relevant_chunks_falls_back_to_lexical(monkeypatch) -> None:
    report = _sample_report()
    monkeypatch.setattr("chat_agent._get_or_build_vector_index", lambda ticker, report, chunks: (_ for _ in ()).throw(OSError("index unavailable")))
    chunks = retrieve_relevant_chunks(report, "TEST", "what is the wacc", top_k=3)
    assert chunks
