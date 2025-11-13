-- ==============================================================================
-- CREATE IAM DATABASE USER FOR CLOUD RUN COMPUTE SERVICE ACCOUNT
-- ==============================================================================
-- FIXED VERSION: Works even if postgres doesn't own the tables
--
-- Execute these commands while connected as 'postgres' superuser
--
-- INSTRUCTIONS:
-- 1. Connect to Cloud SQL:
--    gcloud sql connect hansard-db-v2 --user=postgres --database=hansard
--    Password: efzDDQ1Mxb8VOOAUzJsEVsKdJxtBXTdF
--
-- 2. Copy/paste this entire file into the psql prompt
-- ==============================================================================

-- Step 0: Check current table ownership
\echo '=== Current table ownership ==='
SELECT tablename, tableowner FROM pg_tables WHERE schemaname = 'public';

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

-- Step 4: Grant permissions on existing tables
-- This needs to be done by the table owner OR a superuser
-- Since we're connected as postgres (superuser), we can force this

-- Option A: Grant permissions on specific tables we know exist
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public'
    LOOP
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE %I TO "666924716777-compute@developer"', r.tablename);
        RAISE NOTICE 'Granted permissions on table: %', r.tablename;
    END LOOP;
END$$;

-- Step 5: Grant permissions on sequences
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public'
    LOOP
        EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE %I TO "666924716777-compute@developer"', r.sequence_name);
        RAISE NOTICE 'Granted permissions on sequence: %', r.sequence_name;
    END LOOP;
END$$;

-- Step 6: Set default privileges for FUTURE tables
-- This ensures tables created by ANY user will grant permissions to our IAM user
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES
TO "666924716777-compute@developer";

-- Step 7: Set default privileges for FUTURE sequences
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES
TO "666924716777-compute@developer";

-- Alternative: If you want postgres to own all tables (safer for future grants)
-- Uncomment these lines to transfer ownership:
-- DO $$
-- DECLARE
--     r RECORD;
-- BEGIN
--     FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public'
--     LOOP
--         EXECUTE format('ALTER TABLE %I OWNER TO postgres', r.tablename);
--         RAISE NOTICE 'Changed ownership of table % to postgres', r.tablename;
--     END LOOP;
-- END$$;

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

-- Show table ownership (for troubleshooting)
\echo ''
\echo '=== Table ownership (for reference) ==='
SELECT tablename, tableowner FROM pg_tables WHERE schemaname = 'public';

\echo ''
\echo '=== DONE! IAM user setup complete ==='
