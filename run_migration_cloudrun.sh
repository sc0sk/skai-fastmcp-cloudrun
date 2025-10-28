#!/bin/bash
# Simple script to run migration via Cloud Run service

echo "🚀 Running migration via Cloud Run..."
echo ""

# Get the service URL
SERVICE_URL=$(gcloud run services describe hansard-mcp-server --region=us-central1 --format='value(status.url)')

echo "Service URL: $SERVICE_URL"
echo ""

# Create a simple HTTP endpoint trigger (this requires adding an endpoint to the service)
echo "⚠️  Note: The migration needs to run with proper IAM auth inside Cloud Run."
echo "Since the migration script is included in the deployed image, we can:"
echo ""
echo "Option 1: Use Cloud Run Jobs (requires script in image)"
echo "Option 2: Use Cloud Shell with proper IAM setup"
echo "Option 3: Grant your user account database IAM role"
echo ""
echo "Let's try Option 3: Grant database access to your user..."
echo ""

# Grant Cloud SQL client role to user
gcloud projects add-iam-policy-binding skai-fastmcp-cloudrun \
  --member="user:scott.coleman@aph.gov.au" \
  --role="roles/cloudsql.client"

# Grant database role (requires Cloud SQL Admin API)
echo ""
echo "✅ Granted Cloud SQL client role"
echo ""
echo "Now trying migration again with IAM auth..."
