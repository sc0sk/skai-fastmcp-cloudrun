-- Grant database-level permissions to Cloud Run service account (IAM user)
-- This user was created as: 666924716777-compute@developer

-- Grant CONNECT on database
GRANT CONNECT ON DATABASE hansard TO "666924716777-compute@developer";

-- Grant USAGE on schema
GRANT USAGE ON SCHEMA public TO "666924716777-compute@developer";

-- Grant SELECT, INSERT, UPDATE on hansard_speeches table
GRANT SELECT, INSERT, UPDATE ON TABLE hansard_speeches TO "666924716777-compute@developer";

-- Grant USAGE on sequences (for auto-incrementing columns if any)
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO "666924716777-compute@developer";

-- Grant permissions for LangChain to manage the table
ALTER TABLE hansard_speeches OWNER TO "666924716777-compute@developer";

-- Grant permissions for local development user (scott.coleman@aph.gov.au)
-- Note: This user must be added via Cloud Console SQL Editor since gcloud doesn't recognize external users

-- Run these commands via Cloud Console SQL Editor:
-- CREATE USER "scott.coleman@aph.gov.au";
GRANT USAGE ON SCHEMA public TO "scott.coleman@aph.gov.au";
GRANT SELECT, INSERT, UPDATE ON TABLE hansard_speeches TO "scott.coleman@aph.gov.au";
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO "scott.coleman@aph.gov.au";

-- Grant permissions for local development service account (hansard-mcp-local-dev)
GRANT USAGE ON SCHEMA public TO "hansard-mcp-local-dev@skai-fastmcp-cloudrun.iam";
GRANT SELECT, INSERT, UPDATE ON TABLE hansard_speeches TO "hansard-mcp-local-dev@skai-fastmcp-cloudrun.iam";
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO "hansard-mcp-local-dev@skai-fastmcp-cloudrun.iam";
