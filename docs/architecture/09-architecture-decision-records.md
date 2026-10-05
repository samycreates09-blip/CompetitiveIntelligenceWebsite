# 09 — Architecture Decision Records

Standard ADR format: Context → Decision → Alternatives Considered → Consequences.
These are the six decisions that most shaped the system's shape and cost.

---

## ADR-01: Use PostgreSQL + pgvector instead of a dedicated vector database

**Status:** Accepted

**Context:** The product needs both exact structured facts (prices, dates) and
semantic search over unstructured competitor documents (promo fine print). The
unstructured corpus is currently 3 documents / 17 chunks, and is synthetic/demo data.

**Decision:** Store embeddings as a `vector(768)` column in Postgres via the `pgvector`
extension, queried with the `<=>` cosine-distance operator in raw SQL, with no ANN index
(sequential scan).

**Alternatives considered:**
- A dedicated vector database (Pinecone, Weaviate, Qdrant) — rejected: a second system to
  provision, pay for, and keep consistent with Postgres, for no measurable benefit at
  this corpus size.
- SQLite with a vector extension — rejected: no credible path to a shared/multi-user
  environment, and the team wanted real Postgres semantics from day one.

**Consequences:** One database to operate and one bill to pay. Query cost is a full
sequential scan per search, which is correct and fast at 17 rows and will degrade past
roughly 10K–100K vectors — at which point an `ivfflat`/`hnsw` index should be added (a
schema migration, not a re-architecture). Revisit trigger: document corpus size, not a
calendar date.

---

## ADR-02: Use Gemini (chat + embeddings) rather than a multi-vendor LLM stack

**Status:** Accepted

**Context:** The product needs a chat/function-calling model and an embedding model.
Both OpenAI and Anthropic offer comparable capability for this use case.

**Decision:** Use Google's `google-genai` SDK for both the agentic chat model
(`gemini-3.1-flash-lite`) and the embedding model (`gemini-embedding-001`), configured via
two env vars (`GEMINI_MODEL`, `GEMINI_EMBEDDING_MODEL`).

**Alternatives considered:**
- OpenAI (GPT-4o/4o-mini + text-embedding-3) — comparable function-calling maturity, but
  a second vendor relationship and billing line.
- Anthropic (Claude) for chat, paired with a separate embedding vendor — same
  multi-vendor overhead.

**Consequences:** One SDK, one API key, one safety-wrapper module (`provider_safety.py`)
to maintain. Vendor lock-in is real but shallow — the touchpoints are isolated to two
service modules (`gemini_provider.py`, `embedding_provider.py`) and two config fields, so
switching vendors is a contained change, not a rewrite. The trade was explicitly
"integration simplicity now" over "best possible model now," validated by the
tool-selection eval harness passing at the chosen model tier.

---

## ADR-03: SQLAlchemy Core (hand-declared tables), not the ORM

**Status:** Accepted

**Context:** The service layer needs to run both ordinary relational CRUD queries and
pgvector cosine-distance searches (`<=>` operator, `CAST(:embedding AS vector)`), plus a
`LATERAL` join for "current price" semantics.

**Decision:** Declare all tables by hand as SQLAlchemy Core `Table` objects in
`database.py`; write every query as explicit `select()`/`insert()` statements or raw SQL,
with no declarative ORM model classes.

**Alternatives considered:**
- SQLAlchemy ORM (declarative models, relationships) — rejected: pgvector's operator and
  the `LATERAL` join aren't natural ORM citizens, so raw SQL would be needed regardless;
  mixing ORM-for-CRUD with raw-SQL-for-vectors would create two query styles in one
  codebase.

**Consequences:** More verbose query code than ORM-style `Model.objects.filter(...)`
calls, but one consistent SQL-first style across the entire service layer, and complete
control over exactly what SQL runs — important when a `LATERAL` join or a vector operator
is load-bearing for correctness. Cost: the frontend's TypeScript types are hand-mirrored
rather than ORM-codegen-able, a known and accepted gap (see [doc 08](08-pm-concepts-prioritization-tradeoffs.md)).

---

## ADR-04: Bound the agentic tool-calling loop at a fixed step count

**Status:** Accepted

**Context:** Gemini's native function calling lets the model request tool calls in a
multi-turn loop. An unbounded loop risks the model requesting tools indefinitely,
producing unbounded latency and cost per user request.

**Decision:** Cap the loop at `MAX_TOOL_CALL_STEPS = 4` rounds (each round may contain
multiple parallel tool calls). If the model is still requesting tools after 4 rounds,
return an explicit bounded-fallback message rather than continuing or erroring.

**Alternatives considered:**
- Unbounded loop with a wall-clock timeout — rejected: a timeout is a blunt, non-graceful
  failure (the user gets nothing); a step-count bound can return a meaningful partial
  message instead.
- No tool-calling loop at all (single-shot function calling, no multi-round) — rejected:
  the actual product need (compare two competitors across plans, devices, and promos)
  genuinely requires multiple sequential tool calls.

**Consequences:** Guarantees a bounded number of model round-trips (and therefore bounded
latency and cost) per chat request, with a graceful, user-visible message on the rare
case the bound is hit. The number 4 was chosen from the hardest known real example in the
eval set, not derived analytically — documented explicitly as a judgment call to revisit
as real usage patterns emerge.

---

## ADR-05: Keep the deterministic chat router alongside the new agentic path

**Status:** Accepted (temporary — flagged for future removal)

**Context:** The first chat implementation (`chat_context.py`'s keyword router) was
superseded by the agentic tool-calling path (`agent_service.py`). The frontend now calls
only the new agentic endpoint.

**Decision:** Keep the old deterministic router and its endpoint (`/api/v1/ai/chat`)
live, "retained for comparison and test coverage," rather than deleting it.

**Alternatives considered:**
- Delete the old path immediately on shipping the new one — rejected for now, to preserve
  a regression baseline during the migration.

**Consequences:** Extra maintenance surface (two chat code paths, two test files) in
exchange for a safety net while trust in the new agentic path is still being established.
This ADR should be revisited with an explicit removal decision once the agentic path has
enough production usage to be trusted on its own — keeping superseded code indefinitely
is not the intent.

---

## ADR-06: Defer all production infrastructure (CI/CD, containers, auth, monitoring) to a later phase

**Status:** Accepted

**Context:** The product requirements doc defines a 10-phase roadmap; phase 10 is
explicitly "end-to-end evaluation, monitoring, security, and production hardening."

**Decision:** Build phases 1–9 (data model through agentic chat) with zero deployment
tooling — no Dockerfile, no CI pipeline, no auth, no observability stack — and treat
phase 10 as a distinct, later proposal.

**Alternatives considered:**
- Build infrastructure incrementally alongside each feature phase — rejected: would have
  slowed down validating the core product hypothesis (is grounded, tool-using AI useful
  for competitive intelligence?) without changing whether that hypothesis holds.

**Consequences:** The system today is a fully local, single-user prototype with no
security boundary and no path to a shared environment. This is a named, intentional gap,
not an oversight — detailed with cost and rollout plan in
[doc 10](10-architecture-proposal-production-readiness.md).
