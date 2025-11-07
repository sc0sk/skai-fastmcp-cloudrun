-- ==============================================================================
-- TRANSFER TABLE OWNERSHIP FROM scott.coleman@aph.gov.au
-- ==============================================================================
-- Run this while connected as: scott.coleman@aph.gov.au
-- ==============================================================================

\echo 'Transferring table ownership...'
\echo ''

-- Transfer LangChain tables to IAM user
ALTER TABLE langchain_pg_collection OWNER TO "666924716777-compute@developer";
ALTER TABLE langchain_pg_embedding OWNER TO "666924716777-compute@developer";

\echo '✅ Transferred langchain_pg_collection ownership'
\echo '✅ Transferred langchain_pg_embedding ownership'
\echo ''

-- Verify new ownership
\echo 'New table ownership:'
SELECT tablename, tableowner
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('langchain_pg_collection', 'langchain_pg_embedding');
\echo ''

\echo '=========================================='
\echo '✅ COMPLETE!'
\echo '=========================================='
\echo 'Tables now owned by 666924716777-compute@developer'
\echo 'ChatGPT should now be able to search!'
