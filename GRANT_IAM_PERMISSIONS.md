# Granting IAM Database Permissions to Cloud Run Service Account

## Overview
The Cloud Run service needs database-level permissions to access Cloud SQL PostgreSQL using IAM authentication.

## Current Status
- ✅ IAM database user created: `666924716777-compute@developer`
- ✅ Cloud Run service account: `666924716777-compute@developer.gserviceaccount.com`
- ✅ Cloud Run has `roles/cloudsql.client` IAM role
- ❌ **Pending:** Database-level GRANT permissions

## Instructions for Cloud Shell

### Step 1: Open Cloud Shell
Go to: https://console.cloud.google.com/?cloudshell=true

### Step 2: Set Project
```bash
gcloud config set project skai-fastmcp-cloudrun
```

### Step 3: Download and Start Cloud SQL Proxy
```bash
# Download proxy
curl -o cloud_sql_proxy https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64
chmod +x cloud_sql_proxy

# Start proxy (handles SSL automatically)
./cloud_sql_proxy -instances=skai-fastmcp-cloudrun:us-central1:hansard-db=tcp:5432 &

# Wait for proxy to connect
sleep 10
```

### Step 4: Connect to Database
```bash
# Password: k6K5Za0cfzfjV7q5iRcOLm43
PGPASSWORD='k6K5Za0cfzfjV7q5iRcOLm43' psql -h 127.0.0.1 -p 5432 -U postgres -d hansard
```

### Step 5: Grant IAM Permissions
Once connected to psql, run these SQL commands:

```sql
-- Grant connection permission
GRANT CONNECT ON DATABASE hansard TO "666924716777-compute@developer";

-- Grant schema usage
GRANT USAGE ON SCHEMA public TO "666924716777-compute@developer";

-- Grant table permissions (SELECT, INSERT, UPDATE, DELETE)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "666924716777-compute@developer";

-- Grant sequence permissions (for auto-increment columns)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "666924716777-compute@developer";

-- Grant default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "666924716777-compute@developer";

-- Grant default privileges for future sequences
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO "666924716777-compute@developer";

-- Exit psql
\q
```

### Step 6: Verify and Test
After granting permissions, the MCP search and fetch tools should work with IAM authentication.

Test via MCP Inspector or check Cloud Run logs for successful database connections.

## Current Cloud Run Configuration
- **Service:** hansard-mcp-server
- **Region:** us-central1
- **Current Revision:** hansard-mcp-server-00023-lfm
- **Authentication:** IAM (no user/password environment variables)

## Troubleshooting

### If psql connection fails with SSL errors:
The Cloud SQL Proxy method above handles SSL automatically. If you see SSL errors, ensure:
1. Cloud SQL Proxy is running (check with `ps aux | grep cloud_sql_proxy`)
2. You're connecting to `127.0.0.1:5432` (not the Cloud SQL public IP)

### If GRANT commands fail:
Ensure you're connected as `postgres` user (which has superuser privileges).

### After granting permissions:
The MCP server will automatically use IAM authentication. No code changes or redeployment needed.

## References
- Official LangChain docs: https://python.langchain.com/docs/integrations/vectorstores/google_cloud_sql_pg/
- Cloud SQL IAM authentication: https://cloud.google.com/sql/docs/postgres/authentication
