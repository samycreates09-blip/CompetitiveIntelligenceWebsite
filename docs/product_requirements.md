# Boost Competitive Intelligence Platform

## Product goal

Build an internal AI-native competitive intelligence platform for a telecom company that tracks competitor plans, device pricing, promotions, historical changes, and provides AI-assisted competitive insights.

## Tracked competitors

- Boost Mobile
- T-Mobile
- Verizon

## Core product capabilities

1. Track current wireless plans and prices.
2. Track device pricing and promotions.
3. Preserve historical observations instead of overwriting them.
4. Detect changes between new and previous observations.
5. Generate AI summaries explaining important competitive changes.
6. Provide a chatbot for current and historical competitive questions.
7. Send alerts for important competitor changes.

## Data strategy

Use structured PostgreSQL data for exact facts such as:
- current prices
- historical prices
- dates
- devices
- plan attributes
- promotions where represented structurally

Use RAG for unstructured information such as:
- promotion terms
- competitor webpages/documents
- policy language
- text-heavy offer details

The LLM must not be treated as the source of truth for exact competitive facts.

## AI architecture

The eventual architecture should support:

Sources
→ ingestion
→ validation/normalization
→ PostgreSQL + unstructured documents
→ embeddings/vector retrieval
→ backend
→ AI agent
→ LLM + RAG + deterministic tools
→ response
→ dashboard/chatbot/alerts
→ evaluation and monitoring

## Agent responsibilities

The eventual AI agent should be able to:
- determine whether a question requires structured data, RAG, or both
- call deterministic tools for factual database questions
- retrieve relevant unstructured evidence when needed
- perform multi-step comparisons
- provide grounded responses

## Change detection

Change detection itself should be deterministic.

Example:

new observation
→ compare against previous observation
→ detect changed fields
→ calculate old/new values
→ record competitor change

GenAI may later explain the significance of that detected change.

Important:
The current competitor_changes records are synthetic seed data.
Automatic change detection has NOT been implemented yet.

## Evaluation strategy

Use traditional deterministic tests for:
- database behavior
- APIs
- business rules
- change detection

Introduce AI evals alongside each probabilistic AI capability:

LLM summaries
→ groundedness / hallucination / answer-quality eval

RAG
→ retrieval eval + grounded-answer eval

Tool calling
→ tool-selection and argument-accuracy eval

Agent workflows
→ trajectory/task-completion eval

Complete AI application
→ end-to-end eval suite

## Development phases

Phase 1 — Structured database foundation [COMPLETED]
- PostgreSQL schema
- historical data model
- synthetic seed data
- deterministic queries
- validation

Phase 2 — Backend API
Phase 3 — Web dashboard
Phase 4 — First LLM capability + eval
Phase 5 — RAG + retrieval eval
Phase 6 — deterministic AI tools + tool-selection eval
Phase 7 — agentic workflow + agent eval
Phase 8 — chatbot
Phase 9 — automated change detection and alerts
Phase 10 — end-to-end evaluation, monitoring, security, and production hardening

## Prototype principles

- Start with synthetic/mock data.
- Live/approved competitor ingestion comes later.
- Prefer deterministic software when exact correctness is required.
- Use GenAI where language understanding, retrieval, summarization, or reasoning adds value.
- Maintain historical auditability.
- Human approval is required between major development phases.
- AI coding agents may automate implementation and terminal work, but architecture, requirements, validation criteria, and phase approval remain human-controlled.
