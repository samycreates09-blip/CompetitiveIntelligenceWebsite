"""Run the deterministic RAG retrieval evaluation against the real ingested
documents, using real embedding calls. This is a manual validation step (like
`ingest_documents.py`), not part of the pytest suite, which mocks embeddings
to stay network-free:

    cd backend && source ../.venv/bin/activate && python -m scripts.run_rag_evaluation
"""
from __future__ import annotations

from app.config import settings
from app.database import engine
from app.services.rag_evaluation import RetrievalEvalCase, evaluate_retrieval
from app.services.retrieval_service import embed_query, search_chunks

VERIZON_DOC = "Verizon iPhone 15 Pro Trade-In Bonus — Eligibility and Conditions"
TMOBILE_DOC = "T-Mobile 5G Home and Mobile Combo — Promotion Terms"
BOOST_DOC = "Boost Unlimited Plan and Launch Offer — Plan and Promotion Details"

EVAL_CASES = [
    RetrievalEvalCase("What are the eligibility requirements for Verizon's device promotion?", VERIZON_DOC, competitor_ids=[3]),
    RetrievalEvalCase("Does the Verizon promotion require a new line?", VERIZON_DOC, competitor_ids=[3]),
    RetrievalEvalCase("What conditions apply to T-Mobile's promotion?", TMOBILE_DOC, competitor_ids=[2]),
    RetrievalEvalCase("Summarize the terms of Boost's promotion.", BOOST_DOC, competitor_ids=[1]),
    RetrievalEvalCase("How is the Verizon trade-in bill credit actually applied to my bill?", VERIZON_DOC, competitor_ids=[3]),
    RetrievalEvalCase("What happens if I cancel AutoPay during Boost's launch offer?", BOOST_DOC, competitor_ids=[1]),
]

OFF_TOPIC_QUESTION = "What are the eligibility rules for Boost's satellite texting feature?"


def main() -> None:
    if not settings.gemini_api_key:
        raise SystemExit("GEMINI_API_KEY is not configured; cannot generate embeddings.")

    def embed_fn(question: str):
        return embed_query(question, settings.gemini_api_key, settings.gemini_embedding_model)

    with engine.connect() as conn:
        report = evaluate_retrieval(conn, EVAL_CASES, embed_fn)
        print(f"Retrieval recall@3: {report['recall_at_k']} ({report['hits']}/{report['total']}), passed={report['passed']}")
        for case in report["cases"]:
            mark = "HIT " if case["hit"] else "MISS"
            print(f"  [{mark}] {case['question']}")
            print(f"         expected: {case['expected_document_title']}")
            print(f"         retrieved: {case['retrieved_titles']} (top distance={case['top_distance']})")

        print()
        print("Hallucination guard check (off-topic question, no matching document):")
        off_topic_vector = embed_fn(OFF_TOPIC_QUESTION)
        off_topic_matches = search_chunks(conn, off_topic_vector, top_k=3)
        print(f"  Question: {OFF_TOPIC_QUESTION}")
        print(f"  Matches above relevance threshold: {len(off_topic_matches)} (expected 0)")


if __name__ == "__main__":
    main()
