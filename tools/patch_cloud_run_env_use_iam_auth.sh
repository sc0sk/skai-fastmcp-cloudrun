#!/usr/bin/env bash
set -euo pipefail

# Patch Cloud Run service env to enforce IAM DB auth and trigger a new revision.
#
# This sets USE_IAM_AUTH=true on the specified Cloud Run service.
# By default it updates the service in-place (no image rebuild) and
# triggers a new revision with 100% traffic to latest.
#
# Requirements:
# - gcloud CLI installed and authenticated
# - iam permissions to update the Cloud Run service
#
# Usage:
#   ./tools/patch_cloud_run_env_use_iam_auth.sh \
#       -s hansard-mcp-server \
#       -r us-central1 \
#       -p skai-fastmcp-cloudrun
#
# Flags/Env:
#   -s SERVICE  Cloud Run service name (default: hansard-mcp-server or $CLOUD_RUN_SERVICE)
#   -r REGION   Region (default: $GCP_REGION or us-central1)
#   -p PROJECT  GCP project (default: gcloud config project)
#
# Optional cleanup (commented): You can remove password env vars to avoid confusion.
#

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

echo "🔧 Updating Cloud Run service env..."
echo "   Service:   $SERVICE"
echo "   Region:    $REGION"
echo "   Project:   $PROJECT"

# Ensure the service exists
gcloud run services describe "$SERVICE" \
  --region "$REGION" \
  --project "$PROJECT" \
  --format="value(metadata.name)" >/dev/null

# Patch env to enforce IAM auth and trigger a new revision
gcloud run services update "$SERVICE" \
  --region "$REGION" \
  --project "$PROJECT" \
  --set-env-vars USE_IAM_AUTH=true

# Optional: uncomment to remove legacy password variables from the service
# gcloud run services update "$SERVICE" \
#   --region "$REGION" \
#   --project "$PROJECT" \
#   --remove-env-vars CLOUDSQL_USER,CLOUDSQL_PASSWORD,DATABASE_PASSWORD

echo "✅ Updated. Fetching current env..."
gcloud run services describe "$SERVICE" \
  --region "$REGION" \
  --project "$PROJECT" \
  --format="table(spec.template.spec.containers.env.name, spec.template.spec.containers.env.value)" \
  | grep -E "^(USE_IAM_AUTH|CLOUDSQL_USER|CLOUDSQL_PASSWORD|DATABASE_PASSWORD)\b" || true

echo "🚀 A new revision has been created with USE_IAM_AUTH=true."
echo "   Traffic is set to latest by default. If you use manual traffic splits,"
echo "   adjust with: gcloud run services update-traffic $SERVICE --region $REGION --project $PROJECT --to-latest"
