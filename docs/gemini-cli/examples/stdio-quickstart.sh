#!/usr/bin/env bash
set -euo pipefail

# Hansard MCP STDIO Quickstart Script
# Purpose: Automated local setup for Gemini CLI + Hansard MCP server
# Platform: macOS, Linux
# Usage: bash stdio-quickstart.sh

echo "=========================================="
echo "Hansard MCP STDIO Quickstart"
echo "=========================================="
echo ""

# Detect project directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

echo "Project directory: $PROJECT_ROOT"
echo ""

# Step 1: Check prerequisites
echo "[1/6] Checking prerequisites..."

# Check Gemini CLI
if ! command -v gemini &> /dev/null; then
    echo "ERROR: Gemini CLI not found. Install with: npm install -g @google/gemini-cli"
    exit 1
fi
echo "  ✓ Gemini CLI found: $(gemini --version)"

# Check Python
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo "ERROR: Python not found. Install Python 3.11+ from python.org"
    exit 1
fi
PYTHON_CMD=$(command -v python3 || command -v python)
PYTHON_VERSION=$($PYTHON_CMD --version | grep -oP '\d+\.\d+' || echo "0.0")
echo "  ✓ Python found: $($PYTHON_CMD --version)"

# Check FastMCP
if ! command -v fastmcp &> /dev/null; then
    echo "ERROR: FastMCP not found. Run 'uv sync' in project directory"
    exit 1
fi
FASTMCP_PATH=$(command -v fastmcp)
echo "  ✓ FastMCP found: $FASTMCP_PATH"

# Check uv
if ! command -v uv &> /dev/null; then
    echo "WARNING: uv package manager not found. Install from https://astral.sh/uv"
else
    echo "  ✓ uv found: $(uv --version)"
fi

echo ""

# Step 2: Initialize database (optional)
echo "[2/6] Database setup..."
if [ -f "$PROJECT_ROOT/data/hansard.db" ]; then
    echo "  ✓ Database already exists at: $PROJECT_ROOT/data/hansard.db"
    SPEECH_COUNT=$(sqlite3 "$PROJECT_ROOT/data/hansard.db" "SELECT COUNT(*) FROM speeches;" 2>/dev/null || echo "0")
    echo "  ✓ Database contains $SPEECH_COUNT speeches"
else
    echo "  ! Database not found. Creating directory..."
    mkdir -p "$PROJECT_ROOT/data"

    if [ -f "$PROJECT_ROOT/scripts/init_database.py" ]; then
        echo "  ! Initializing local database..."
        cd "$PROJECT_ROOT"
        $PYTHON_CMD scripts/init_database.py --local || echo "  WARNING: Database initialization failed"
    fi
fi

echo ""

# Step 3: Detect OS and config path
echo "[3/6] Detecting Gemini CLI configuration path..."

if [[ "$OSTYPE" == "darwin"* ]]; then
    CONFIG_DIR="$HOME/.config/gemini-cli"
    PLATFORM="macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    CONFIG_DIR="$HOME/.config/gemini-cli"
    PLATFORM="Linux"
else
    echo "ERROR: Unsupported platform: $OSTYPE"
    echo "This script supports macOS and Linux only. For Windows, use stdio-quickstart.ps1"
    exit 1
fi

CONFIG_FILE="$CONFIG_DIR/config.json"
echo "  ✓ Platform: $PLATFORM"
echo "  ✓ Config file: $CONFIG_FILE"

# Create config directory if needed
mkdir -p "$CONFIG_DIR"

echo ""

# Step 4: Backup existing config
echo "[4/6] Backing up existing configuration..."

if [ -f "$CONFIG_FILE" ]; then
    BACKUP_FILE="$CONFIG_DIR/config.json.backup.$(date +%Y%m%d-%H%M%S)"
    cp "$CONFIG_FILE" "$BACKUP_FILE"
    echo "  ✓ Backed up to: $BACKUP_FILE"
else
    echo "  ! No existing config found. Creating new config..."
fi

echo ""

# Step 5: Generate configuration
echo "[5/6] Generating Hansard MCP configuration..."

# Read existing config or create empty JSON
if [ -f "$CONFIG_FILE" ]; then
    EXISTING_CONFIG=$(cat "$CONFIG_FILE")
else
    EXISTING_CONFIG='{}'
fi

# Create Hansard server configuration
HANSARD_CONFIG=$(cat <<EOF
{
  "mcpServers": {
    "hansard": {
      "command": "$FASTMCP_PATH",
      "args": ["run", "src/server.py"],
      "env": {
        "DANGEROUSLY_OMIT_AUTH": "true",
        "DATABASE_URL": "sqlite:///$PROJECT_ROOT/data/hansard.db",
        "PYTHONPATH": "$PROJECT_ROOT",
        "LOG_LEVEL": "INFO"
      },
      "timeout": 30,
      "description": "Australian Hansard parliamentary speech search (local development)"
    }
  }
}
EOF
)

# Merge configurations (simple approach: add hansard to existing mcpServers)
if echo "$EXISTING_CONFIG" | grep -q '"mcpServers"'; then
    # Existing config has mcpServers, need to merge
    echo "  ! Existing mcpServers found. Manual merge required."
    echo ""
    echo "  Add this configuration to your config.json mcpServers section:"
    echo ""
    echo "    \"hansard\": {"
    echo "      \"command\": \"$FASTMCP_PATH\","
    echo "      \"args\": [\"run\", \"src/server.py\"],"
    echo "      \"env\": {"
    echo "        \"DANGEROUSLY_OMIT_AUTH\": \"true\","
    echo "        \"DATABASE_URL\": \"sqlite:///$PROJECT_ROOT/data/hansard.db\","
    echo "        \"PYTHONPATH\": \"$PROJECT_ROOT\","
    echo "        \"LOG_LEVEL\": \"INFO\""
    echo "      },"
    echo "      \"timeout\": 30,"
    echo "      \"description\": \"Australian Hansard parliamentary speech search (local development)\""
    echo "    }"
    echo ""

    # Save full config to temp file
    TEMP_CONFIG="/tmp/hansard-mcp-config.json"
    echo "$HANSARD_CONFIG" > "$TEMP_CONFIG"
    echo "  Full configuration saved to: $TEMP_CONFIG"
else
    # No existing mcpServers, safe to write
    echo "$HANSARD_CONFIG" > "$CONFIG_FILE"
    echo "  ✓ Configuration written to: $CONFIG_FILE"
fi

echo ""

# Step 6: Verify setup
echo "[6/6] Verifying setup..."

# Test server manually
echo "  ! Testing server startup..."
cd "$PROJECT_ROOT"
timeout 5s env DANGEROUSLY_OMIT_AUTH=true "$FASTMCP_PATH" dev src/server.py &> /tmp/hansard-test.log || true

if grep -q "error" /tmp/hansard-test.log || grep -q "Error" /tmp/hansard-test.log; then
    echo "  WARNING: Server test showed errors. Check /tmp/hansard-test.log"
else
    echo "  ✓ Server starts successfully"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Restart Gemini CLI: gemini restart"
echo "  2. Verify tools: Ask Gemini 'What Hansard tools are available?'"
echo "  3. Test search: Ask Gemini 'Search Hansard for speeches about climate change'"
echo ""
echo "Configuration file: $CONFIG_FILE"
echo "Project directory: $PROJECT_ROOT"
echo ""
echo "For troubleshooting, see: $PROJECT_ROOT/docs/gemini-cli/troubleshooting.md"
echo ""
