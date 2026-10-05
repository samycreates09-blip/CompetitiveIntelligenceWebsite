-- 09_unstructured_documents.sql
-- RAG foundation: stores synthetic/demo unstructured competitor documents
-- (promotion terms, eligibility conditions, plan descriptions) and their
-- chunk-level embeddings for semantic retrieval. Exact prices, dates, and
-- other structured facts continue to come from the deterministic tables
-- above, not from this vector store.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS competitor_documents (
    document_id BIGSERIAL PRIMARY KEY,
    competitor_id BIGINT NOT NULL REFERENCES competitors(competitor_id) ON DELETE RESTRICT,
    title VARCHAR(255) NOT NULL,
    document_type VARCHAR(100) NOT NULL,
    source_label VARCHAR(50) NOT NULL DEFAULT 'synthetic_demo',
    captured_date DATE NOT NULL,
    raw_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_competitor_documents_source_label CHECK (source_label IN ('synthetic_demo'))
);

CREATE INDEX IF NOT EXISTS idx_competitor_documents_competitor_id ON competitor_documents(competitor_id);

-- 768 dimensions: gemini-embedding-001 output truncated via output_dimensionality,
-- chosen so the column stays well under pgvector's indexable dimension limit.
CREATE TABLE IF NOT EXISTS document_chunks (
    chunk_id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES competitor_documents(document_id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(768) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_document_chunks_document_chunk UNIQUE (document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON document_chunks(document_id);

-- No ANN index (ivfflat/hnsw) is created: the synthetic demo corpus is a
-- handful of documents and a few dozen chunks, so an exact sequential-scan
-- cosine-distance search (ORDER BY embedding <=> query LIMIT k) is both
-- simpler and fast enough. Add an index only if the corpus grows materially.
