# skai-fastmcp-cloudrun Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-27

## Active Technologies
- Existing Cloud SQL PostgreSQL (via Feature 012 ingest_markdown_file tool) (013-bulk-markdown-ingestion)
- Python 3.11+ (Cloud Run requirement) (014-update-langchain-1-0)
- PostgreSQL via Cloud SQL with pgvector extension (014-update-langchain-1-0)
- PostgreSQL via Cloud SQL with pgvector extension (existing schema must remain compatible) (014-update-langchain-1-0)
- LangChain 1.0+ with langchain-google-vertexai>=2.0 (Vertex AI embeddings, chat models) (014-update-langchain-1-0)
- langchain-google-genai, langchain-google-community (Google integrations supporting LangChain 1.0) (014-update-langchain-1-0)
- LangChain 1.0+ vector store via langchain-postgres (PGVector) with psycopg3 driver (postgresql+psycopg://) (016-langchain-postgres-upgrade)
- SQLAlchemy 2.x engine using google-cloud-sql-connector (automatic IAM DB auth) (016-langchain-postgres-upgrade)
- Python 3.11+ (Cloud Run compatibility requirement) + FastMCP 2.14.0+, pathlib (stdlib), glob patterns (013-bulk-markdown-ingestion)
- AsyncIO-aware MCP testing framework + comprehensive docstring standards with "Returns" sections (018-mcp-tools-quality-improvements)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11+ (Cloud Run compatibility requirement): Follow standard conventions

## Recent Changes
- 014-update-langchain-1-0: Added LangChain 1.0+ with langchain-google-vertexai>=2.0, langchain-google-genai, langchain-google-community (all support LangChain 1.0)
- 014-update-langchain-1-0: Added Python 3.11+ (Cloud Run compatibility requirement)
- 014-update-langchain-1-0: Added Python 3.11+ (Cloud Run requirement)
- 013-bulk-markdown-ingestion: Added Python 3.11+ (Cloud Run compatibility requirement) + FastMCP 2.14.0+, pathlib (stdlib), glob patterns
 - 016-langchain-postgres-upgrade: Replace langchain-google-cloud-sql-pg with langchain-postgres (dedicated package); migrate to psycopg3 driver and SQLAlchemy 2 with Cloud SQL connector (IAM auth)
 - 016-langchain-postgres-upgrade: Adopt PGVector standard schema (langchain_pg_collection, langchain_pg_embedding); use collection_name and JSONB metadata
 - 018-mcp-tools-quality-improvements: Enhanced MCP tool docstrings with "Returns" sections; implemented async-aware testing framework to eliminate coroutine warnings; improved best practices compliance from 0.39/1.00 to target 0.80/1.00


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
