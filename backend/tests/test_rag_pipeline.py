import dataclasses
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.database import engine
from app.main import app
from app.services import chat_context, chat_service, rag_evaluation
from app.services.briefing_service import BriefingConfiguration
from app.services.document_ingestion import chunk_text, parse_document_file
from app.services.rag_evaluation import RetrievalEvalCase, evaluate_chat_groundedness, evaluate_unsupported_refusal

client = TestClient(app)


# ---- Chunking / parsing (pure functions, no DB or network) ----

def test_chunk_text_groups_paragraphs_under_the_limit():
    body = "Paragraph one is short.\n\nParagraph two is also short.\n\nParagraph three too."
    chunks = chunk_text(body, max_chars=60)
    assert len(chunks) > 1
    assert all(len(chunk) <= 60 for chunk in chunks)
    assert "Paragraph one is short." in chunks[0]


def test_chunk_text_splits_an_oversized_paragraph_on_sentence_boundaries():
    sentence = "This is one sentence of real content. "
    oversized_paragraph = sentence * 20
    chunks = chunk_text(oversized_paragraph, max_chars=100)
    assert len(chunks) > 1
    assert all(len(chunk) <= 100 for chunk in chunks)
    original_words = oversized_paragraph.split()
    rejoined_words = " ".join(chunks).split()
    assert rejoined_words == original_words


def test_parse_document_file_reads_front_matter_and_body(tmp_path):
    path = tmp_path / "doc.md"
    path.write_text(
        "competitor: Verizon\n"
        "title: Example Title\n"
        "document_type: promotion_terms\n"
        "captured_date: 2026-09-10\n"
        "---\n"
        "Body paragraph one.\n\nBody paragraph two.\n"
    )
    parsed = parse_document_file(path)
    assert parsed.competitor_short_name == "Verizon"
    assert parsed.title == "Example Title"
    assert parsed.source_label == "synthetic_demo"
    assert parsed.body == "Body paragraph one.\n\nBody paragraph two."


def test_parse_document_file_rejects_missing_front_matter_fields(tmp_path):
    path = tmp_path / "bad.md"
    path.write_text("competitor: Verizon\n---\nBody only.")
    with pytest.raises(ValueError):
        parse_document_file(path)


# ---- Deterministic routing: RAG keywords add "documents" without disturbing existing categories ----

def test_routing_adds_documents_category_for_eligibility_questions():
    competitors = [
        {"competitor_id": 1, "name": "Boost Mobile", "short_name": "Boost"},
        {"competitor_id": 2, "name": "T-Mobile", "short_name": "T-Mobile"},
        {"competitor_id": 3, "name": "Verizon", "short_name": "Verizon"},
    ]
    route = chat_context.route_question("What are the eligibility requirements for Verizon's device promotion?", competitors)
    assert "documents" in route["categories"]
    assert route["competitor_ids"] == [3]

    route2 = chat_context.route_question("Does the Verizon promotion require a new line?", competitors)
    assert "documents" in route2["categories"]

    route3 = chat_context.route_question("Summarize the terms of Boost's promotion.", competitors)
    assert "documents" in route3["categories"]
    assert "promotions" in route3["categories"]


def test_routing_leaves_pure_structured_questions_rag_free():
    competitors = [{"competitor_id": 2, "name": "T-Mobile", "short_name": "T-Mobile"}]
    route = chat_context.route_question("What is T-Mobile Essentials currently priced at?", competitors)
    assert route["categories"] == ["plans"]
    assert "documents" not in route["categories"]


# ---- assemble_chat_context: mock retrieval directly, no embedding calls ----

def test_assemble_chat_context_includes_document_sources_for_rag_question(monkeypatch):
    fake_chunk = {
        "chunk_id": 1,
        "document_id": 3,
        "chunk_index": 1,
        "chunk_text": "Eligibility requirements: the customer must open a new line of service...",
        "title": "Verizon iPhone 15 Pro Trade-In Bonus — Eligibility and Conditions",
        "document_type": "promotion_terms",
        "source_label": "synthetic_demo",
        "captured_date": "2026-09-10",
        "competitor_id": 3,
        "competitor_name": "Verizon",
        "distance": 0.27,
    }
    monkeypatch.setattr(chat_context, "embed_query", lambda *_args, **_kwargs: [0.0])
    monkeypatch.setattr(chat_context, "search_chunks", lambda *_args, **_kwargs: [fake_chunk])
    monkeypatch.setattr(chat_context, "settings", dataclasses.replace(chat_context.settings, gemini_api_key="test-key"))

    with engine.connect() as conn:
        context = chat_context.assemble_chat_context(conn, "What are the eligibility requirements for Verizon's device promotion?")

    assert context["sufficient"]
    doc_sources = [s for s in context["sources"] if s["category"] == "document_chunk"]
    assert len(doc_sources) == 1
    assert doc_sources[0]["source_id"] == "DOC-3-1"
    assert doc_sources[0]["record_origin"] == "synthetic_document"
    assert context["data_scope"]["document_sources_included"] is True
    assert "Verizon" in context["data_scope"]["competitors"]


def test_assemble_chat_context_skips_retrieval_when_embedding_not_configured(monkeypatch):
    called = []
    monkeypatch.setattr(chat_context, "search_chunks", lambda *_a, **_k: called.append(True))
    monkeypatch.setattr(chat_context, "settings", dataclasses.replace(chat_context.settings, gemini_api_key=""))

    with engine.connect() as conn:
        context = chat_context.assemble_chat_context(conn, "What conditions apply to T-Mobile's promotion?")

    assert called == []
    assert all(s["category"] != "document_chunk" for s in context["sources"])


def test_assemble_chat_context_degrades_gracefully_on_embedding_failure(monkeypatch):
    from app.services.embedding_provider import EmbeddingProviderError

    def boom(*_args, **_kwargs):
        raise EmbeddingProviderError("provider unavailable")

    monkeypatch.setattr(chat_context, "embed_query", boom)
    monkeypatch.setattr(chat_context, "settings", dataclasses.replace(chat_context.settings, gemini_api_key="test-key"))

    with engine.connect() as conn:
        context = chat_context.assemble_chat_context(conn, "What conditions apply to T-Mobile's promotion?")

    assert all(s["category"] != "document_chunk" for s in context["sources"])


def test_hybrid_question_combines_structured_and_document_sources(monkeypatch):
    fake_chunk = {
        "chunk_id": 2, "document_id": 3, "chunk_index": 0,
        "chunk_text": "Trade-in device requirements: ...",
        "title": "Verizon iPhone 15 Pro Trade-In Bonus — Eligibility and Conditions",
        "document_type": "promotion_terms", "source_label": "synthetic_demo",
        "captured_date": "2026-09-10", "competitor_id": 3, "competitor_name": "Verizon",
        "distance": 0.28,
    }
    monkeypatch.setattr(chat_context, "embed_query", lambda *_a, **_k: [0.0])
    monkeypatch.setattr(chat_context, "search_chunks", lambda *_a, **_k: [fake_chunk])
    monkeypatch.setattr(chat_context, "settings", dataclasses.replace(chat_context.settings, gemini_api_key="test-key"))

    with engine.connect() as conn:
        context = chat_context.assemble_chat_context(
            conn, "How much does the Verizon plan cost and what conditions apply to its iPhone promotion?"
        )

    categories_with_sources = {s["category"] for s in context["sources"]}
    assert "current_plan" in categories_with_sources
    assert "document_chunk" in categories_with_sources


# ---- Full chat endpoint: mocked Gemini, mocked retrieval ----

def test_chat_endpoint_answers_rag_question_with_document_sources(monkeypatch):
    monkeypatch.setattr(
        chat_service, "load_chat_configuration",
        lambda: BriefingConfiguration(api_key="not-a-real-test-key", model="test-model"),
    )
    fake_chunk = {
        "chunk_id": 1, "document_id": 1, "chunk_index": 2,
        "chunk_text": "Eligibility requirements: the account must enroll in AutoPay...",
        "title": "Boost Unlimited Plan and Launch Offer — Plan and Promotion Details",
        "document_type": "plan_and_promotion_terms", "source_label": "synthetic_demo",
        "captured_date": "2026-09-15", "competitor_id": 1, "competitor_name": "Boost Mobile",
        "distance": 0.24,
    }
    monkeypatch.setattr(chat_context, "embed_query", lambda *_a, **_k: [0.0])
    monkeypatch.setattr(chat_context, "search_chunks", lambda *_a, **_k: [fake_chunk])
    monkeypatch.setattr(chat_context, "settings", dataclasses.replace(chat_context.settings, gemini_api_key="test-key"))

    captured = {}

    def fake_answer(question, context_json, _key, model):
        context = json.loads(context_json)
        captured["context"] = context
        doc_source = next(s for s in context["sources"] if s["category"] == "document_chunk")
        return f"Boost's launch offer requires AutoPay enrollment [{doc_source['source_id']}]."

    monkeypatch.setattr(chat_service, "generate_chat_answer", fake_answer)
    response = client.post("/api/v1/ai/chat", json={"message": "Summarize the terms of Boost's promotion."})

    assert response.status_code == 200
    payload = response.json()
    assert "AutoPay" in payload["answer"]
    assert any(s["category"] == "document_chunk" for s in payload["sources"])
    assert any(s["record_origin"] == "synthetic_document" for s in payload["sources"])
    assert payload["data_scope"]["document_sources_included"] is True


def test_chat_endpoint_structured_only_question_has_no_document_sources(monkeypatch):
    monkeypatch.setattr(
        chat_service, "load_chat_configuration",
        lambda: BriefingConfiguration(api_key="not-a-real-test-key", model="test-model"),
    )
    called = []
    monkeypatch.setattr(chat_context, "search_chunks", lambda *_a, **_k: called.append(True))
    monkeypatch.setattr(chat_service, "generate_chat_answer", lambda *_a: "T-Mobile Essentials currently costs $65.00 per month [PLAN-201].")

    response = client.post("/api/v1/ai/chat", json={"message": "What is T-Mobile Essentials currently priced at?"})
    assert response.status_code == 200
    assert called == []
    assert all(s["category"] != "document_chunk" for s in response.json()["sources"])


# ---- RAG evaluation framework: fully mocked embeddings, zero live calls ----

FAKE_EMBEDDINGS = {
    "verizon trade-in eligibility": [1.0, 0.0, 0.0],
    "boost autopay terms": [0.0, 1.0, 0.0],
    "irrelevant question": [0.0, 0.0, 1.0],
}


def test_evaluate_retrieval_reports_hit_rate_with_mocked_embeddings(monkeypatch):
    def fake_embed(question: str):
        return FAKE_EMBEDDINGS[question]

    def fake_search_chunks(_conn, query_vector, top_k=3, competitor_ids=None, max_distance=0.45):
        if query_vector == [1.0, 0.0, 0.0]:
            return [{"title": "Verizon Doc", "distance": 0.1}]
        if query_vector == [0.0, 1.0, 0.0]:
            return [{"title": "Boost Doc", "distance": 0.1}]
        return []

    monkeypatch.setattr(rag_evaluation, "search_chunks", fake_search_chunks)
    cases = [
        RetrievalEvalCase("verizon trade-in eligibility", "Verizon Doc"),
        RetrievalEvalCase("boost autopay terms", "Boost Doc"),
        RetrievalEvalCase("irrelevant question", "Verizon Doc"),
    ]
    with engine.connect() as conn:
        report = rag_evaluation.evaluate_retrieval(conn, cases, fake_embed)

    assert report["hits"] == 2
    assert report["total"] == 3
    assert report["recall_at_k"] == pytest.approx(0.67, rel=0.02)
    assert report["passed"] is False
    assert report["cases"][2]["hit"] is False


def test_evaluate_chat_groundedness_flags_citations_not_in_supplied_sources():
    sources = [{"source_id": "DOC-3-1"}, {"source_id": "PLAN-201"}]
    grounded = evaluate_chat_groundedness("Price is $65 [PLAN-201].", sources)
    assert grounded["passed"] is True
    assert grounded["invalid_citations"] == []

    hallucinated = evaluate_chat_groundedness("Price is $65 [PLAN-999].", sources)
    assert hallucinated["passed"] is False
    assert hallucinated["invalid_citations"] == ["PLAN-999"]


def test_evaluate_unsupported_refusal_detects_declined_answers():
    assert evaluate_unsupported_refusal("The tracked data does not contain enough information to answer that.")["passed"] is True
    assert evaluate_unsupported_refusal("Verizon's promotion requires a 24-month contract.")["passed"] is False


def test_unstructured_rag_architecture_is_documented():
    documentation = Path(__file__).resolve().parents[2] / "docs" / "future_unstructured_data.md"
    text = documentation.read_text()
    assert "pgvector" in text
    assert "Structured path" in text
    assert "RAG path" in text
    assert "Hybrid path" in text
