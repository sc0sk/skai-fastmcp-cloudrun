#!/bin/bash
# Feature 018 Production Deployment Script
# Deploys MCP Tools Quality Improvements with OAuth to Cloud Run
# Usage: ./deploy_feature_018.sh [--dry-run]

set -e

PROJECT_ID="skai-fastmcp-cloudrun"
REGION="us-central1"
SERVICE_NAME="hansard-mcp-server"
FEATURE_BRANCH="018-mcp-tools-quality-improvements"
DRY_RUN=${1:-"--dry-run"}

echo "🚀 Feature 018 Production Deployment Script"
echo "=========================================="
echo "Project: $PROJECT_ID"
echo "Service: $SERVICE_NAME"
echo "Region: $REGION"
echo "Feature: $FEATURE_BRANCH"
echo "Mode: $DRY_RUN"
echo ""

# Verify on correct branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "$FEATURE_BRANCH" ]; then
    echo "❌ Not on $FEATURE_BRANCH branch (currently on $CURRENT_BRANCH)"
    exit 1
fi

# Set project
echo "📋 Setting GCP project..."
gcloud config set project $PROJECT_ID

# Verify OAuth secrets
echo "🔐 Verifying OAuth secrets..."
if ! gcloud secrets describe github-oauth-client-id > /dev/null 2>&1; then
    echo "❌ OAuth secret 'github-oauth-client-id' not found in Secret Manager"
    echo "   Please create it with: echo -n 'YOUR_CLIENT_ID' | gcloud secrets create github-oauth-client-id --data-file=-"
    exit 1
fi

if ! gcloud secrets describe github-oauth-client-secret > /dev/null 2>&1; then
    echo "❌ OAuth secret 'github-oauth-client-secret' not found in Secret Manager"
    echo "   Please create it with: echo -n 'YOUR_CLIENT_SECRET' | gcloud secrets create github-oauth-client-secret --data-file=-"
    exit 1
fi
echo "✅ OAuth secrets verified"

# Display deployment command
echo ""
echo "📦 Deployment Configuration:"
echo "=================================="
DEPLOY_CMD="gcloud run deploy $SERVICE_NAME \
  --source . \
  --region=$REGION \
  --platform=managed \
  --no-allow-unauthenticated \
  --set-env-vars=PYTHONPATH=/app/src,FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.github.GitHubProvider,FASTMCP_SERVER_AUTH_GITHUB_BASE_URL=https://mcp.simonkennedymp.com.au \
  --set-secrets=FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=github-oauth-client-id:latest,FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=github-oauth-client-secret:latest \
  --cpu=2 \
  --memory=2Gi \
  --max-instances=10 \
  --timeout=300 \
  --cpu-boost \
  --vpc-connector=hansard-vpc-connector \
  --vpc-egress=private-ranges-only \
  --add-cloudsql-instances=skai-fastmcp-cloudrun:us-central1:hansard-db-v2 \
  --service-account=666924716777-compute@developer.gserviceaccount.com"

echo "$DEPLOY_CMD"
echo "=================================="

if [ "$DRY_RUN" == "--dry-run" ]; then
    echo ""
    echo "✨ Dry run complete - no changes made"
    echo "Run with: ./deploy_feature_018.sh --deploy"
    exit 0
fi

# Confirm deployment
echo ""
echo "⚠️  This will deploy to PRODUCTION!"
echo ""
read -p "Type 'yes' to confirm deployment: " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Deployment cancelled"
    exit 1
fi

# Execute deployment
echo ""
echo "🚀 Deploying Feature 018 to Cloud Run..."
eval $DEPLOY_CMD

# Wait for deployment
echo ""
echo "⏳ Waiting for deployment to complete..."
gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.conditions[0].message)' | tail -5

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')
echo ""
echo "✅ Deployment completed successfully!"
echo "📍 Service URL: $SERVICE_URL"
echo ""
echo "🔐 Authentication Status:"
gcloud run services describe $SERVICE_NAME --region=$REGION \
  --format='value(spec.template.spec.containers[0].env[name=FASTMCP_SERVER_AUTH].value)'

echo ""
echo "📝 Next steps:"
echo "1. Test authentication is enforced: curl $SERVICE_URL"
echo "   Expected: 401 Unauthorized or OAuth redirect"
echo "2. Test MCP tools with GitHub OAuth token"
echo "3. Monitor logs: gcloud run services logs read $SERVICE_NAME --region=$REGION --limit=50"
echo ""
echo "✨ Feature 018 deployment complete!"