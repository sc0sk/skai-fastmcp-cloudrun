-- ==============================================================================
-- GRANT PERMISSIONS FROM SCOTT'S ACCOUNT
-- ==============================================================================
-- Run this while authenticated as scott.coleman@aph.gov.au
-- (It's a CLOUD_IAM_USER so no password needed - uses gcloud auth)
-- ==============================================================================

\echo 'Transferring LangChain table ownership...'
ALTER TABLE langchain_pg_collection OWNER TO "666924716777-compute@developer";
ALTER TABLE langchain_pg_embedding OWNER TO "666924716777-compute@developer";
\echo '✅ Transferred ownership'
\echo ''

\echo 'Verifying ownership...'
SELECT tablename, tableowner FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;
\echo ''

\echo '=========================================='
\echo '✅ COMPLETE!'
\echo '=========================================='
\echo 'ChatGPT searches should now work!'
