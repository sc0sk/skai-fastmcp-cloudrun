-- Check who owns the tables
SELECT
    schemaname,
    tablename,
    tableowner
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- Check what permissions the IAM user currently has
SELECT
    grantee,
    table_name,
    privilege_type
FROM information_schema.table_privileges
WHERE grantee = '666924716777-compute@developer'
ORDER BY table_name, privilege_type;
