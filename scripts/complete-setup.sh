#!/bin/bash
# Complete database setup and ingestion
# This script guides you through the remaining manual steps

set -e

echo "🔧 Hansard RAG Setup Completion Script"
echo "========================================"
echo ""

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

PROJECT_ID="${GCP_PROJECT_ID:-skai-fastmcp-cloudrun}"
INSTANCE_NAME="${CLOUDSQL_INSTANCE:-hansard-db}"
DATABASE_NAME="${CLOUDSQL_DATABASE:-hansard}"
REGION="${GCP_REGION:-us-central1}"

echo "📋 Configuration:"
echo "  Project: $PROJECT_ID"
echo "  Instance: $INSTANCE_NAME"
echo "  Database: $DATABASE_NAME"
echo "  Region: $REGION"
echo ""

# Step 1: Check if psql is installed
echo "🔍 Step 1: Checking for psql client..."
if command -v psql &> /dev/null; then
    echo "✅ psql is installed: $(psql --version)"
else
    echo "❌ psql is not installed"
    echo ""
    echo "Please install PostgreSQL client:"
    echo ""
    echo "  Ubuntu/Debian/WSL:"
    echo "    sudo apt-get update"
    echo "    sudo apt-get install postgresql-client"
    echo ""
    echo "  macOS:"
    echo "    brew install postgresql@15"
    echo ""
    echo "Run this script again after installing psql."
    exit 1
fi
echo ""

# Step 2: Enable pgvector extension
echo "🔌 Step 2: Enabling pgvector extension..."
echo ""
echo "Connecting to Cloud SQL instance..."
echo "(You may be prompted to enter the postgres password or use IAM authentication)"
echo ""

gcloud sql connect "$INSTANCE_NAME" \
    --user=postgres \
    --database="$DATABASE_NAME" \
    --project="$PROJECT_ID" \
    --quiet <<EOF
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

-- Exit
\q
EOF

if [ $? -eq 0 ]; then
    echo "✅ pgvector extension enabled successfully"
else
    echo "❌ Failed to enable pgvector extension"
    echo ""
    echo "Alternative: Use Cloud SQL Proxy"
    echo ""
    echo "  1. Download Cloud SQL Proxy:"
    echo "     curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.14.1/cloud-sql-proxy.linux.amd64"
    echo "     chmod +x cloud-sql-proxy"
    echo "     sudo mv cloud-sql-proxy /usr/local/bin/"
    echo ""
    echo "  2. Start proxy (in another terminal):"
    echo "     cloud-sql-proxy $PROJECT_ID:$REGION:$INSTANCE_NAME"
    echo ""
    echo "  3. Connect with psql:"
    echo "     psql -h 127.0.0.1 -U postgres -d $DATABASE_NAME"
    echo ""
    echo "  4. Then run:"
    echo "     CREATE EXTENSION IF NOT EXISTS vector;"
    exit 1
fi
echo ""

# Step 3: Initialize database schema
echo "📊 Step 3: Initializing database schema..."
echo ""

if [ ! -f "scripts/init_database.py" ]; then
    echo "❌ scripts/init_database.py not found"
    exit 1
fi

echo "Running: python scripts/init_database.py"
python scripts/init_database.py

if [ $? -eq 0 ]; then
    echo "✅ Database schema initialized successfully"
else
    echo "❌ Failed to initialize database schema"
    exit 1
fi
echo ""

# Step 4: Validate sample data
echo "📁 Step 4: Validating sample data..."
echo ""

if [ ! -d "data/sk-hansard" ]; then
    echo "❌ data/sk-hansard directory not found"
    exit 1
fi

SPEECH_COUNT=$(find data/sk-hansard -name "*.md" | wc -l)
echo "Found $SPEECH_COUNT Markdown files in data/sk-hansard"
echo ""

# Step 5: Dry run ingestion
echo "🧪 Step 5: Running dry-run ingestion test..."
echo ""

python scripts/ingest_hansard.py \
    --directory data/sk-hansard \
    --dry-run \
    --verbose

if [ $? -eq 0 ]; then
    echo "✅ Dry-run validation successful"
else
    echo "❌ Dry-run validation failed"
    exit 1
fi
echo ""

# Step 6: Confirm full ingestion
echo "🚀 Step 6: Ready for full ingestion"
echo ""
echo "The dry-run was successful. Do you want to proceed with full ingestion?"
echo "This will:"
echo "  - Process $SPEECH_COUNT speeches"
echo "  - Generate ~768-dimensional embeddings using Vertex AI"
echo "  - Store chunks and vectors in Cloud SQL"
echo ""
read -p "Proceed with full ingestion? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting full ingestion..."
    echo ""

    python scripts/ingest_hansard.py \
        --directory data/sk-hansard \
        --verbose

    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Full ingestion completed successfully!"
    else
        echo "❌ Ingestion failed"
        exit 1
    fi
else
    echo "Skipping full ingestion. You can run it manually later:"
    echo "  python scripts/ingest_hansard.py --directory data/sk-hansard"
fi
echo ""

# Step 7: Summary
echo "🎉 Setup Complete!"
echo "==================="
echo ""
echo "✅ Cloud SQL instance created and configured"
echo "✅ pgvector extension enabled"
echo "✅ Database schema initialized"
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "✅ Sample data ingested"
else
    echo "⏳ Sample data ready to ingest"
fi
echo ""
echo "Next steps:"
echo "  1. Test MCP server:"
echo "     fastmcp dev src/server.py"
echo "     # Open http://localhost:6274 in browser"
echo ""
echo "  2. Test search tool:"
echo '     {"name": "search", "arguments": {"query": "climate change", "limit": 5}}'
echo ""
echo "  3. Deploy to Cloud Run (optional):"
echo "     gcloud run deploy hansard-mcp-server --source=."
echo ""
