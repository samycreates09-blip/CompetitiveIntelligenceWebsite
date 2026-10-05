# 08 — PM Concepts: Prioritization & Trade-offs

This document re-reads the codebase through a product-management lens: how was the
10-phase roadmap in `docs/product_requirements.md` actually sequenced, what got
cut/deferred and why, and what's the trade-off log a PM should be able to recite.

## The roadmap, scored retroactively with MoSCoW

`docs/product_requirements.md` lays out 10 phases. Mapping them onto MoSCoW makes the
sequencing logic explicit — and matches what was actually built, in order:

| Phase | What | MoSCoW | Shipped? |
|---|---|---|---|
| 1 | Structured data foundation (schema, seed data) | **Must** | ✅ |
| 2 | Deterministic backend API | **Must** | ✅ |
| 3 | Web dashboard (read-only) | **Must** | ✅ |
| 4 | First LLM capability (AI briefing) + eval | **Should** | ✅ |
| 5 | RAG + retrieval eval | **Should** | ✅ |
| 6 | Deterministic AI tools + tool-selection eval | **Should** | ✅ (folded into phase 7's agentic work) |
| 7 | Agentic workflow + agent eval | **Could** | ✅ |
| 8 | Chatbot UI | **Should** | ✅ (delivered as part of phases 6/7 — "Ask AI") |
| 9 | Automated change detection + alerting | **Must** (for the product's core value) | ✅ (shipped alongside phase 6, ahead of its numbered position) |
| 10 | E2E eval, monitoring, security, production hardening | **Must before real users**, but correctly **last** for a prototype | ❌ — see [doc 10](10-architecture-proposal-production-readiness.md) |

Two things stand out. First, **change detection (phase 9) shipped earlier than its number
implies**, bundled with deterministic chat (phase 6) — a sign the team re-sequenced
against the roadmap when it made sense rather than treating phase numbers as a rigid
gate; that's healthy. Second, **production hardening (phase 10) is explicitly last and
still not started**, which is the correct call for a prototype proving product-market fit
on functionality, not infrastructure — but it means this system is not a hidden "secretly
production-ready" build, and a PM should be precise about that distinction when
presenting it upward.

## Why data-model-first, not AI-first

The build order was: **data foundation → deterministic API → dashboard → AI.** An
AI-native team under time pressure might be tempted to jump straight to "build the chatbot
demo" because that's the exciting, fundable part. This codebase did the opposite, and the
reasoning is visible in the product requirements doc itself: *"The LLM must not be treated
as the source of truth for exact competitive facts."* You cannot build a trustworthy
agent on top of data you don't yet have a trustworthy model for. This is the single
strongest prioritization lesson in the whole repo: **de-risk the deterministic foundation
before spending AI-development effort on top of it**, because every AI capability (the
briefing, the RAG tool, the agent's six tools) is, structurally, a thin wrapper around
services that were already correct and already tested before any LLM touched them.

## Build vs. buy, named explicitly

| Decision | Build | Buy / adopt | What was chosen | Why |
|---|---|---|---|---|
| Vector storage | Run ANN indexing ourselves | Pinecone/Weaviate (managed vector DB) | **Neither — reuse Postgres via pgvector** | Avoids a second system entirely; see [doc 02](02-database-layer.md) |
| Natural-language reasoning | Train/fine-tune a model | Rent a frontier model via API (Gemini) | **Buy (rent)** | Training a model is wildly out of scope for a competitive-intel feature; renting reasoning is the correct buy call almost always for this kind of product |
| Embeddings | Self-host sentence-transformers | Rent via the same Gemini API | **Buy** | One vendor relationship instead of two; see [doc 04](04-rag-pipeline.md) |
| Groundedness/hallucination checking | Use a second LLM as judge (buy more inference) | Write deterministic regex/heuristic checks (build) | **Build** | Cheaper, deterministic, testable without live API calls — see [doc 07](07-testing-evaluation-strategy.md) |
| API contract sync (frontend/backend types) | Hand-maintain types (build, manually) | Generate from OpenAPI (buy tooling, `openapi-typescript`) | **Build (manually) — a known gap** | Acceptable short-term for one developer; flagged as technical debt below |

## Trade-off log

A PM-facing decision log — each row is a concrete choice, the alternative given up, and
why it was reversible or not. Full ADR write-ups for the first three are in
[doc 09](09-architecture-decision-records.md).

| Decision | Alternative rejected | Reason | Reversibility |
|---|---|---|---|
| Postgres + pgvector, no dedicated vector DB | Pinecone/Weaviate/Qdrant | Avoid a second system at 17-chunk scale | Easy to add later; data model doesn't need to change, only the query path |
| Gemini for both chat and embeddings | OpenAI, Anthropic, or a mix | Single-vendor integration simplicity | Easy — isolated to `gemini_provider.py`/`embedding_provider.py` and one config field |
| Bounded agent loop (max 4 steps) | Unbounded ReAct-style loop | Guarantee bounded latency/cost per request, never hang | Easy — one constant, already covered by tests |
| SQLAlchemy Core, not ORM | Django/SQLAlchemy ORM | pgvector raw SQL needed anyway; one query style | Hard — would mean rewriting every service function |
| Deterministic router kept alongside the agent | Delete the old chat path | Regression baseline during migration | Easy — it's explicitly marked "kept for comparison," safe to delete once agent path is trusted |
| No CI/CD, no containers, no auth yet | Build infra alongside each feature | Prototype's goal was proving functionality, not productionizing | Represents accumulated, *known* technical debt — see below |

## Technical debt, knowingly accepted

A PM should be able to distinguish "debt we don't know about" from "debt we chose and can
name." This codebase is mostly the second kind:

- **No CI/CD or deployment target.** Chosen because the prototype's goal (phases 1–9) was
  proving the product idea and the AI architecture pattern, not operating a service.
  Explicitly deferred to phase 10.
- **No authentication.** Fine for a local single-user prototype; not fine the moment this
  is shared with even a second analyst.
- **Hand-maintained frontend/backend type sync.** Cheap today (one developer), will
  become a real cost the moment a second person starts shipping backend changes.
- **Documentation lag** (`docs/future_unstructured_data.md` describes a pre-agentic
  architecture that the code has since moved past — see [doc 05](05-llm-agentic-workflow.md)).
  A small, concrete example of docs rotting faster than code, worth surfacing in an
  interview as something you'd put a lightweight process control around (e.g. "update the
  architecture doc" as a definition-of-done item on any PR that changes it), not a bigger
  test suite.

All of the above are addressed, with cost and rollout framing, in
[doc 10](10-architecture-proposal-production-readiness.md).
