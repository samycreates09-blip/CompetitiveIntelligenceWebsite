"""One-time/idempotent build step: embed the synthetic demo documents in
database/documents/ and load them into competitor_documents/document_chunks.

This is a provisioning step (like the SQL seed files), not a test — it makes
a small number of real embedding API calls. Run it manually after editing or
adding a document:

    cd backend && source ../.venv/bin/activate && python -m scripts.ingest_documents
"""
from __future__ import annotations

from app.config import settings
from app.database import engine
from app.services.document_ingestion import ingest_all_documents


def main() -> None:
    if not settings.gemini_api_key:
        raise SystemExit("GEMINI_API_KEY is not configured; cannot generate embeddings.")
    with engine.begin() as conn:
        summary = ingest_all_documents(conn, api_key=settings.gemini_api_key, embedding_model=settings.gemini_embedding_model)
    print(f"Ingested {summary['documents']} document(s), {summary['chunks']} chunk(s):")
    for title in summary["titles"]:
        print(f"  - {title}")


if __name__ == "__main__":
    main()
