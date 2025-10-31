#!/usr/bin/env bash
set -euo pipefail

# Check Cloud Run service account and required IAM roles for Cloud SQL IAM DB auth.
#
# This script:
#  - Prints the service account used by the Cloud Run service
#  - Checks for project-level roles commonly required:
#      roles/cloudsql.client
#      roles/cloudsql.instanceUser   (often needed for IAM DB auth token generation)
#  - Shows a quick summary
#
# Note: DB-level privileges (CONNECT/USAGE/SELECT/INSERT/etc.) must still be
# granted inside PostgreSQL to the IAM DB principal.
#
# Usage:
#   ./tools/check_cloud_run_sa_iam.sh -s hansard-mcp-server -r us-central1 -p skai-fastmcp-cloudrun
#
# Flags/Env:
#   -s SERVICE  Cloud Run service name (default: hansard-mcp-server or $CLOUD_RUN_SERVICE)
#   -r REGION   Region (default: $GCP_REGION or us-central1)
#   -p PROJECT  GCP project (default: gcloud config project)

SERVICE="${CLOUD_RUN_SERVICE:-hansard-mcp-server}"
REGION="${GCP_REGION:-us-central1}"
PROJECT="$(gcloud config get-value project 2>/dev/null || true)"

while getopts ":s:r:p:" opt; do
  case ${opt} in
    s) SERVICE="$OPTARG" ;;
    r) REGION="$OPTARG" ;;
    p) PROJECT="$OPTARG" ;;
    :) echo "Error: Option -$OPTARG requires an argument." >&2; exit 2 ;;
    \?) echo "Usage: $0 [-s service] [-r region] [-p project]" >&2; exit 2 ;;
  esac
done

if [[ -z "$SERVICE" || -z "$REGION" ]]; then
  echo "Error: SERVICE and REGION are required." >&2
  exit 2
fi

if [[ -z "$PROJECT" || "$PROJECT" == "(unset)" ]]; then
  echo "Info: PROJECT not provided; using active gcloud config project."
  PROJECT="$(gcloud config get-value project)"
fi

echo "🔎 Inspecting Cloud Run service account and IAM roles..."
echo "   Service:   $SERVICE"
echo "   Region:    $REGION"
echo "   Project:   $PROJECT"

SA_EMAIL=$(gcloud run services describe "$SERVICE" \
  --region "$REGION" \
  --project "$PROJECT" \
  --format="value(spec.template.spec.serviceAccountName)")

if [[ -z "$SA_EMAIL" ]]; then
  echo "❌ Could not determine service account for the Cloud Run service." >&2
  exit 1
fi

echo "👤 Service Account: $SA_EMAIL"

echo "📋 Checking project IAM bindings for required roles..."
# Fetch bindings once
POLICY_JSON=$(gcloud projects get-iam-policy "$PROJECT" --format=json)

check_role() {
  local role="$1"
  echo "$POLICY_JSON" | jq -r \
    --arg ROLE "$role" \
    --arg SA "$SA_EMAIL" \
    '.bindings[] | select(.role==$ROLE) | .members[]' \
    | grep -E "(serviceAccount:$SA_EMAIL|principal://iam.googleapis.com/$SA_EMAIL)" >/dev/null 2>&1
}

HAS_CLIENT="no"
HAS_INSTANCE_USER="no"

if check_role "roles/cloudsql.client"; then HAS_CLIENT="yes"; fi
if check_role "roles/cloudsql.instanceUser"; then HAS_INSTANCE_USER="yes"; fi

printf "  - roles/cloudsql.client:       %s\n" "$HAS_CLIENT"
printf "  - roles/cloudsql.instanceUser: %s\n" "$HAS_INSTANCE_USER"

if [[ "$HAS_CLIENT" != "yes" ]]; then
  echo "⚠️  Missing roles/cloudsql.client. Grant with:" 
  echo "   gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:$SA_EMAIL --role=roles/cloudsql.client"
fi
if [[ "$HAS_INSTANCE_USER" != "yes" ]]; then
  echo "⚠️  Missing roles/cloudsql.instanceUser (needed for IAM DB auth). Grant with:"
  echo "   gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:$SA_EMAIL --role=roles/cloudsql.instanceUser"
fi

echo "✅ Check complete. Remember: the database (PostgreSQL) must grant privileges to this IAM user inside the DB as well."
