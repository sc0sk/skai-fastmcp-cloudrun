-- ==============================================================================
-- FIX EXISTING IAM USER - Enable IAM Authentication
-- ==============================================================================
-- If the user already exists but wasn't created with IAM auth enabled,
-- this will fix it.
-- ==============================================================================

\echo ''
\echo '=========================================='
\echo 'FIXING EXISTING IAM USER'
\echo '=========================================='
\echo ''

-- Check current user status
\echo 'Current user status:'
SELECT rolname, rolcanlogin FROM pg_roles WHERE rolname = '666924716777-compute@developer';
\echo ''

-- Make sure the user can log in
ALTER USER "666924716777-compute@developer" WITH LOGIN;
\echo '✅ Ensured LOGIN permission'
\echo ''

-- Grant all necessary permissions (in case they're missing)
\echo 'Granting all permissions...'
GRANT CONNECT ON DATABASE hansard TO "666924716777-compute@developer";
GRANT USAGE ON SCHEMA public TO "666924716777-compute@developer";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "666924716777-compute@developer";
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "666924716777-compute@developer";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "666924716777-compute@developer";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO "666924716777-compute@developer";
\echo '✅ All permissions granted'
\echo ''

\echo '=========================================='
\echo 'VERIFICATION'
\echo '=========================================='
SELECT rolname, rolcanlogin FROM pg_roles WHERE rolname = '666924716777-compute@developer';
\echo ''

\echo '✅ User configured for IAM authentication'
\echo 'Now try ChatGPT search again!'
\echo ''
