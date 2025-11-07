#!/usr/bin/env python3
"""Test MCP tools on Cloud Run to verify IAM authentication."""

import json
import subprocess
import requests

# Get ID token for Cloud Run authentication
result = subprocess.run(
    ["gcloud", "auth", "print-identity-token"],
    capture_output=True,
    text=True,
    check=True
)
token = result.stdout.strip()

# Cloud Run service URL
url = "https://hansard-mcp-server-666924716777.us-central1.run.app/mcp/v1/tools/call"

# Test search tool
payload = {
    "name": "search_hansard_speeches",
    "arguments": {
        "query": "housing",
        "limit": 2
    }
}

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

print("Testing MCP search tool on Cloud Run...")
print(f"URL: {url}")
print(f"Payload: {json.dumps(payload, indent=2)}")
print()

response = requests.post(url, headers=headers, json=payload, timeout=30)

print(f"Status Code: {response.status_code}")
print(f"Response Headers: {dict(response.headers)}")
print()
print("Response Body:")
print(json.dumps(response.json() if response.headers.get('content-type') == 'application/json' else response.text, indent=2))
