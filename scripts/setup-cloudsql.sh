#!/bin/bash
# Setup Cloud SQL PostgreSQL instance with pgvector extension
#
# Usage:
#   ./scripts/setup-cloudsql.sh
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - GCP_PROJECT_ID set in .env or environment
#   - Cloud SQL Admin API enabled

set -e

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-skai-fastmcp-cloudrun}"
REGION="${GCP_REGION:-us-central1}"
INSTANCE_NAME="${CLOUDSQL_INSTANCE:-hansard-db}"
DATABASE_NAME="${CLOUDSQL_DATABASE:-hansard}"
POSTGRES_VERSION="POSTGRES_15"
TIER="db-custom-2-4096"  # 2 vCPU, 4GB RAM (adjust as needed)

echo "🔧 Cloud SQL PostgreSQL Setup"
echo "=============================="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Instance: $INSTANCE_NAME"
echo "Database: $DATABASE_NAME"
echo ""

# Set active project
echo "📌 Setting active GCP project..."
gcloud config set project "$PROJECT_ID"

# Check if instance already exists
if gcloud sql instances describe "$INSTANCE_NAME" --project="$PROJECT_ID" 2>/dev/null; then
    echo "✅ Cloud SQL instance '$INSTANCE_NAME' already exists"
else
    echo "📦 Creating Cloud SQL PostgreSQL instance..."
    echo "   This may take 5-10 minutes..."

    gcloud sql instances create "$INSTANCE_NAME" \
        --database-version="$POSTGRES_VERSION" \
        --tier="$TIER" \
        --region="$REGION" \
        --backup-start-time=03:00 \
        --project="$PROJECT_ID"

    echo "✅ Cloud SQL instance created"
fi

# Wait for instance to be ready
echo "⏳ Waiting for instance to be ready..."
gcloud sql operations wait \
    --project="$PROJECT_ID" \
    $(gcloud sql operations list --instance="$INSTANCE_NAME" --project="$PROJECT_ID" --limit=1 --format="value(name)") \
    --timeout=600 || true

# Check if database exists
if gcloud sql databases describe "$DATABASE_NAME" --instance="$INSTANCE_NAME" --project="$PROJECT_ID" 2>/dev/null; then
    echo "✅ Database '$DATABASE_NAME' already exists"
else
    echo "📊 Creating database '$DATABASE_NAME'..."
    gcloud sql databases create "$DATABASE_NAME" \
        --instance="$INSTANCE_NAME" \
        --project="$PROJECT_ID"

    echo "✅ Database created"
fi

# Enable pgvector extension (requires connecting to database)
echo "🔌 Enabling pgvector extension..."
echo "   Note: This requires psql client and instance connection"

# Create SQL commands file
cat > /tmp/setup-pgvector.sql <<'EOF'
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify pgvector is installed
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
EOF

echo "   Run the following command to enable pgvector:"
echo ""
echo "   gcloud sql connect $INSTANCE_NAME --user=postgres --database=$DATABASE_NAME --project=$PROJECT_ID"
echo ""
echo "   Then execute:"
echo "   CREATE EXTENSION IF NOT EXISTS vector;"
echo ""

# Output connection string
CONNECTION_STRING="$PROJECT_ID:$REGION:$INSTANCE_NAME"
echo ""
echo "✅ Cloud SQL Setup Complete!"
echo "=============================="
echo ""
echo "Instance Details:"
echo "  - Instance Name: $INSTANCE_NAME"
echo "  - Connection Name: $CONNECTION_STRING"
echo "  - Database: $DATABASE_NAME"
echo "  - Region: $REGION"
echo ""
echo "Next Steps:"
echo "1. Enable pgvector extension (see command above)"
echo "2. Run database schema initialization:"
echo "   python scripts/init_database.py"
echo ""
echo "Connection Examples:"
echo ""
echo "# Using gcloud SQL proxy:"
echo "gcloud sql connect $INSTANCE_NAME --user=postgres --database=$DATABASE_NAME"
echo ""
echo "# Using psql with proxy:"
echo "./cloud-sql-proxy $CONNECTION_STRING &"
echo "psql -h 127.0.0.1 -U postgres -d $DATABASE_NAME"
echo ""
