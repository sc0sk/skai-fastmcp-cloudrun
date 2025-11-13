# Research: LangChain 1.0 with langchain-postgres

This document captures external references and decisions that inform the implementation.

## Key Sources

- LangChain PGVector docs (integration): https://docs.langchain.com/oss/python/integrations/vectorstores/pgvector
  - Status: Uses dedicated `langchain-postgres` package
  - Driver: `psycopg3` (connection string `postgresql+psycopg://`)
  - Requires explicit connection object
  - Rich metadata filtering ($eq, $in, $and, $or, $ilike, etc.)
  - Explicit IDs supported (overwrites if exists)

- Google Cloud SQL Python Connector docs: https://cloud.google.com/sql/docs/postgres/connect-connectors
  - Supports automatic IAM database authentication (recommended)
  - Works with token refresh for long-lived processes

- Cloud SQL IAM authentication: https://cloud.google.com/sql/docs/postgres/iam-authentication
  - Automatic IAM auth via connector; manual auth not recommended

## Decisions

- Adopt `langchain-postgres` as the vector store implementation
- Use `psycopg[binary]` 3.x driver and `postgresql+psycopg://` URIs
- Build SQLAlchemy Engine via `google-cloud-sql-connector` (IAM-only)
- Keep embeddings provider as Vertex AI (text-embedding-005)
- Use JSONB metadata (use_jsonb=True) and `collection_name="hansard"`
- Implement async wrappers via `asyncio.to_thread` to keep async service API

## Alternatives Considered

- Keep `langchain-google-cloud-sql-pg` and pin to <1.0: Rejected due to blocking `langchain-core<1.0.0`
- Use `langchain-community` PGVector: Deprecated in docs in favor of `langchain-postgres`
- Native async with asyncpg: Deferred; psycopg3 + to_thread is sufficient and simpler

## Risks

- Schema changes in `langchain-postgres` require table recreation
- Migration needs care to preserve chunk IDs and metadata
- psycopg3 differences from psycopg2 may affect tooling/workflows

## Open Questions

- Which collection_name should we use across environments? Default `hansard` set
- What is the expected vector dimension (e.g., 768 for text-embedding-005)? Confirm at runtime
