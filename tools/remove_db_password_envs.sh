#!/usr/bin/env bash
set -euo pipefail

# Remove legacy DB password env vars from a Cloud Run service and roll a new revision.
#
# This prevents accidental fallback to password authentication when we intend to
# use IAM DB auth only.
#
# Usage:
#   ./tools/remove_db_password_envs.sh -s hansard-mcp-server -r us-central1 -p skai-fastmcp-cloudrun
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

echo "🧹 Removing DB password env vars from Cloud Run service..."
echo "   Service:   $SERVICE"
echo "   Region:    $REGION"
echo "   Project:   $PROJECT"

# Ensure the service exists
gcloud run services describe "$SERVICE" \
  --region "$REGION" \
  --project "$PROJECT" \
  --format="value(metadata.name)" >/dev/null

# Remove possible password env vars
# Includes both DATABASE_PASSWORD (preferred var) and legacy CLOUDSQL_PASSWORD
# and possible CLOUDSQL_USER for safety
if ! gcloud run services update "$SERVICE" \
  --region "$REGION" \
  --project "$PROJECT" \
  --remove-env-vars CLOUDSQL_USER,CLOUDSQL_PASSWORD,DATABASE_PASSWORD; then
  echo "No matching env vars to remove or update failed; continuing to show current env..." >&2
fi

echo "✅ Updated. Current relevant env vars:"
gcloud run services describe "$SERVICE" \
  --region "$REGION" \
  --project "$PROJECT" \
  --format="table(spec.template.spec.containers.env.name, spec.template.spec.containers.env.value)" \
  | grep -E "^(USE_IAM_AUTH|CLOUDSQL_USER|CLOUDSQL_PASSWORD|DATABASE_PASSWORD)\b" || true

echo "🚀 A new revision has been created without password env vars."