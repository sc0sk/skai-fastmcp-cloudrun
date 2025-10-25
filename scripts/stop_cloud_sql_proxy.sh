#!/usr/bin/env bash
set -e

PIDFILE=".cloud_sql_proxy.pid"

if [[ ! -f "$PIDFILE" ]]; then
  echo "No proxy PID file found. Proxy may not be running."
  exit 1
fi

PID=$(cat "$PIDFILE")
if ps -p $PID > /dev/null 2>&1; then
  kill $PID
  echo "Sent SIGTERM to proxy (PID $PID)."
  sleep 2
  if ps -p $PID > /dev/null 2>&1; then
    echo "Proxy did not exit. Sending SIGKILL."
    kill -9 $PID
  fi
  echo "Proxy stopped."
else
  echo "Proxy process $PID not found."
fi
rm -f "$PIDFILE"
