#!/bin/bash

# =============================================================================
# IAM Setup for Cloud SQL + Cloud Run Integration
# Purpose: Configure service accounts with proper Cloud SQL IAM authentication
# =============================================================================

set -euo pipefail

# Configuration
PROJECT_ID="skai-fastmcp-cloudrun"
REGION="us-central1"
CLOUD_SQL_INSTANCE="hansard-db-v2"
CLOUD_RUN_SERVICE="hansard-mcp-server"
DB_USER="deployment_service"

# Service account details
DEFAULT_COMPUTE_SA="${PROJECT_ID}-compute@developer.gserviceaccount.com"
DEDICATED_SA="hansard-cloud-sql-iam@${PROJECT_ID}.iam.gserviceaccount.com"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         Cloud SQL IAM Authentication Setup                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"

# Step 1: Create dedicated service account for Cloud SQL IAM
echo ""
echo "Step 1: Creating dedicated service account..."
if gcloud iam service-accounts describe "${DEDICATED_SA}" &>/dev/null; then
    echo "  ✓ Service account already exists: ${DEDICATED_SA}"
else
    gcloud iam service-accounts create hansard-cloud-sql-iam \
        --display-name="Hansard Cloud SQL IAM Authentication" \
        --description="Service account for Cloud Run to Cloud SQL IAM-based access"
    echo "  ✓ Created service account: ${DEDICATED_SA}"
fi

# Step 2: Grant Cloud SQL Client role to the dedicated service account
echo ""
echo "Step 2: Granting Cloud SQL Client role..."
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${DEDICATED_SA}" \
    --role="roles/cloudsql.client" \
    --condition=None \
    --quiet
echo "  ✓ Granted roles/cloudsql.client"

# Step 3: Grant Service Account User role (for Cloud Run to use it)
echo ""
echo "Step 3: Granting Service Account User role to default compute SA..."
gcloud iam service-accounts add-iam-policy-binding "${DEDICATED_SA}" \
    --member="serviceAccount:${DEFAULT_COMPUTE_SA}" \
    --role="roles/iam.serviceAccountUser" \
    --condition=None \
    --quiet
echo "  ✓ Default compute SA can now use the dedicated SA"

# Step 4: Create database user for IAM authentication
echo ""
echo "Step 4: Creating database user for IAM authentication..."
echo "  Note: This creates a PostgreSQL user matching the service account email"
echo "  User will be: ${DEDICATED_SA}"

# Get Cloud SQL proxy
if ! command -v cloud_sql_proxy &> /dev/null; then
    echo "  Installing cloud_sql_proxy..."
    curl -o ./cloud_sql_proxy https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64
    chmod +x ./cloud_sql_proxy
fi

# Start Cloud SQL proxy in background
echo "  Starting Cloud SQL proxy..."
./cloud_sql_proxy -instances="${PROJECT_ID}:${REGION}:${CLOUD_SQL_INSTANCE}"=tcp:5432 &
PROXY_PID=$!
sleep 2

# Create IAM-based database user
echo "  Creating database user..."
psql -h localhost -U postgres -d postgres <<EOF || true
-- Drop existing IAM user if present
DROP USER IF EXISTS "${DEDICATED_SA}" CASCADE;

-- Create IAM-authenticated user
CREATE USER "${DEDICATED_SA}" WITH LOGIN;

-- Grant necessary permissions
GRANT CONNECT ON DATABASE hansard_db_fresh TO "${DEDICATED_SA}";
GRANT USAGE ON SCHEMA public TO "${DEDICATED_SA}";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "${DEDICATED_SA}";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "${DEDICATED_SA}";
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO "${DEDICATED_SA}";

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "${DEDICATED_SA}";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "${DEDICATED_SA}";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO "${DEDICATED_SA}";

\du

EOF

# Kill proxy
kill $PROXY_PID 2>/dev/null || true
wait $PROXY_PID 2>/dev/null || true

echo "  ✓ Database user created: ${DEDICATED_SA}"

# Step 5: Update Cloud Run service to use dedicated service account
echo ""
echo "Step 5: Updating Cloud Run service to use dedicated service account..."
gcloud run services update "${CLOUD_RUN_SERVICE}" \
    --region="${REGION}" \
    --service-account="${DEDICATED_SA}" \
    --quiet
echo "  ✓ Cloud Run service now uses: ${DEDICATED_SA}"

# Step 6: Verify setup
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    VERIFICATION                               ║"
echo "╚════════════════════════════════════════════════════════════════╝"

echo ""
echo "Service Account: ${DEDICATED_SA}"
gcloud iam service-accounts describe "${DEDICATED_SA}" \
    --format='table(email,displayName,disabled)'

echo ""
echo "IAM Roles for service account:"
gcloud projects get-iam-policy "${PROJECT_ID}" \
    --flatten="bindings[].members" \
    --format='table(bindings.role)' \
    --filter="bindings.members:${DEDICATED_SA}" || true

echo ""
echo "Cloud Run Service Account:"
gcloud run services describe "${CLOUD_RUN_SERVICE}" \
    --region="${REGION}" \
    --format='value(spec.template.spec.serviceAccountName)'

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    SETUP COMPLETE                             ║"
echo "╚════════════════════════════════════════════════════════════════╝"

echo ""
echo "Next steps:"
echo "  1. Update environment variables in Cloud Run:"
echo "     CLOUD_SQL_USER=${DEDICATED_SA}"
echo "     CLOUD_SQL_ENABLE_IAM_AUTH=true"
echo ""
echo "  2. Update cloud_sql_engine.py to use these settings"
echo ""
echo "  3. Redeploy Cloud Run service"
echo ""
echo "  4. Test database connection with new service account"

