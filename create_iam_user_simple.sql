-- ==============================================================================
-- SIMPLE IAM USER CREATION - WITH LOTS OF FEEDBACK
-- ==============================================================================
-- This version shows you exactly what's happening at each step
-- ==============================================================================

\echo ''
\echo '=========================================='
\echo 'STARTING IAM USER CREATION'
\echo '=========================================='
\echo ''

-- Show current connection info
\echo 'Step 0: Checking connection...'
SELECT current_database() as database, current_user as connected_as;
\echo ''

-- Show existing tables
\echo 'Step 1: Listing existing tables...'
SELECT tablename, tableowner FROM pg_tables WHERE schemaname = 'public';
\echo ''

-- Create the IAM user
\echo 'Step 2: Creating IAM user "666924716777-compute@developer"...'
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '666924716777-compute@developer') THEN
        CREATE USER "666924716777-compute@developer" WITH LOGIN;
        RAISE NOTICE '✅ SUCCESS: Created IAM user';
    ELSE
        RAISE NOTICE '✅ User already exists (this is OK)';
    END IF;
END$$;
\echo ''

-- Grant database permissions
\echo 'Step 3: Granting database permissions...'
GRANT CONNECT ON DATABASE hansard TO "666924716777-compute@developer";
\echo '✅ Granted CONNECT'
\echo ''

-- Grant schema permissions
\echo 'Step 4: Granting schema permissions...'
GRANT USAGE ON SCHEMA public TO "666924716777-compute@developer";
\echo '✅ Granted USAGE on schema public'
\echo ''

-- Grant table permissions (with feedback for each table)
\echo 'Step 5: Granting table permissions...'
DO $$
DECLARE
    r RECORD;
    table_count INTEGER := 0;
BEGIN
    FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public'
    LOOP
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE %I TO "666924716777-compute@developer"', r.tablename);
        table_count := table_count + 1;
        RAISE NOTICE '  ✅ Granted permissions on: %', r.tablename;
    END LOOP;
    RAISE NOTICE '';
    RAISE NOTICE 'Total tables processed: %', table_count;
END$$;
\echo ''

-- Grant sequence permissions
\echo 'Step 6: Granting sequence permissions...'
DO $$
DECLARE
    r RECORD;
    seq_count INTEGER := 0;
BEGIN
    FOR r IN SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public'
    LOOP
        EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE %I TO "666924716777-compute@developer"', r.sequence_name);
        seq_count := seq_count + 1;
        RAISE NOTICE '  ✅ Granted permissions on sequence: %', r.sequence_name;
    END LOOP;
    RAISE NOTICE '';
    RAISE NOTICE 'Total sequences processed: %', seq_count;
END$$;
\echo ''

-- Set default privileges
\echo 'Step 7: Setting default privileges for future tables...'
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

\echo 'Checking user exists...'
SELECT
    CASE WHEN COUNT(*) > 0
        THEN '✅ User exists'
        ELSE '❌ User NOT found'
    END as status
FROM pg_roles
WHERE rolname = '666924716777-compute@developer';
\echo ''

\echo 'Checking permissions granted...'
SELECT COUNT(*) as permission_count
FROM information_schema.table_privileges
WHERE grantee = '666924716777-compute@developer';
\echo ''

\echo '=========================================='
\echo '✅ DONE! IAM USER SETUP COMPLETE'
\echo '=========================================='
\echo ''
\echo 'The user "666924716777-compute@developer" is now ready for IAM authentication.'
\echo 'ChatGPT searches should now work!'
\echo ''
