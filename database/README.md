# Competitive Intelligence Database Foundation

This folder contains the structured data foundation for the competitive intelligence prototype.

## Purpose

The goal of this database is to store telecom competitor information in a way that preserves history and supports later analysis, comparison, and alerts.

Important design rules:

- Historical observations are append-only and never overwritten.
- `captured_at` means when our system observed the data.
- `effective_date` means when the competitor offer actually became effective, if known.
- `effective_date` is nullable because we may not always know the real effective date.
- Current price is derived from the newest applicable historical record, not from an `is_active` flag.

## Directory structure

- `schema/` - PostgreSQL table definitions
- `seed/` - synthetic/mock records for Boost, T-Mobile, and Verizon
- `queries/` - example SQL for current state and historical comparison

## Core model

- `competitors`: the companies we monitor
- `service_plans`: the plans offered by each competitor
- `plan_price_history`: historical snapshots of plan pricing over time
- `devices`: devices sold by competitors
- `device_price_history`: historical snapshots of device pricing
- `promotions`: time-bounded promotional offers
- `competitor_changes`: a change log produced by deterministic comparison logic

## Change provenance migration

For an existing database, apply `schema/08_change_record_origin.sql` after the
original schema and seed scripts. It adds `competitor_changes.record_origin`;
existing rows default to `synthetic_seeded`, while the deterministic observation
workflow writes `system_detected`. New development databases can use the updated
`schema/07_competitor_changes.sql` directly.

## Important idea: versioned history

Instead of overwriting data, the system stores a new row each time a plan or device price changes. This lets users ask:

- What is the current price?
- What was the price 30 days ago?
- What changed between yesterday and today?
- What device promotion existed last month?

The prototype UI/backend may submit explicit development observations, append
history rows, compare the previous observation deterministically, and record a
mock alert. This is not automated ingestion or scraping. Unstructured-document
RAG is documented as a future architecture only; this repo does not add document
chunking, embeddings, or vector storage.
