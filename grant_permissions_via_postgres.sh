#!/bin/bash
# Grant permissions via Cloud SQL proxy using gcloud IAM authentication

echo "============================================================"
echo "GRANT PERMISSIONS ON LANGCHAIN TABLES"
echo "============================================================"
echo ""
echo "This will connect as scott.coleman@aph.gov.au (IAM user)"
echo "and grant permissions to the compute service account."
echo ""

# Create temporary SQL file
cat > /tmp/grant_perms.sql << 'EOSQL'
-- Grant all privileges on LangChain tables
GRANT ALL PRIVILEGES ON langchain_pg_collection TO "666924716777-compute@developer";
GRANT ALL PRIVILEGES ON langchain_pg_embedding TO "666924716777-compute@developer";

-- Verify
SELECT 'Permissions granted!' as status;

SELECT table_name, privilege_type
FROM information_schema.table_privileges
WHERE grantee = '666924716777-compute@developer'
  AND table_name IN ('langchain_pg_collection', 'langchain_pg_embedding')
ORDER BY table_name, privilege_type;
EOSQL

# Connect and run SQL
echo "Running SQL as scott.coleman@aph.gov.au..."
gcloud sql connect hansard-db-v2 \
  --user=scott.coleman@aph.gov.au \
  --database=hansard \
  --project=skai-fastmcp-cloudrun < /tmp/grant_perms.sql

echo ""
echo "============================================================"
echo "✅ DONE!"
echo "============================================================"
echo "Try ChatGPT search now"

rm /tmp/grant_perms.sql
