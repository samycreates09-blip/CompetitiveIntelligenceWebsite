from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.services.embedding_provider import embed_texts

DOCUMENTS_DIR = Path(__file__).resolve().parents[3] / "database" / "documents"
EMBEDDING_MODEL_DEFAULT = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768
MAX_CHUNK_CHARS = 500


@dataclass(frozen=True)
class ParsedDocument:
    competitor_short_name: str
    title: str
    document_type: str
    source_label: str
    captured_date: str
    body: str
    filename: str


def parse_document_file(path: Path) -> ParsedDocument:
    """Parse a `key: value` front-matter block followed by a `---` line and body text."""
    raw = path.read_text()
    header, separator, body = raw.partition("\n---\n")
    if not separator:
        raise ValueError(f"{path.name}: missing '---' front-matter separator.")
    fields: Dict[str, str] = {}
    for line in header.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip().lower()] = value.strip()
    required = ("competitor", "title", "document_type", "captured_date")
    missing = [field for field in required if not fields.get(field)]
    if missing:
        raise ValueError(f"{path.name}: missing required front-matter field(s): {', '.join(missing)}.")
    return ParsedDocument(
        competitor_short_name=fields["competitor"],
        title=fields["title"],
        document_type=fields["document_type"],
        source_label=fields.get("source_label", "synthetic_demo"),
        captured_date=fields["captured_date"],
        body=body.strip(),
        filename=path.name,
    )


def _split_oversized_paragraph(paragraph: str, max_chars: int) -> List[str]:
    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
    chunks: List[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip()
        if len(candidate) <= max_chars or not current:
            current = candidate
        else:
            chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks


def chunk_text(body: str, max_chars: int = MAX_CHUNK_CHARS) -> List[str]:
    """Greedily group paragraphs into chunks up to `max_chars`, splitting oversized
    paragraphs on sentence boundaries. No overlap is used: the synthetic demo
    documents are short, and each chunk is already a coherent paragraph group,
    so overlap would mostly just duplicate near-identical chunks in the index."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    chunks: List[str] = []
    current = ""
    for paragraph in paragraphs:
        pieces = (
            _split_oversized_paragraph(paragraph, max_chars)
            if len(paragraph) > max_chars
            else [paragraph]
        )
        for piece in pieces:
            candidate = f"{current}\n\n{piece}".strip() if current else piece
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = piece
    if current:
        chunks.append(current)
    return chunks


def _vector_literal(vector: List[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"


def ingest_all_documents(
    conn: Connection,
    api_key: str,
    embedding_model: str = EMBEDDING_MODEL_DEFAULT,
    documents_dir: Path = DOCUMENTS_DIR,
) -> Dict[str, Any]:
    """Idempotently (re-)ingest every `*.md` document in `documents_dir`.

    Re-running this replaces each document's rows (matched by competitor + title)
    so editing a source file and re-ingesting does not leave stale chunks behind.
    """
    competitor_rows = conn.execute(text("SELECT competitor_id, short_name FROM competitors")).mappings().all()
    competitor_lookup = {row["short_name"]: row["competitor_id"] for row in competitor_rows}

    documents = [parse_document_file(path) for path in sorted(documents_dir.glob("*.md"))]
    unknown = [doc.filename for doc in documents if doc.competitor_short_name not in competitor_lookup]
    if unknown:
        raise ValueError(f"Unknown competitor short_name in document(s): {unknown}")

    summary: Dict[str, Any] = {"documents": 0, "chunks": 0, "titles": []}
    for doc in documents:
        competitor_id = competitor_lookup[doc.competitor_short_name]
        conn.execute(
            text("DELETE FROM competitor_documents WHERE competitor_id = :cid AND title = :title"),
            {"cid": competitor_id, "title": doc.title},
        )
        document_id = conn.execute(
            text(
                """
                INSERT INTO competitor_documents (competitor_id, title, document_type, source_label, captured_date, raw_text)
                VALUES (:cid, :title, :doc_type, :source_label, :captured_date, :raw_text)
                RETURNING document_id
                """
            ),
            {
                "cid": competitor_id,
                "title": doc.title,
                "doc_type": doc.document_type,
                "source_label": doc.source_label,
                "captured_date": doc.captured_date,
                "raw_text": doc.body,
            },
        ).scalar_one()

        chunks = chunk_text(doc.body)
        vectors = embed_texts(
            chunks,
            api_key=api_key,
            model=embedding_model,
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=EMBEDDING_DIMENSIONS,
        )
        for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
            conn.execute(
                text(
                    """
                    INSERT INTO document_chunks (document_id, chunk_index, chunk_text, embedding)
                    VALUES (:doc_id, :idx, :chunk_text, CAST(:embedding AS vector))
                    """
                ),
                {"doc_id": document_id, "idx": index, "chunk_text": chunk, "embedding": _vector_literal(vector)},
            )
        summary["documents"] += 1
        summary["chunks"] += len(chunks)
        summary["titles"].append(doc.title)

    return summary
