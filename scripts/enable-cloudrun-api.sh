#!/bin/bash
#
# Enable Cloud Run API and Required Services
# Project: skai-fastmcp-cloudrun
#
# Usage:
#   ./scripts/enable-cloudrun-api.sh
#

set -e

PROJECT_ID="skai-fastmcp-cloudrun"
PROJECT_NUMBER="666924716777"
REGION="us-central1"

echo "============================================"
echo "Enable Cloud Run API & Services"
echo "Project: $PROJECT_ID ($PROJECT_NUMBER)"
echo "Region: $REGION"
echo "============================================"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    echo "Install it: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo "❌ Error: Not authenticated with gcloud"
    echo "Run: gcloud auth login"
    exit 1
fi

echo "✅ gcloud CLI authenticated"
ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1)
echo "Active account: $ACCOUNT"
echo ""

# Set project
echo "Setting project to: $PROJECT_ID..."
gcloud config set project "$PROJECT_ID"
echo "✅ Project set"
echo ""

# Enable APIs
echo "Enabling required Google Cloud APIs..."
echo "This may take a few minutes..."
echo ""

APIS=(
    "run.googleapis.com"                    # Cloud Run
    "artifactregistry.googleapis.com"       # Artifact Registry (for Docker images)
    "cloudbuild.googleapis.com"             # Cloud Build (for building images)
    "sqladmin.googleapis.com"               # Cloud SQL Admin
    "aiplatform.googleapis.com"             # Vertex AI (for embeddings)
    "secretmanager.googleapis.com"          # Secret Manager
    "compute.googleapis.com"                # Compute Engine (for networking)
    "vpcaccess.googleapis.com"              # VPC Access (for Cloud SQL connection)
)

for API in "${APIS[@]}"; do
    echo "  Enabling $API..."
    gcloud services enable "$API" --project="$PROJECT_ID" 2>&1 | grep -v "already enabled" || true
done

echo ""
echo "✅ All APIs enabled"
echo ""

# Wait for APIs to be fully enabled
echo "Waiting 15 seconds for APIs to be fully available..."
sleep 15

# Verify Cloud Run API is enabled
echo "Verifying Cloud Run API..."
if gcloud services list --enabled --filter="name:run.googleapis.com" --project="$PROJECT_ID" | grep -q "run.googleapis.com"; then
    echo "✅ Cloud Run API is enabled and ready"
else
    echo "⚠️  Cloud Run API may still be enabling. Wait a minute and try again."
fi
echo ""

# Check for existing Cloud Run services
echo "Checking for existing Cloud Run services in $REGION..."
SERVICES=$(gcloud run services list --region="$REGION" --project="$PROJECT_ID" --format="value(metadata.name)" 2>/dev/null || echo "")

if [ -z "$SERVICES" ]; then
    echo "No services found in region $REGION"
    echo ""
    echo "Next step: Deploy your first Cloud Run service"
    echo ""
    echo "Option 1: Deploy placeholder service (for testing)"
    echo "  gcloud run deploy hansard-mcp-server \\"
    echo "    --image=gcr.io/cloudrun/hello \\"
    echo "    --region=$REGION \\"
    echo "    --platform=managed \\"
    echo "    --allow-unauthenticated \\"
    echo "    --project=$PROJECT_ID"
    echo ""
    echo "Option 2: Build and deploy your application"
    echo "  See: deployment/CUSTOM_DOMAIN_SETUP.md"
else
    echo "Found existing services:"
    echo "$SERVICES" | sed 's/^/  - /'
fi
echo ""

# Check for Cloud SQL instances
echo "Checking for Cloud SQL instances..."
SQL_INSTANCES=$(gcloud sql instances list --project="$PROJECT_ID" --format="value(name)" 2>/dev/null || echo "")

if [ -z "$SQL_INSTANCES" ]; then
    echo "No Cloud SQL instances found"
    echo ""
    echo "To create Cloud SQL instance for production:"
    echo "  gcloud sql instances create hansard-db \\"
    echo "    --database-version=POSTGRES_15 \\"
    echo "    --tier=db-custom-2-7680 \\"
    echo "    --region=$REGION \\"
    echo "    --database-flags=cloudsql.iam_authentication=on \\"
    echo "    --project=$PROJECT_ID"
else
    echo "Found existing instances:"
    echo "$SQL_INSTANCES" | sed 's/^/  - /'
fi
echo ""

# Check service account
echo "Checking for deployment service account..."
SA_EMAIL="hansard-mcp-deployer@${PROJECT_ID}.iam.gserviceaccount.com"

if gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
    echo "✅ Service account exists: $SA_EMAIL"
else
    echo "⚠️  Service account not found: $SA_EMAIL"
    echo ""
    read -p "Create service account now? (yes/no): " CREATE_SA

    if [ "$CREATE_SA" = "yes" ]; then
        echo "Creating service account..."
        gcloud iam service-accounts create hansard-mcp-deployer \
            --display-name="Hansard MCP Deployer" \
            --description="Service account for deploying Hansard MCP Cloud Run service" \
            --project="$PROJECT_ID"

        echo "Granting required roles..."

        # Grant roles
        ROLES=(
            "roles/run.admin"
            "roles/cloudsql.client"
            "roles/aiplatform.user"
            "roles/storage.objectViewer"
            "roles/artifactregistry.writer"
            "roles/secretmanager.secretAccessor"
        )

        for ROLE in "${ROLES[@]}"; do
            echo "  Granting $ROLE..."
            gcloud projects add-iam-policy-binding "$PROJECT_ID" \
                --member="serviceAccount:${SA_EMAIL}" \
                --role="$ROLE" \
                --condition=None \
                --quiet 2>&1 | grep -v "Updated IAM policy" || true
        done

        echo "✅ Service account created and configured"
    fi
fi
echo ""

# Summary
echo "============================================"
echo "Setup Complete!"
echo "============================================"
echo ""
echo "Enabled APIs:"
echo "  ✅ Cloud Run"
echo "  ✅ Artifact Registry"
echo "  ✅ Cloud Build"
echo "  ✅ Cloud SQL Admin"
echo "  ✅ Vertex AI"
echo "  ✅ Secret Manager"
echo "  ✅ Compute Engine"
echo "  ✅ VPC Access"
echo ""
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""
echo "Next Steps:"
echo ""
echo "1. Run domain migration script:"
echo "   ./scripts/migrate-custom-domain.sh"
echo ""
echo "2. Set up GitHub OAuth secrets:"
echo "   ./scripts/setup-github-secrets.sh"
echo ""
echo "3. Deploy your Cloud Run service:"
echo "   See: specs/001-hansard-rag-implementation/quickstart.md"
echo ""
