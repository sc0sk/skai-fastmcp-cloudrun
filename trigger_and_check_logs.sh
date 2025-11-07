#!/bin/bash
set -e

echo "=== Triggering Cloud Run service to generate logs ==="
TOKEN=$(gcloud auth print-identity-token)
curl -s "https://hansard-mcp-server-666924716777.us-central1.run.app/debug/iam-user" \
  -H "Authorization: Bearer $TOKEN" > /tmp/debug_response.json

echo "Debug endpoint response:"
cat /tmp/debug_response.json | python3 -m json.tool
echo ""

echo "=== Waiting 10 seconds for logs to propagate ==="
sleep 10

echo "=== Fetching recent Cloud Run logs ==="
gcloud logging read \
  'resource.type=cloud_run_revision AND resource.labels.service_name=hansard-mcp-server AND timestamp>="2025-11-06T04:35:00Z"' \
  --limit 100 \
  --format=json > /tmp/cloudrun_logs.json

echo "=== Filtering for CloudSQLEngine and IAM-related logs ==="
cat /tmp/cloudrun_logs.json | jq -r '.[] |
  select(
    (.textPayload // "" | test("CloudSQL|detected_iam|IAM|iam_valid"; "i")) or
    (.jsonPayload.detected_iam_user // false) or
    (.jsonPayload.detection_method // false)
  ) |
  "\(.timestamp) [\(.severity)] \(.textPayload // (.jsonPayload | tostring))"' | head -30

echo ""
echo "=== Log analysis complete ==="
