-- Grant database-level permissions to IAM user scott.coleman@aph.gov.au
-- Run this via: gcloud sql connect hansard-db-v2 --user=postgres --database=hansard

-- Grant CONNECT privilege on database
GRANT CONNECT ON DATABASE hansard TO "scott.coleman@aph.gov.au";

-- Grant schema usage (required for accessing tables)
GRANT USAGE ON SCHEMA public TO "scott.coleman@aph.gov.au";

-- Grant table permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "scott.coleman@aph.gov.au";

-- Grant sequence permissions (for auto-increment IDs)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "scott.coleman@aph.gov.au";

-- Grant default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "scott.coleman@aph.gov.au";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO "scott.coleman@aph.gov.au";

-- Grant CREATE privilege (needed for pgvector extension and table creation)
GRANT CREATE ON SCHEMA public TO "scott.coleman@aph.gov.au";

-- Verify grants
\dp
