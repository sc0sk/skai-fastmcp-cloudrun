# Decision Record: Replace Google Cloud SQL PG wrapper with LangChain 1.x native PGVector

Date: 2025-10-25
Status: Proposed (awaiting confirmation)
Feature: 014-update-langchain-1-0

## Context

- Current project uses `langchain-google-cloud-sql-pg` (Google wrapper) for Postgres + pgvector vector store and Cloud SQL connection handling.
- Upgrade to LangChain 1.x is blocked by `langchain-google-cloud-sql-pg` requiring `langchain-core < 1.0.0`.
- Goal: Adopt LangChain 1.x "native" approach without the Google wrapper while keeping existing DB compatibility.

## Options

1. Switch to LangChain 1.x PGVector (native/community integration) and migrate to its standard schema
   - Use `langchain-community` PGVector vector store (or `langchain-postgres` if available)
   - Pros: Fully supported by LangChain 1.x, simple long-term, rich ecosystem
   - Cons: Requires adopting PGVector’s standard tables (`langchain_pg_embedding`, `langchain_pg_collection`, ...). Data migration needed if current table differs

2. Implement a compatibility adapter on top of existing table schema
   - Write our own minimal vector store wrapper that uses SQLAlchemy + pgvector ops directly on the existing table
   - Pros: No data migration, preserves current schema/permissions
   - Cons: We maintain more code; fewer built-in features (indexes/hybrid search helpers, test suite)

3. Wait for Google wrapper to support LangChain 1.x
   - Pros: Minimal change later
   - Cons: Timeline unknown; blocks upgrade now

## Proposed path

Proceed with Option 1, with a safe feature-flagged rollout:
- Introduce a backend flag (env: `VECTOR_BACKEND=community|google`)
- Implement PGVector backend while leaving Google backend intact for fallback
- Start with a pilot collection to validate parity; then plan data migration (if needed)

## Constraints / Non-negotiables
- Keep compatibility with existing Cloud SQL / pgvector environment
- Preserve result shapes and metadata filters used by tools
- Embedding model remains `text-embedding-005` (768 dims)

## Acceptance criteria
- Add/search/delete work identically (IDs, metadata, filters)
- Integration works in Cloud Run with Cloud SQL Connector (IAM or password)
- End-to-end tests green (ingest/search tools)

## Rollback
- Flip `VECTOR_BACKEND=google` env var to fall back instantly
