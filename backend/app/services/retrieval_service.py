from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Connection

from app.services.embedding_provider import embed_texts

EMBEDDING_MODEL_DEFAULT = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768
DEFAULT_TOP_K = 4

# Cosine distance (pgvector `<=>`) above this is treated as "not relevant enough"
# rather than fed to the LLM as grounded context. This is the deterministic
# guard against the RAG path supplying noisy, unrelated passages: software
# decides relevance, not the LLM. Chosen empirically against the synthetic demo
# corpus: genuinely on-topic chunks land around 0.23-0.28, while chunks from
# the wrong document land around 0.33+, so 0.45 keeps true matches with margin
# while still rejecting clearly unrelated passages.
MAX_RELEVANT_DISTANCE = 0.45


def embed_query(question: str, api_key: str, model: str = EMBEDDING_MODEL_DEFAULT) -> List[float]:
    vectors = embed_texts(
        [question],
        api_key=api_key,
        model=model,
        task_type="RETRIEVAL_QUERY",
        output_dimensionality=EMBEDDING_DIMENSIONS,
    )
    return vectors[0]


def _vector_literal(vector: List[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"


def search_chunks(
    conn: Connection,
    query_vector: List[float],
    top_k: int = DEFAULT_TOP_K,
    competitor_ids: Optional[List[int]] = None,
    max_distance: float = MAX_RELEVANT_DISTANCE,
) -> List[Dict[str, Any]]:
    """Return the top-k most similar document chunks, filtered to a relevance
    threshold and optionally restricted to a set of competitor IDs."""
    sql = """
        SELECT
            dc.chunk_id, dc.document_id, dc.chunk_index, dc.chunk_text,
            cd.title, cd.document_type, cd.source_label, cd.captured_date,
            cd.competitor_id, c.name AS competitor_name,
            (dc.embedding <=> CAST(:embedding AS vector)) AS distance
        FROM document_chunks dc
        JOIN competitor_documents cd ON cd.document_id = dc.document_id
        JOIN competitors c ON c.competitor_id = cd.competitor_id
    """
    params: Dict[str, Any] = {"embedding": _vector_literal(query_vector), "top_k": top_k}
    if competitor_ids:
        sql += " WHERE cd.competitor_id IN :competitor_ids "
        params["competitor_ids"] = competitor_ids
    sql += " ORDER BY distance ASC LIMIT :top_k"
    statement = text(sql)
    if competitor_ids:
        statement = statement.bindparams(bindparam("competitor_ids", expanding=True))
    rows = conn.execute(statement, params).mappings().all()
    return [dict(row) for row in rows if row["distance"] <= max_distance]
