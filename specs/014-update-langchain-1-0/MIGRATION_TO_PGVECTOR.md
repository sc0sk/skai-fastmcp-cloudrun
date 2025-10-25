# Migration Plan: Use LangChain 1.x Native PGVector (drop Google wrapper)

Last Updated: 2025-10-25
Status: Draft

This document outlines the steps to replace `langchain-google-cloud-sql-pg` with LangChain 1.x native PGVector, while preserving API behavior and database compatibility.

## Summary of differences

- Google wrapper (`langchain-google-cloud-sql-pg`):
  - Adds Cloud SQL connection helpers (PostgresEngine), IAM DB auth, sync/async APIs
  - Allows custom table name/columns (e.g., id_column, content_column)
  - Extra helpers (indexing, hybrid search)
- LangChain native PGVector (`langchain-community.vectorstores.PGVector`):
  - Standardized schema and operations; uses LangChain’s collection-based tables
  - Generally sync API; may need to run in thread from async contexts
  - No Cloud SQL specifics; we supply a SQLAlchemy engine/connection string

## Two viable approaches

A) Adopt PGVector standard schema (recommended)
- Tables: `langchain_pg_collection`, `langchain_pg_embedding`, `langchain_pg_embedding_collection`
- Use `collection_name` to scope data (e.g., `hansard`)
- Requires one-time data migration from current table if it differs

B) Compatibility adapter on existing table
- Keep current table (e.g., `speech_chunks`/`hansard_speeches`) and columns
- Implement minimal SQL-based vector ops using pgvector (insert/query/delete)
- Wrap in a class that matches our `VectorStoreService` public methods

## Proposed implementation (A, with feature flag)

1) Dependencies (pyproject.toml)
- Add:
  - `langchain>=1.0.0`
  - `langchain-community>=0.2.0` (vectorstores)
  - `sqlalchemy>=2.0.0`
  - `pg8000>=1.30` (or `asyncpg` if we choose async engine)
  - `pgvector>=0.2.5` (Python client for vector type)
  - `google-cloud-sql-connector>=1.9.0`
  - keep: `langchain-google-vertexai>=2.0.0`
- Remove later (once migrated): `langchain-google-cloud-sql-pg`

2) Cloud SQL connectivity
- Build a SQLAlchemy engine via Cloud SQL Python Connector:
  - IAM auth (recommended) or user/password
  - Driver: `pg8000`
  - Example (conceptual): create_engine("postgresql+pg8000://", creator=connector.connect(...))
- Provide `connection_string` or `engine` to PGVector

3) Vector backend flag
- Env: `VECTOR_BACKEND=community|google` (default google)
- In `VectorStoreService`, branch in `_get_vector_store()`:
  - google → current PostgresVectorStore path
  - community → build engine + instantiate PGVector

4) PGVector usage (community backend)
- Embeddings: `VertexAIEmbeddings(model_name="text-embedding-005", project=..., location=...)`
- Initialize store:
  - `PGVector.from_documents` (bootstrap) or instantiate and then `.add_texts`
  - Use `collection_name="hansard"` (or ENV)
  - Prefer JSONB metadata
- Methods mapping:
  - add_chunks → `add_texts(texts, metadatas, ids=optional)`; return ids
  - similarity_search → `similarity_search_with_score(query, k, filter=metadata_dict)`
  - delete_by_speech_id → `delete(filter={"speech_id": id})`

5) Async interop
- Community PGVector is sync-centric; our service is async
- Strategy: run blocking calls via `asyncio.to_thread(...)` wrappers for add/search/delete
- Keep `VectorStoreService` async API unchanged

6) Table/schema
- For new deployments: use standard PGVector tables (no custom table names)
- For existing data: either
  - Migrate to PGVector standard tables (recommended), or
  - Read-only fallback to google backend until migration finished

## Data migration (if choosing A)

- Create PGVector tables by initializing a dummy store
- One-off ETL script:
  - SELECT chunk_id, chunk_text as page_content, embedding, metadata FROM current_table
  - Insert into PGVector via `add_texts` with ids=chunk_id to preserve continuity
- Validate counts and spot-check search parity

## Risks and mitigations

- Loss of Google wrapper features (indices, hybrid search):
  - Mitigate: use PostgreSQL/pgvector indexes manually; hybrid can be added separately (tsvector + weighted combine)
- Async → sync bridging overhead:
  - Mitigate: batch operations; thread pool tuning
- Schema differences:
  - Mitigate: run migration with reversible steps; keep fallback backend

## Test plan

- Unit: stub embeddings, test add/search/delete with filters
- Integration: small doc set in dev DB; verify top-k and metadata filtering
- E2E: run existing ingest and search tools; compare outputs to baseline

## Rollout

- Phase 0: Feature flag and scaffolding merged (no behavior change)
- Phase 1: Deploy community backend to staging; verify parity
- Phase 2: Migrate data (if chosen), flip default backend to community
- Phase 3: Remove google wrapper dependency when stable

## Backout plan
- Flip `VECTOR_BACKEND=google` to revert instantly

## References
- LangChain PGVector docs (LangChain 1.x)
- Cloud SQL Python Connector + SQLAlchemy examples
- Current Google wrapper tests (for parity behaviors)
