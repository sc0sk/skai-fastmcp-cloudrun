# skai-fastmcp-cloudrun Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-22

## Active Technologies
- Python 3.11+ (Cloud Run compatibility) + FastMCP 2.14.0+ (tool annotations, metadata, icons) (001-chatgpt-devmode-enhancements)
- Python 3.11+ + FastMCP 2.12.5+, LangChain (langchain-google-vertexai, langchain-google-cloud-sql-pg), Pydantic v2 (004-search-fetch-mcp-tools)
- Cloud SQL PostgreSQL with pgvector extension (LangChain schema: langchain_pg_embedding + speeches metadata table) (004-search-fetch-mcp-tools)
- Python 3.11+ + FastMCP 2.12.5+ (existing), no new dependencies required (005-chatgpt-integration)
- N/A (metadata optimization only, no database changes) (005-chatgpt-integration)

## Project Structure
```
src/
tests/
```

## Commands
cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style
Python 3.11+ (Cloud Run compatibility): Follow standard conventions

## Recent Changes
- 005-chatgpt-integration: Added Python 3.11+ + FastMCP 2.12.5+ (existing), no new dependencies required
- 004-search-fetch-mcp-tools: Added Python 3.11+ + FastMCP 2.12.5+, LangChain (langchain-google-vertexai, langchain-google-cloud-sql-pg), Pydantic v2
- 001-chatgpt-devmode-enhancements: Added Python 3.11+ (Cloud Run compatibility) + FastMCP 2.14.0+ (tool annotations, metadata, icons)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
