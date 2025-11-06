-- ==============================================================================
-- CREATE IAM DATABASE USER FOR CLOUD RUN COMPUTE SERVICE ACCOUNT
-- ==============================================================================
-- Execute these commands while connected as 'postgres' superuser
--
-- INSTRUCTIONS:
-- 1. Connect to Cloud SQL:
--    gcloud sql connect hansard-db-v2 --user=postgres --database=hansard
--
-- 2. Get postgres password:
--    gcloud secrets versions access latest --secret=CLOUDSQL_PASSWORD
--
-- 3. Copy/paste this entire file into the psql prompt
-- ==============================================================================

-- Step 1: Create the IAM user (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '666924716777-compute@developer') THEN
        CREATE USER "666924716777-compute@developer" WITH LOGIN;
        RAISE NOTICE 'Created IAM user: 666924716777-compute@developer';
    ELSE
        RAISE NOTICE 'IAM user already exists: 666924716777-compute@developer';
    END IF;
END$$;

-- Step 2: Grant database-level permissions
GRANT CONNECT ON DATABASE hansard TO "666924716777-compute@developer";

-- Step 3: Grant schema-level permissions
GRANT USAGE ON SCHEMA public TO "666924716777-compute@developer";

-- Step 4: Grant permissions on all existing tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public
TO "666924716777-compute@developer";

-- Step 5: Grant permissions on all existing sequences
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public
TO "666924716777-compute@developer";

-- Step 6: Set default privileges for future tables (created by any user)
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES
TO "666924716777-compute@developer";

-- Step 7: Set default privileges for future sequences
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES
TO "666924716777-compute@developer";

-- ==============================================================================
-- VERIFICATION QUERIES
-- ==============================================================================

-- Verify user exists
\echo ''
\echo '=== Verifying IAM user exists ==='
SELECT rolname, rolsuper, rolinherit, rolcreaterole, rolcreatedb
FROM pg_roles
WHERE rolname = '666924716777-compute@developer';

-- Show table permissions for this user
\echo ''
\echo '=== Table permissions granted ==='
SELECT
    table_schema,
    table_name,
    privilege_type
FROM information_schema.table_privileges
WHERE grantee = '666924716777-compute@developer'
ORDER BY table_schema, table_name, privilege_type;

\echo ''
\echo '=== DONE! IAM user setup complete ==='
