-- ==============================================================================
-- FIX LANGCHAIN TABLE PERMISSIONS
-- ==============================================================================
-- Quick fix to grant permissions on langchain_pg_* tables to IAM user
-- Run this in Cloud SQL Query Editor or psql
-- ==============================================================================

-- Transfer ownership of langchain tables to postgres first
ALTER TABLE langchain_pg_collection OWNER TO postgres;
ALTER TABLE langchain_pg_embedding OWNER TO postgres;

-- Grant permissions to IAM user
GRANT SELECT, INSERT, UPDATE, DELETE ON langchain_pg_collection TO "666924716777-compute@developer";
GRANT SELECT, INSERT, UPDATE, DELETE ON langchain_pg_embedding TO "666924716777-compute@developer";

-- Also grant on the hansard_speeches table if not already done
GRANT SELECT, INSERT, UPDATE, DELETE ON hansard_speeches TO "666924716777-compute@developer";

-- Grant sequence permissions (for auto-increment IDs)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "666924716777-compute@developer";

-- Set default privileges for any future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "666924716777-compute@developer";

-- Verify permissions
SELECT
    grantee,
    table_name,
    privilege_type
FROM information_schema.table_privileges
WHERE grantee = '666924716777-compute@developer'
ORDER BY table_name, privilege_type;
