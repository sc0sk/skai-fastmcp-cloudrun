-- Grant database permissions to Cloud Run service account for IAM authentication
-- IAM user: 666924716777-compute@developer

-- Connect to hansard database
\c hansard

-- Grant connection to database
GRANT CONNECT ON DATABASE hansard TO "666924716777-compute@developer";

-- Grant schema usage
GRANT USAGE ON SCHEMA public TO "666924716777-compute@developer";

-- Grant table permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "666924716777-compute@developer";

-- Grant sequence permissions (for auto-increment IDs)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "666924716777-compute@developer";

-- Grant permissions on future tables (for schema changes)
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "666924716777-compute@developer";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO "666924716777-compute@developer";

-- Verify permissions
\dp speeches
\dp speech_chunks
