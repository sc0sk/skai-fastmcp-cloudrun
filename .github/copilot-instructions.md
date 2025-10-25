# skai-fastmcp-cloudrun Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-24

## Active Technologies
- Existing Cloud SQL PostgreSQL (via Feature 012 ingest_markdown_file tool) (013-bulk-markdown-ingestion)
- Python 3.11+ (Cloud Run requirement) (001-update-langchain-1-0)
- PostgreSQL via Cloud SQL with pgvector extension (001-update-langchain-1-0)
- PostgreSQL via Cloud SQL with pgvector extension (existing schema must remain compatible) (001-update-langchain-1-0)

- Python 3.11+ (Cloud Run compatibility requirement) + FastMCP 2.14.0+, pathlib (stdlib), glob patterns (013-bulk-markdown-ingestion)

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
- 001-update-langchain-1-0: Added Python 3.11+ (Cloud Run compatibility requirement)
- 001-update-langchain-1-0: Added Python 3.11+ (Cloud Run requirement)
- 013-bulk-markdown-ingestion: Added Python 3.11+ (Cloud Run compatibility requirement) + FastMCP 2.14.0+, pathlib (stdlib), glob patterns


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
