-- ==============================================================================
-- CREATE IAM DATABASE USER - FINAL VERSION
-- ==============================================================================
-- This version:
-- 1. Transfers ownership of all tables to postgres
-- 2. Then grants permissions to IAM user
-- This ensures postgres has permission to grant to others
-- ==============================================================================

\echo ''
\echo '=========================================='
\echo 'IAM USER CREATION - FINAL VERSION'
\echo '=========================================='
\echo ''

-- Step 1: Show current ownership
\echo 'Step 1: Current table ownership...'
SELECT tablename, tableowner FROM pg_tables WHERE schemaname = 'public';
\echo ''

-- Step 2: Transfer ownership to postgres (so postgres can grant permissions)
\echo 'Step 2: Transferring table ownership to postgres...'
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public'
    LOOP
        EXECUTE format('ALTER TABLE %I OWNER TO postgres', r.tablename);
        RAISE NOTICE '  ✅ Changed ownership: % → postgres', r.tablename;
    END LOOP;
END$$;
\echo ''

-- Step 3: Transfer sequence ownership to postgres
\echo 'Step 3: Transferring sequence ownership to postgres...'
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public'
    LOOP
        EXECUTE format('ALTER SEQUENCE %I OWNER TO postgres', r.sequence_name);
        RAISE NOTICE '  ✅ Changed ownership: % → postgres', r.sequence_name;
    END LOOP;
END$$;
\echo ''

-- Step 4: Create the IAM user
\echo 'Step 4: Creating IAM user "666924716777-compute@developer"...'
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '666924716777-compute@developer') THEN
        CREATE USER "666924716777-compute@developer" WITH LOGIN;
        RAISE NOTICE '✅ Created IAM user';
    ELSE
        RAISE NOTICE '✅ User already exists';
    END IF;
END$$;
\echo ''

-- Step 5: Grant database permissions
\echo 'Step 5: Granting database permissions...'
GRANT CONNECT ON DATABASE hansard TO "666924716777-compute@developer";
\echo '✅ Granted CONNECT'
\echo ''

-- Step 6: Grant schema permissions
\echo 'Step 6: Granting schema permissions...'
GRANT USAGE ON SCHEMA public TO "666924716777-compute@developer";
\echo '✅ Granted USAGE on schema public'
\echo ''

-- Step 7: Grant table permissions (now postgres owns them, so this will work)
\echo 'Step 7: Granting table permissions...'
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public
TO "666924716777-compute@developer";
\echo '✅ Granted SELECT, INSERT, UPDATE, DELETE on all tables'
\echo ''

-- Step 8: Grant sequence permissions
\echo 'Step 8: Granting sequence permissions...'
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public
TO "666924716777-compute@developer";
\echo '✅ Granted USAGE, SELECT on all sequences'
\echo ''

-- Step 9: Set default privileges for future tables
\echo 'Step 9: Setting default privileges...'
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES
TO "666924716777-compute@developer";
\echo '✅ Default privileges set for tables'

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES
TO "666924716777-compute@developer";
\echo '✅ Default privileges set for sequences'
\echo ''

-- Verification
\echo '=========================================='
\echo 'VERIFICATION'
\echo '=========================================='
\echo ''

\echo 'User exists:'
SELECT rolname FROM pg_roles WHERE rolname = '666924716777-compute@developer';
\echo ''

\echo 'Permissions granted:'
SELECT COUNT(*) as permission_count
FROM information_schema.table_privileges
WHERE grantee = '666924716777-compute@developer';
\echo ''

\echo 'Table ownership (should all be postgres now):'
SELECT tablename, tableowner FROM pg_tables WHERE schemaname = 'public';
\echo ''

\echo '=========================================='
\echo '✅ COMPLETE! IAM USER READY'
\echo '=========================================='
\echo 'ChatGPT searches should now work!'
\echo ''
