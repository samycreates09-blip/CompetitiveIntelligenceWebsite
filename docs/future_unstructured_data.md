# Unstructured competitor data: RAG architecture

The product now has three question-answering paths. All three still end with
Gemini synthesizing a conversational answer from backend-assembled context;
Gemini never queries the database or vector store directly, and never has
general-knowledge license to fill gaps.

## Structured path (exact facts)

```text
question
  → deterministic router (keyword/entity rules, no LLM)
  → PostgreSQL (plans, devices, promotions, changes)
  → grounded structured context
  → Gemini
  → answer
```

Used for exact prices, dates, and historical movements — e.g. "What is
T-Mobile Essentials currently priced at?" Exact numbers must always come from
this path, never from vector search, because embeddings retrieve semantically
similar text, not verified facts.

## RAG path (unstructured documents)

```text
question
  → deterministic router (adds a "documents" intent for eligibility/terms/
    conditions-style questions)
  → question embedding (gemini-embedding-001, task_type=RETRIEVAL_QUERY)
  → pgvector similarity search (cosine distance, document_chunks table)
  → top relevant chunks, filtered to a relevance threshold and to any
    competitor named in the question
  → grounded document-excerpt context
  → Gemini
  → answer + document sources
```

Used for promotion fine print, eligibility conditions, and plan descriptions
that live in synthetic demo documents rather than structured tables — e.g.
"What are the eligibility requirements for Verizon's device promotion?"

## Hybrid path (both)

The router is additive: a question can match both structured categories
(plans, devices, promotions, changes) and the documents category in the same
turn. When it does, both PostgreSQL records and retrieved document chunks are
assembled into one context and handed to Gemini together — e.g. "How much
does the Verizon plan cost and what conditions apply to its iPhone
promotion?" returns the structured plan price alongside the retrieved
trade-in eligibility chunk. RAG complements structured retrieval; it never
replaces it for a question a structured category already covers.

```text
question
  → router matches structured AND documents categories
  → PostgreSQL records + vector-retrieved chunks
  → combined grounded context
  → Gemini
  → answer
```

## Implementation

- **Documents**: three synthetic/demo documents in `database/documents/`
  (`*.md` with a small `key: value` front-matter block + body), clearly
  labeled as synthetic inside the text itself. Covers T-Mobile promotion
  terms, Verizon device-promotion terms, and Boost plan/promotion details.
- **Schema**: `database/schema/09_unstructured_documents.sql` adds the
  `vector` extension (pgvector, bundled with this Postgres.app install) plus
  `competitor_documents` (one row per document, with competitor/type/date
  metadata) and `document_chunks` (one row per chunk, with a `vector(768)`
  embedding and a foreign key back to its document).
- **Chunking**: `app/services/document_ingestion.chunk_text` greedily groups
  paragraphs up to ~500 characters, splitting an oversized paragraph on
  sentence boundaries. No overlap — the synthetic documents are short enough
  that overlap would mostly duplicate near-identical chunks in the index.
- **Embeddings**: `gemini-embedding-001` via the existing `google-genai` SDK
  (same API key/stack as chat generation), truncated to 768 dimensions via
  `output_dimensionality` — small enough to stay well under pgvector's
  indexable dimension limit, with no accuracy loss observed in evaluation.
  Ingestion uses `task_type=RETRIEVAL_DOCUMENT`; queries use
  `RETRIEVAL_QUERY`, matching the model's asymmetric retrieval design.
- **Vector storage/search**: PostgreSQL + pgvector, queried with the `<=>`
  cosine-distance operator. No ANN index (ivfflat/hnsw) — the corpus is a
  handful of documents and ~17 chunks, so an exact sequential scan is simpler
  and fast enough; add an index only if the corpus grows materially.
- **Routing**: `app/services/chat_context.route_question` adds a
  `"documents"` category when the question contains eligibility/terms/
  condition/requirement-style language, on top of its existing structured
  categories. This is still a deterministic keyword router, not an LLM
  classifier or autonomous agent.
- **Relevance guard**: chunks with cosine distance above `0.45` are dropped
  before reaching Gemini (`app/services/retrieval_service.MAX_RELEVANT_
  DISTANCE`), chosen empirically against this corpus (true matches cluster
  around 0.23–0.29; off-document matches run 0.33+). This is a deterministic
  first-line filter, not a semantic judge — see Limitations below.
- **Grounding**: the chat system instruction (`app/services/gemini_provider.
  CHAT_SYSTEM_INSTRUCTION`) requires Gemini to answer only from supplied
  structured records and document excerpts, to label document-derived claims
  as coming from a synthetic/demo document, and to say the tracked data is
  insufficient rather than filling a gap with outside knowledge.
- **Evaluation**: `app/services/rag_evaluation.py` — deterministic retrieval
  hit-rate/recall against known question→document pairs, a citation-validity
  check for generated answers (any cited source_id must exist in the supplied
  context), and a check that "no relevant chunk found" answers actually say
  so instead of guessing. No LLM-as-judge; `backend/scripts/run_rag_
  evaluation.py` runs it with real embeddings against the real corpus as a
  manual validation step.

## Limitations

- The 0.45 cosine-distance cutoff is a document-level relevance filter, not a
  sub-topic filter: a question about something a document doesn't cover (but
  which is topically adjacent to a document that does exist) can still clear
  the threshold. The system instruction's "say insufficient data" requirement
  is the actual backstop for that case, not the distance threshold alone —
  this is a deliberate reliance on the LLM for the judgment call that
  nearest-neighbor distance cannot make, consistent with using Gemini for
  interpretation and PostgreSQL/pgvector for retrieval, not the reverse.
- The corpus is intentionally tiny (3 documents, 17 chunks) and manually
  authored synthetic content, not scraped or vendor-sourced.
- No automated agentic tool selection yet: the router decides which
  categories (structured and/or RAG) apply; Gemini does not choose tools or
  call retrieval itself.
