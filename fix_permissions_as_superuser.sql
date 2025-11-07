-- ==============================================================================
-- FIX LANGCHAIN TABLE PERMISSIONS (RUN AS SUPERUSER)
-- ==============================================================================
-- Run this as 'postgres' user BUT first we need to make postgres a superuser
-- OR run as the cloudsqlsuperuser role
-- ==============================================================================

-- First, let's check who owns the tables
\echo 'Current table ownership:'
SELECT tablename, tableowner FROM pg_tables WHERE schemaname = 'public';
\echo ''

-- Grant permissions directly (this will work if you're the owner or superuser)
\echo 'Granting permissions...'

DO $$
DECLARE
    v_table RECORD;
BEGIN
    -- Loop through all tables and grant permissions
    FOR v_table IN
        SELECT tablename FROM pg_tables WHERE schemaname = 'public'
    LOOP
        BEGIN
            EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON %I TO %L',
                v_table.tablename,
                '666924716777-compute@developer');
            RAISE NOTICE '✅ Granted permissions on %', v_table.tablename;
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE '❌ Could not grant on % - Error: %', v_table.tablename, SQLERRM;
        END;
    END LOOP;
END$$;

\echo ''
\echo 'Granting sequence permissions...'
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "666924716777-compute@developer";

\echo ''
\echo 'Verifying permissions:'
SELECT
    grantee,
    table_name,
    privilege_type
FROM information_schema.table_privileges
WHERE grantee = '666924716777-compute@developer'
ORDER BY table_name, privilege_type;
