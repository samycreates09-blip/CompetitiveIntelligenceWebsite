# Boost Competitive Intelligence — Architecture Documentation

This folder is a PM-oriented technical walkthrough of the Boost Competitive Intelligence
prototype: what was built, why each technology was chosen over its alternatives, what it
costs, and how a product manager should reason about the trade-offs. It was written for
interview prep (AI-Native Senior Builder / PM L6), so each document pairs **what the code
does** with **why a PM should care**.

The product itself: an internal, AI-native competitive intelligence platform that tracks
Boost Mobile's competitors (T-Mobile, Verizon) — plan prices, device prices, promotions —
detects changes over time, and lets a user ask natural-language questions answered by an
LLM agent that is grounded in a real database rather than its own memory.

## How to read this

Read in order if you're new to the repo; jump directly to a doc if you already know the
area and want the trade-off framing.

| # | Document | Covers |
|---|----------|--------|
| 01 | [System Overview](01-system-overview.md) | The whole system in one picture, end-to-end request flow, build sequence |
| 02 | [Database Layer](02-database-layer.md) | Postgres + pgvector schema, append-only history design, vector store trade-off |
| 03 | [Backend API](03-backend-api.md) | FastAPI, SQLAlchemy Core, layered service architecture, error contract |
| 04 | [RAG Pipeline](04-rag-pipeline.md) | Document ingestion, chunking, embeddings, deterministic relevance gate |
| 05 | [LLM Agentic Workflow](05-llm-agentic-workflow.md) | Gemini tool calling, the bounded agent loop, grounding/safety design |
| 06 | [Frontend](06-frontend.md) | React + Vite + React Query, no-router/no-Tailwind decisions, component tree |
| 07 | [Testing & Evaluation Strategy](07-testing-evaluation-strategy.md) | Test pyramid vs. AI eval pyramid, what the team treats as highest-risk |
| 08 | [PM Concepts: Prioritization & Trade-offs](08-pm-concepts-prioritization-tradeoffs.md) | Roadmap sequencing, RICE/MoSCoW framing, build-vs-buy, tech debt log |
| 09 | [Architecture Decision Records](09-architecture-decision-records.md) | 6 ADRs for the decisions that most shaped the system |
| 10 | [Architecture Proposal: Production Readiness](10-architecture-proposal-production-readiness.md) | A formal proposal doc for the next phase (what's missing, cost, risk, rollout) |

## One-paragraph architecture summary

A React/TypeScript single-page app calls a FastAPI backend over REST. The backend stores
all competitive facts (plans, devices, promotions, price history, detected changes) in
Postgres, using plain SQL tables (SQLAlchemy Core, no ORM) so that history is append-only
and auditable. Unstructured competitor documents (promo fine print) are chunked, embedded
with Gemini's embedding model, and stored as vectors in the same Postgres database via the
`pgvector` extension — no separate vector database. A Gemini model with native function
calling acts as an agent: it is given six read-only tools (wrapping the same services the
REST API uses) and a bounded loop (max 4 rounds) to call them, so it only ever answers from
real data it fetched, never from memory, and every claim is cited back to a source record.
There is currently no CI/CD, container, or deployment layer — this is a local-only
prototype, and that gap is the subject of the production-readiness proposal (doc 10).
