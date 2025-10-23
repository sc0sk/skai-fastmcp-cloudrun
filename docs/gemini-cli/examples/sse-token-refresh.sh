#!/usr/bin/env bash
set -euo pipefail

# Hansard MCP SSE Token Refresh Script
# Purpose: Automate Google Cloud identity token generation and Gemini CLI config update
# Platform: macOS, Linux
# Usage: bash sse-token-refresh.sh [--service-account=SA_EMAIL]

echo "=========================================="
echo "Hansard MCP SSE Token Refresh"
echo "=========================================="
echo ""

# Parse command-line arguments
SERVICE_ACCOUNT=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --service-account=*)
            SERVICE_ACCOUNT="${1#*=}"
            shift
            ;;
        --service-account)
            SERVICE_ACCOUNT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--service-account=SERVICE_ACCOUNT_EMAIL]"
            exit 1
            ;;
    esac
done

# Detect platform and config path
if [[ "$OSTYPE" == "darwin"* ]]; then
    CONFIG_DIR="$HOME/.config/gemini-cli"
    PLATFORM="macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    CONFIG_DIR="$HOME/.config/gemini-cli"
    PLATFORM="Linux"
else
    echo "ERROR: Unsupported platform: $OSTYPE"
    echo "This script supports macOS and Linux only."
    exit 1
fi

CONFIG_FILE="$CONFIG_DIR/config.json"

echo "Platform: $PLATFORM"
echo "Config file: $CONFIG_FILE"
echo ""

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Gemini CLI config not found at: $CONFIG_FILE"
    echo "Please create the config file first. See: sse-setup.md"
    exit 1
fi

# Check if jq is installed (for JSON manipulation)
if ! command -v jq &> /dev/null; then
    echo "WARNING: jq not installed. Will use basic text replacement (less reliable)."
    echo "Install jq for better JSON handling: brew install jq (macOS) or apt install jq (Linux)"
    USE_JQ=false
else
    echo "✓ jq found: $(jq --version)"
    USE_JQ=true
fi

echo ""

# Step 1: Generate new identity token
echo "[1/4] Generating new identity token..."

if [ -n "$SERVICE_ACCOUNT" ]; then
    echo "  Using service account: $SERVICE_ACCOUNT"
    if ! gcloud auth print-identity-token --impersonate-service-account="$SERVICE_ACCOUNT" &> /dev/null; then
        echo "ERROR: Failed to generate token for service account: $SERVICE_ACCOUNT"
        echo "Verify service account exists and you have permission to impersonate it."
        exit 1
    fi
    NEW_TOKEN=$(gcloud auth print-identity-token --impersonate-service-account="$SERVICE_ACCOUNT")
else
    echo "  Using user credentials"
    if ! gcloud auth print-identity-token &> /dev/null; then
        echo "ERROR: Failed to generate identity token."
        echo "Verify you are authenticated: gcloud auth login"
        exit 1
    fi
    NEW_TOKEN=$(gcloud auth print-identity-token)
fi

if [ -z "$NEW_TOKEN" ]; then
    echo "ERROR: Generated token is empty"
    exit 1
fi

echo "  ✓ Token generated (length: ${#NEW_TOKEN} chars)"
echo "  ! Token preview: ${NEW_TOKEN:0:50}..."

echo ""

# Step 2: Backup existing config
echo "[2/4] Backing up config..."

BACKUP_FILE="$CONFIG_DIR/config.json.backup.$(date +%Y%m%d-%H%M%S)"
cp "$CONFIG_FILE" "$BACKUP_FILE"
echo "  ✓ Backup created: $BACKUP_FILE"

echo ""

# Step 3: Update config with new token
echo "[3/4] Updating config with new token..."

if [ "$USE_JQ" = true ]; then
    # Use jq for reliable JSON manipulation
    jq --arg token "$NEW_TOKEN" \
       '.mcpServers.hansard.headers.Authorization = "Bearer " + $token' \
       "$CONFIG_FILE" > "${CONFIG_FILE}.tmp"

    if [ $? -eq 0 ]; then
        mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
        echo "  ✓ Config updated using jq"
    else
        echo "ERROR: jq update failed. Config not modified."
        rm -f "${CONFIG_FILE}.tmp"
        exit 1
    fi
else
    # Fallback: basic text replacement (less reliable)
    # This looks for "Authorization": "Bearer OLD_TOKEN" and replaces with new token

    # Check if hansard.headers.Authorization exists
    if ! grep -q '"Authorization"' "$CONFIG_FILE"; then
        echo "ERROR: Authorization header not found in config"
        echo "Please ensure config has hansard.headers.Authorization field"
        exit 1
    fi

    # Replace Authorization header value
    sed -i.tmp "s|\"Authorization\": \"Bearer [^\"]*\"|\"Authorization\": \"Bearer $NEW_TOKEN\"|" "$CONFIG_FILE"

    if [ $? -eq 0 ]; then
        rm -f "${CONFIG_FILE}.tmp"
        echo "  ✓ Config updated using sed"
    else
        echo "ERROR: sed update failed. Config not modified."
        exit 1
    fi
fi

echo ""

# Step 4: Verify and restart Gemini CLI
echo "[4/4] Verifying update..."

# Verify token appears in config
if grep -q "${NEW_TOKEN:0:30}" "$CONFIG_FILE"; then
    echo "  ✓ Token verified in config"
else
    echo "WARNING: Could not verify token in config. Manual check recommended."
fi

# Check if Gemini CLI is running
if pgrep -f "gemini" &> /dev/null; then
    echo "  ! Gemini CLI is running. Restart required to apply changes."
    echo ""
    echo "  To restart Gemini CLI:"
    echo "    Option 1: gemini restart"
    echo "    Option 2: Kill and restart: pkill -f gemini && gemini"
else
    echo "  ! Gemini CLI not currently running. Start with: gemini"
fi

echo ""
echo "=========================================="
echo "Token Refresh Complete!"
echo "=========================================="
echo ""
echo "Token details:"
echo "  Generated at: $(date)"
echo "  Token length: ${#NEW_TOKEN} characters"
echo "  Expires in: ~60 minutes (for user tokens)"
if [ -n "$SERVICE_ACCOUNT" ]; then
    echo "  Service account: $SERVICE_ACCOUNT"
fi
echo ""
echo "Config file: $CONFIG_FILE"
echo "Backup file: $BACKUP_FILE"
echo ""

# Optional: Display token expiration time (if jwt is available)
if command -v jwt &> /dev/null; then
    echo "Token expiration:"
    jwt decode "$NEW_TOKEN" | grep -i exp || true
    echo ""
fi

# Optional: Test connection
echo "To test connection, run:"
echo "  curl -H \"Authorization: Bearer \$(gcloud auth print-identity-token)\" \\"
echo "    https://YOUR-SERVICE-URL.a.run.app/health"
echo ""

# Optional: Set up cron job reminder
if [ ! -f "$HOME/.hansard-token-cron" ]; then
    echo "TIP: Set up automated token refresh with cron:"
    echo "  crontab -e"
    echo "  # Add line: */30 * * * * $(realpath "$0")"
    echo ""
    echo "To suppress this reminder, run: touch ~/.hansard-token-cron"
    echo ""
fi

exit 0
