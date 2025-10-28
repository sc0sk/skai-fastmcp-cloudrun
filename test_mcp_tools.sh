#!/bin/bash
# Test MCP server tools using MCP Inspector

set -e

cd /home/user/skai-fastmcp-cloudrun

echo "=== Testing MCP Server Tools ==="
echo ""

# Set environment variables
export USE_IAM_AUTH=1
export GCP_PROJECT_ID=skai-fastmcp-cloudrun
export GCP_REGION=us-central1
export CLOUDSQL_INSTANCE=hansard-db-v2
export CLOUDSQL_DATABASE=hansard
export VECTOR_BACKEND=postgres
export DANGEROUSLY_OMIT_AUTH=true

# Start MCP server and test with Inspector
echo "Starting MCP Inspector..."
echo "Server command: uv run python3 -m src.server"
echo ""

# Run inspector
npx @modelcontextprotocol/inspector uv run python3 -m src.server
