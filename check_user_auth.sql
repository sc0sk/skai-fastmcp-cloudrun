-- Check if the IAM user exists and how it's configured

\echo '=========================================='
\echo 'CHECKING IAM USER CONFIGURATION'
\echo '=========================================='
\echo ''

-- Check if user exists
\echo 'User exists:'
SELECT rolname, rolcanlogin FROM pg_roles WHERE rolname = '666924716777-compute@developer';
\echo ''

-- Check user's authentication method (if available in pg_hba or pg_authid)
\echo 'User details:'
SELECT
    rolname,
    rolcanlogin as can_login,
    rolsuper as is_superuser,
    rolinherit as can_inherit,
    rolcreaterole as can_create_roles,
    rolcreatedb as can_create_db,
    rolreplication as can_replicate,
    rolconnlimit as connection_limit
FROM pg_roles
WHERE rolname = '666924716777-compute@developer';
\echo ''

-- Check what permissions the user has
\echo 'Database permissions:'
SELECT datname, has_database_privilege('666924716777-compute@developer', datname, 'CONNECT') as can_connect
FROM pg_database
WHERE datname = 'hansard';
\echo ''

-- Check table ownership
\echo 'Tables owned by this user:'
SELECT tablename FROM pg_tables WHERE tableowner = '666924716777-compute@developer' AND schemaname = 'public';
\echo ''

-- Check table permissions
\echo 'Permissions on hansard_speeches:'
SELECT
    grantee,
    privilege_type
FROM information_schema.table_privileges
WHERE table_name = 'hansard_speeches'
AND grantee = '666924716777-compute@developer';
\echo ''

\echo '=========================================='
\echo 'DIAGNOSIS'
\echo '=========================================='
\echo ''
\echo 'If user exists and owns tables, the 500 error might be:'
\echo '1. IAM authentication not enabled in Cloud SQL for this user'
\echo '2. User was created with password auth instead of IAM'
\echo '3. Cloud SQL IAM flag not set on the instance'
\echo ''
