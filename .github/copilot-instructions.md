# skai-fastmcp-cloudrun Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-25

## Active Technologies
- Existing Cloud SQL PostgreSQL (via Feature 012 ingest_markdown_file tool) (013-bulk-markdown-ingestion)
- Python 3.11+ (Cloud Run compatibility requirement) + FastMCP 2.14.0+, pathlib (stdlib), glob patterns (013-bulk-markdown-ingestion)
- Cloud SQL Auth Proxy for local database testing (014-fix-local-database)

## Project Structure

```text
src/
  storage/
    vector_store.py    # Uses DATABASE_PASSWORD for local auth
    metadata_store.py  # Uses DATABASE_PASSWORD for local auth
tests/
scripts/
  start_cloud_sql_proxy.sh  # Start proxy for local testing
  stop_cloud_sql_proxy.sh   # Stop proxy cleanly
```

## Local Development Setup

### Database Authentication
- **Local testing**: Use Cloud SQL proxy with password authentication
  - Set `CLOUDSQL_USER=postgres` in `.env`
  - Set `DATABASE_PASSWORD=<your_password>` in `.env`
  - Start proxy: `./scripts/start_cloud_sql_proxy.sh`
- **Production (Cloud Run)**: Use IAM authentication
  - Omit `CLOUDSQL_USER` and `DATABASE_PASSWORD` from production env vars
  - Service account handles authentication automatically

### Cloud SQL Proxy Scripts
- `./scripts/start_cloud_sql_proxy.sh` - Start proxy (auto-detects v1/v2, handles port conflicts)
- `./scripts/stop_cloud_sql_proxy.sh` - Stop proxy cleanly
- PID file: `.cloud_sql_proxy.pid` (gitignored)
- Port override: `./scripts/start_cloud_sql_proxy.sh --port 5433`

### Common Issues
- "password authentication failed for user postgresql": Use `CLOUDSQL_USER=postgres` (not `postgresql`)
- "Connection refused": Start proxy with `./scripts/start_cloud_sql_proxy.sh`
- Port conflicts: Script auto-selects alternate ports (5433-5435)

See `DATABASE_SETUP.md` for detailed setup guide.

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11+ (Cloud Run compatibility requirement): Follow standard conventions

## Recent Changes
- 014-fix-local-database: Fixed database authentication for local testing (username postgres vs postgresql, proxy management scripts)
- 013-bulk-markdown-ingestion: Added Python 3.11+ (Cloud Run compatibility requirement) + FastMCP 2.14.0+, pathlib (stdlib), glob patterns

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
