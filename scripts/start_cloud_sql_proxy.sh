#!/usr/bin/env bash
set -e

# Usage: ./scripts/start_cloud_sql_proxy.sh [--port PORT] [--instance INSTANCE]
# Supports both v1 (cloud_sql_proxy) and v2 (cloud-sql-proxy) binaries

PORT=5432
INSTANCE="skai-fastmcp-cloudrun:us-central1:hansard-db-v2"
BINARY=""
PIDFILE=".cloud_sql_proxy.pid"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --port)
      PORT="$2"
      shift 2
      ;;
    --instance)
      INSTANCE="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

# Find proxy binary (current dir first, then PATH)
if [[ -x "./cloud_sql_proxy" ]]; then
  BINARY="./cloud_sql_proxy"
elif command -v cloud_sql_proxy >/dev/null; then
  BINARY="$(command -v cloud_sql_proxy)"
elif [[ -x "./cloud-sql-proxy" ]]; then
  BINARY="./cloud-sql-proxy"
elif command -v cloud-sql-proxy >/dev/null; then
  BINARY="$(command -v cloud-sql-proxy)"
else
  echo "Cloud SQL Auth Proxy not found. Install from https://cloud.google.com/sql/docs/postgres/sql-proxy" >&2
  exit 1
fi

# Check if already running
if [[ -f "$PIDFILE" ]]; then
  PID=$(cat "$PIDFILE")
  if ps -p $PID > /dev/null 2>&1; then
    echo "Proxy already running (PID $PID) on port $PORT."
    exit 0
  else
    rm -f "$PIDFILE"
  fi
fi

# Check port availability
if lsof -i :$PORT >/dev/null 2>&1; then
  echo "Port $PORT is already in use. Trying alternative ports..."
  for ALT in 5433 5434 5435; do
    if ! lsof -i :$ALT >/dev/null 2>&1; then
      PORT=$ALT
      echo "Using port $PORT."
      break
    fi
  done
fi

# Write port to .env for app usage
if grep -q "^CLOUDSQL_PORT=" .env; then
  sed -i "s/^CLOUDSQL_PORT=.*/CLOUDSQL_PORT=$PORT/" .env
else
  echo "CLOUDSQL_PORT=$PORT" >> .env
fi

# Start proxy
if [[ "$BINARY" == *cloud_sql_proxy ]]; then
  "$BINARY" -instances="$INSTANCE"=tcp:$PORT &
else
  "$BINARY" "$INSTANCE" --port $PORT &
fi
PID=$!
echo $PID > "$PIDFILE"
echo "Proxy started (PID $PID) on port $PORT."
