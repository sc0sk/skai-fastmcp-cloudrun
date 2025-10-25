# Database Setup Guide

## Overview

This guide covers database setup for both **production (Cloud Run)** and **local development** environments.

This project uses two specialized service accounts for database access:

1. **hansard-db-admin@skai-fastmcp-cloudrun.iam** - Full ownership for schema management
2. **hansard-db-readonly@skai-fastmcp-cloudrun.iam** - Read-only access for MCP server queries

## Local Testing with Cloud SQL Proxy

### Prerequisites

- Cloud SQL Auth Proxy binary installed ([download here](https://cloud.google.com/sql/docs/postgres/sql-proxy))
- Database password for `postgres` user
- GCP credentials configured: `gcloud auth application-default login`

### Installation

#### macOS (Homebrew)
```bash
brew install cloud-sql-proxy
```

#### macOS/Linux (Manual)
```bash
# Download v2 (recommended)
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.14.2/cloud-sql-proxy.darwin.amd64
chmod +x cloud-sql-proxy
mv cloud-sql-proxy /usr/local/bin/

# Or download v1 (current project setup)
curl -o cloud_sql_proxy https://dl.google.com/cloudsql/cloud_sql_proxy.darwin.amd64
chmod +x cloud_sql_proxy
```

#### Windows
```powershell
# Download from: https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.14.2/cloud-sql-proxy.x64.exe
# Rename to cloud-sql-proxy.exe and add to PATH
```

### Quick Start Scripts

#### Start Proxy
```bash
./scripts/start_cloud_sql_proxy.sh

# With custom port
./scripts/start_cloud_sql_proxy.sh --port 5433

# With custom instance
./scripts/start_cloud_sql_proxy.sh --instance project:region:instance
```

The start script automatically:
- Detects v1 (`cloud_sql_proxy`) or v2 (`cloud-sql-proxy`) binary
- Checks for port conflicts and falls back to 5433, 5434, 5435
- Saves PID to `.cloud_sql_proxy.pid`
- Updates `.env` with `CLOUDSQL_PORT` if using non-default port

#### Stop Proxy
```bash
./scripts/stop_cloud_sql_proxy.sh
```

### Configuration

#### Environment Variables (`.env`)

**For local development with proxy (password authentication):**
```bash
CLOUDSQL_USER=postgres
DATABASE_PASSWORD=your_database_password_here
CLOUDSQL_INSTANCE=hansard-db-v2
CLOUDSQL_DATABASE=hansard
GCP_PROJECT_ID=skai-fastmcp-cloudrun
GCP_REGION=us-central1
```

**For production Cloud Run (IAM authentication):**
```bash
# Omit CLOUDSQL_USER and DATABASE_PASSWORD
CLOUDSQL_INSTANCE=hansard-db-v2
CLOUDSQL_DATABASE=hansard
GCP_PROJECT_ID=skai-fastmcp-cloudrun
GCP_REGION=us-central1
```

### Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `password authentication failed for user "postgresql"` | Wrong username | Use `CLOUDSQL_USER=postgres` (not `postgresql`) |
| `password authentication failed for user "postgres"` | Wrong password | Check `DATABASE_PASSWORD` in `.env` |
| `Connection refused` / `timeout` | Proxy not running | Run `./scripts/start_cloud_sql_proxy.sh` |
| `dial tcp 127.0.0.1:5432: connect: connection refused` | Proxy crashed or stopped | Check proxy logs; restart proxy |
| `bind: address already in use` | Port 5432 occupied | Script auto-selects 5433-5435; check console output |
| `User does not have permission` | IAM permissions missing | Run `gcloud auth application-default login` |

## Production Database Setup (Cloud Run)

### Current Status

✅ Service accounts created
✅ Cloud SQL Client IAM role granted
❌ **Database-level permissions NOT configured**
❌ **Table schema needs to be recreated**

## Required Manual Steps

### Step 1: Connect to Cloud SQL as postgres superuser

```bash
gcloud sql connect hansard-db-v2 --user=postgres --database=hansard --project=skai-fastmcp-cloudrun
```

### Step 2: Create database users for service accounts

```sql
-- Create admin user (if not exists)
CREATE USER "hansard-db-admin@skai-fastmcp-cloudrun.iam";

-- Create readonly user (if not exists)
CREATE USER "hansard-db-readonly@skai-fastmcp-cloudrun.iam";
```

### Step 3: Grant permissions

```sql
-- Grant admin full database permissions
GRANT ALL PRIVILEGES ON DATABASE hansard TO "hansard-db-admin@skai-fastmcp-cloudrun.iam";
GRANT ALL PRIVILEGES ON SCHEMA public TO "hansard-db-admin@skai-fastmcp-cloudrun.iam";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "hansard-db-admin@skai-fastmcp-cloudrun.iam";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "hansard-db-admin@skai-fastmcp-cloudrun.iam";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "hansard-db-admin@skai-fastmcp-cloudrun.iam";

-- Grant readonly SELECT only
GRANT CONNECT ON DATABASE hansard TO "hansard-db-readonly@skai-fastmcp-cloudrun.iam";
GRANT USAGE ON SCHEMA public TO "hansard-db-readonly@skai-fastmcp-cloudrun.iam";
GRANT SELECT ON ALL TABLES IN SCHEMA public TO "hansard-db-readonly@skai-fastmcp-cloudrun.iam";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO "hansard-db-readonly@skai-fastmcp-cloudrun.iam";
```

### Step 4: Drop existing table and transfer ownership

```sql
-- Drop the existing table with wrong schema
DROP TABLE IF EXISTS hansard_speeches CASCADE;

-- Exit psql
\q
```

### Step 5: Recreate table with correct LangChain schema

```bash
# Run as the admin service account
GCP_PROJECT_ID=skai-fastmcp-cloudrun \
GCP_REGION=us-central1 \
CLOUDSQL_INSTANCE=hansard-db-v2 \
CLOUDSQL_DATABASE=hansard \
CLOUDSQL_USER="hansard-db-admin@skai-fastmcp-cloudrun.iam" \
python3 scripts/init_langchain_schema.py
```

This will create the `hansard_speeches` table with:
- `langchain_id` (UUID, primary key) ← **THIS IS THE MISSING COLUMN**
- `content` (TEXT)
- `embedding` (VECTOR(768))
- `langchain_metadata` (JSONB)
- Plus 9 custom metadata columns (speaker, party, chamber, date, etc.)

### Step 6: Verify the schema

```bash
gcloud sql connect hansard-db-v2 --user=postgres --database=hansard --project=skai-fastmcp-cloudrun
```

```sql
\d hansard_speeches
```

You should see the `langchain_id` column in the output.

### Step 7: Test search functionality

```bash
GCP_PROJECT_ID=skai-fastmcp-cloudrun \
GCP_REGION=us-central1 \
CLOUDSQL_INSTANCE=hansard-db-v2 \
CLOUDSQL_DATABASE=hansard \
CLOUDSQL_USER="hansard-db-readonly@skai-fastmcp-cloudrun.iam" \
uv run python3 -c "
import asyncio
from tools.search import search_hansard_speeches

async def test():
    result = await search_hansard_speeches(query='climate', limit=5)
    print(f'Total results: {result.get(\"total_results\", 0)}')

asyncio.run(test())
"
```

## Why This Is Needed

The existing `hansard_speeches` table was created without the `langchain_id` column that LangChain's `PostgresVectorStore` requires. This causes all search queries to fail with:

```
ValueError: Id column, langchain_id, does not exist.
```

The table must be dropped and recreated with the correct schema. However, only the table owner (currently unknown) or postgres superuser can drop the table. Once dropped, the admin service account can recreate it with proper ownership.

## Service Account Usage

After setup:

- **hansard-db-admin**: Use for schema migrations, data ingestion, table management
- **hansard-db-readonly**: Use for MCP server runtime queries (production)

## Files Created

- [scripts/setup_db_service_accounts.py](scripts/setup_db_service_accounts.py) - Automated setup script (requires postgres access)
- [scripts/drop_and_recreate_table.py](scripts/drop_and_recreate_table.py) - Table recreation script
- [scripts/init_langchain_schema.py](scripts/init_langchain_schema.py) - LangChain-compatible schema initialization
