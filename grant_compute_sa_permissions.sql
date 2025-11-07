-- ==============================================================================
-- GRANT PERMISSIONS TO COMPUTE SERVICE ACCOUNT
-- ==============================================================================
-- Run this as postgres user with password: efzDDQ1Mxb8VOOAUzJsEVsKdJxtBXTdF
-- ==============================================================================

-- Step 1: Make postgres a superuser temporarily
ALTER USER postgres WITH SUPERUSER;
\echo '✅ Granted postgres SUPERUSER privileges'
\echo ''

-- Step 2: Transfer ownership of LangChain tables to compute service account
\echo 'Transferring table ownership...'
ALTER TABLE langchain_pg_collection OWNER TO "666924716777-compute@developer";
ALTER TABLE langchain_pg_embedding OWNER TO "666924716777-compute@developer";
\echo '✅ Transferred langchain_pg_collection'
\echo '✅ Transferred langchain_pg_embedding'
\echo ''

-- Step 3: Grant all privileges on all tables
\echo 'Granting privileges on all tables...'
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "666924716777-compute@developer";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "666924716777-compute@developer";
\echo '✅ Granted all privileges'
\echo ''

-- Step 4: Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL PRIVILEGES ON TABLES TO "666924716777-compute@developer";

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL PRIVILEGES ON SEQUENCES TO "666924716777-compute@developer";
\echo '✅ Set default privileges'
\echo ''

-- Step 5: Remove superuser from postgres (security best practice)
ALTER USER postgres WITH NOSUPERUSER;
\echo '✅ Removed SUPERUSER from postgres'
\echo ''

-- Verification
\echo '=========================================='
\echo 'VERIFICATION'
\echo '=========================================='
\echo ''

\echo 'Table ownership:'
SELECT tablename, tableowner FROM pg_tables WHERE schemaname = 'public';
\echo ''

\echo 'Permissions for 666924716777-compute@developer:'
SELECT table_name, privilege_type
FROM information_schema.table_privileges
WHERE grantee = '666924716777-compute@developer'
ORDER BY table_name, privilege_type;
\echo ''

\echo '=========================================='
\echo '✅ COMPLETE!'
\echo '=========================================='
\echo 'ChatGPT searches should now work!'
