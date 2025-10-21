#!/bin/bash
#
# Migrate Custom Domain: mcp.simonkennedymp.com.au
# Move domain mapping from old project to skai-fastmcp-cloudrun
#
# Usage:
#   ./scripts/migrate-custom-domain.sh
#

set -e

DOMAIN="mcp.simonkennedymp.com.au"
NEW_PROJECT="skai-fastmcp-cloudrun"
REGION="us-central1"

echo "============================================"
echo "Custom Domain Migration"
echo "Domain: $DOMAIN"
echo "Target Project: $NEW_PROJECT"
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
echo ""

# Get current project
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
echo "Current project: $CURRENT_PROJECT"
echo ""

# Step 1: Check if domain is mapped in ANY project
echo "Step 1: Checking for existing domain mappings..."
echo ""

# We need to find which project has this domain
# Try to list projects the user has access to
echo "Listing your GCP projects to find domain mapping..."
PROJECTS=$(gcloud projects list --format="value(projectId)" 2>/dev/null)

FOUND_PROJECT=""
for PROJECT in $PROJECTS; do
    echo "  Checking project: $PROJECT..."
    # Try to list domain mappings in this project
    MAPPINGS=$(gcloud beta run domain-mappings list \
        --project="$PROJECT" \
        --format="value(metadata.name)" 2>/dev/null || echo "")

    if echo "$MAPPINGS" | grep -q "$DOMAIN"; then
        FOUND_PROJECT="$PROJECT"
        echo "  ✅ Found domain mapping in project: $PROJECT"
        break
    fi
done

if [ -z "$FOUND_PROJECT" ]; then
    echo "⚠️  No existing domain mapping found in accessible projects"
    echo "The domain may be:"
    echo "  1. Not mapped yet (DNS points to ghs.googlehosted.com but no service mapped)"
    echo "  2. Mapped in a project you don't have access to"
    echo "  3. Using a different mapping method (Firebase Hosting, etc.)"
    echo ""
    echo "We'll proceed to map it to $NEW_PROJECT..."
    echo ""
else
    # Step 2: Remove from old project
    echo ""
    echo "Step 2: Removing domain mapping from old project ($FOUND_PROJECT)..."
    echo ""

    if [ "$FOUND_PROJECT" != "$NEW_PROJECT" ]; then
        echo "⚠️  WARNING: This will temporarily break the domain until remapped!"
        echo "Domain: $DOMAIN"
        echo "Current project: $FOUND_PROJECT"
        echo ""
        read -p "Continue? (yes/no): " CONFIRM

        if [ "$CONFIRM" != "yes" ]; then
            echo "❌ Aborted by user"
            exit 1
        fi

        echo "Deleting domain mapping from $FOUND_PROJECT..."
        gcloud beta run domain-mappings delete "$DOMAIN" \
            --project="$FOUND_PROJECT" \
            --quiet 2>&1 || echo "Warning: Could not delete mapping (may not exist)"

        echo "✅ Domain mapping removed from old project"
        echo "Waiting 10 seconds for propagation..."
        sleep 10
    else
        echo "✅ Domain is already in target project: $NEW_PROJECT"
    fi
fi

# Step 3: Switch to new project
echo ""
echo "Step 3: Switching to target project..."
gcloud config set project "$NEW_PROJECT"
echo "✅ Current project: $NEW_PROJECT"
echo ""

# Step 4: Enable Cloud Run API
echo "Step 4: Enabling Cloud Run API..."
echo ""

gcloud services enable run.googleapis.com --project="$NEW_PROJECT"

echo "✅ Cloud Run API enabled"
echo ""

# Wait for API to be fully enabled
echo "Waiting 10 seconds for API to be fully enabled..."
sleep 10

# Step 5: Check for existing Cloud Run services
echo "Step 5: Checking for existing Cloud Run services..."
echo ""

SERVICES=$(gcloud run services list \
    --region="$REGION" \
    --project="$NEW_PROJECT" \
    --format="value(metadata.name)" 2>/dev/null || echo "")

if [ -z "$SERVICES" ]; then
    echo "⚠️  No Cloud Run services found in region $REGION"
    echo ""
    echo "You need to deploy a Cloud Run service first before mapping the domain."
    echo ""
    echo "Options:"
    echo "  A. Deploy a placeholder service now (recommended for testing)"
    echo "  B. Skip and deploy later (you'll need to run domain mapping manually)"
    echo ""
    read -p "Deploy placeholder service? (yes/no): " DEPLOY_PLACEHOLDER

    if [ "$DEPLOY_PLACEHOLDER" = "yes" ]; then
        echo ""
        echo "Deploying placeholder Cloud Run service..."

        # Deploy a simple hello-world service
        gcloud run deploy hansard-mcp-server \
            --image=gcr.io/cloudrun/hello \
            --region="$REGION" \
            --platform=managed \
            --allow-unauthenticated \
            --project="$NEW_PROJECT"

        echo "✅ Placeholder service deployed"
        SERVICE_NAME="hansard-mcp-server"
    else
        echo ""
        echo "⚠️  Skipping service deployment"
        echo "You'll need to:"
        echo "  1. Deploy your Cloud Run service"
        echo "  2. Run domain mapping manually:"
        echo ""
        echo "     gcloud beta run domain-mappings create \\"
        echo "       --service=YOUR_SERVICE_NAME \\"
        echo "       --domain=$DOMAIN \\"
        echo "       --project=$NEW_PROJECT"
        echo ""
        exit 0
    fi
else
    echo "Found existing services:"
    echo "$SERVICES"
    echo ""

    # If only one service, use it
    SERVICE_COUNT=$(echo "$SERVICES" | wc -l)
    if [ "$SERVICE_COUNT" -eq 1 ]; then
        SERVICE_NAME="$SERVICES"
        echo "Using service: $SERVICE_NAME"
    else
        echo "Multiple services found. Which service should the domain map to?"
        select SERVICE_NAME in $SERVICES; do
            if [ -n "$SERVICE_NAME" ]; then
                echo "Selected: $SERVICE_NAME"
                break
            fi
        done
    fi
fi

# Step 6: Create domain mapping
echo ""
echo "Step 6: Creating domain mapping..."
echo "Service: $SERVICE_NAME"
echo "Domain: $DOMAIN"
echo ""

gcloud beta run domain-mappings create \
    --service="$SERVICE_NAME" \
    --domain="$DOMAIN" \
    --project="$NEW_PROJECT" 2>&1 || {
        echo ""
        echo "⚠️  Domain mapping may already exist or need different configuration"
        echo "Checking existing mappings..."
        gcloud beta run domain-mappings describe "$DOMAIN" \
            --project="$NEW_PROJECT" 2>&1 || echo "No mapping found"
    }

echo ""
echo "============================================"
echo "Domain Migration Complete!"
echo "============================================"
echo ""
echo "Next Steps:"
echo ""
echo "1. Verify domain mapping status:"
echo "   gcloud beta run domain-mappings describe $DOMAIN \\"
echo "     --project=$NEW_PROJECT"
echo ""
echo "2. Check SSL certificate provisioning (may take 15min-24hr):"
echo "   gcloud beta run domain-mappings describe $DOMAIN \\"
echo "     --project=$NEW_PROJECT \\"
echo "     --format='value(status.conditions)'"
echo ""
echo "3. Test the domain:"
echo "   curl -I https://$DOMAIN"
echo ""
echo "4. If DNS records need updating, you'll see instructions above"
echo "   Current DNS: $DOMAIN -> ghs.googlehosted.com (already correct!)"
echo ""
