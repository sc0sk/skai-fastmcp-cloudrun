#!/bin/bash
# Grant permissions to Cloud Run compute service account via Cloud SQL proxy

echo "Starting Cloud SQL proxy in background..."
./cloud_sql_proxy skai-fastmcp-cloudrun:us-central1:hansard-db-v2 &
PROXY_PID=$!

sleep 3

echo "Granting permissions to 666924716777-compute@developer..."

psql "host=localhost port=5432 dbname=hansard user=scott.coleman@aph.gov.au sslmode=disable" << 'EOF'
GRANT CONNECT ON DATABASE hansard TO "666924716777-compute@developer";
GRANT USAGE ON SCHEMA public TO "666924716777-compute@developer";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "666924716777-compute@developer";
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "666924716777-compute@developer";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "666924716777-compute@developer";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO "666924716777-compute@developer";
\q
EOF

echo "Stopping Cloud SQL proxy..."
kill $PROXY_PID

echo "✅ Permissions granted!"
