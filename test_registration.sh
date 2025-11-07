#!/bin/bash
set -e

echo "=== Testing OAuth Client Registration ==="
echo ""

echo "Registering test client..."
RESPONSE=$(curl -s -X POST "https://mcp.simonkennedymp.com.au/register" \
  -H "Content-Type: application/json" \
  -d '{"client_name": "Test Persistence Client", "redirect_uris": ["https://test.example.com/callback"]}')

echo "$RESPONSE" | python3 -m json.tool

# Extract client_id
CLIENT_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['client_id'])")

echo ""
echo "Client registered successfully!"
echo "Client ID: $CLIENT_ID"
echo ""
echo "To test persistence, this client should remain registered after server restart."
echo ""
echo "Test authorization with:"
echo "https://mcp.simonkennedymp.com.au/authorize?client_id=$CLIENT_ID&redirect_uri=https://test.example.com/callback&response_type=code&scope=user"
