#!/bin/bash
#
# Setup GitHub Secrets for OAuth
# Run this script after creating your GitHub OAuth App
#
# Usage:
#   1. Get Client ID and Client Secret from: https://github.com/settings/developers
#   2. Run: ./scripts/setup-github-secrets.sh
#   3. Paste your credentials when prompted (Client Secret won't be displayed)
#

set -e

echo "============================================"
echo "GitHub OAuth Secrets Setup"
echo "Project: skai-fastmcp-cloudrun"
echo "============================================"
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ Error: GitHub CLI (gh) is not installed"
    echo "Install it: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Error: Not authenticated with GitHub CLI"
    echo "Run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI authenticated"
echo ""

# Prompt for Client ID
echo "Enter your GitHub OAuth Client ID (starts with Ov23li...):"
read -r CLIENT_ID

if [[ -z "$CLIENT_ID" ]]; then
    echo "❌ Error: Client ID cannot be empty"
    exit 1
fi

# Prompt for Client Secret (hidden input)
echo "Enter your GitHub OAuth Client Secret (will be hidden):"
read -rs CLIENT_SECRET

if [[ -z "$CLIENT_SECRET" ]]; then
    echo "❌ Error: Client Secret cannot be empty"
    exit 1
fi

echo ""
echo "Setting GitHub secrets..."
echo ""

# Set secrets (using FastMCP environment variable names)
echo "📝 Setting FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID..."
gh secret set FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID --body "$CLIENT_ID"

echo "📝 Setting FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET..."
gh secret set FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET --body "$CLIENT_SECRET"

echo "📝 Setting FASTMCP_SERVER_BASE_URL..."
gh secret set FASTMCP_SERVER_BASE_URL --body "https://mcp.simonkennedymp.com.au"

echo "📝 Setting FASTMCP_SERVER_AUTH..."
gh secret set FASTMCP_SERVER_AUTH --body "fastmcp.server.auth.providers.github.GitHubProvider"

echo "📝 Setting FASTMCP_SERVER_AUTH_GITHUB_REQUIRED_SCOPES..."
gh secret set FASTMCP_SERVER_AUTH_GITHUB_REQUIRED_SCOPES --body "user"

echo ""
echo "✅ All GitHub secrets set successfully!"
echo ""
echo "Verifying secrets..."
gh secret list

echo ""
echo "============================================"
echo "Next Steps:"
echo "============================================"
echo "1. Set up Google Cloud Secret Manager:"
echo "   ./scripts/setup-gcp-secrets.sh"
echo ""
echo "2. Verify GitHub OAuth App settings:"
echo "   Homepage: https://mcp.simonkennedymp.com.au"
echo "   Callback: https://mcp.simonkennedymp.com.au/auth/callback"
echo ""
echo "3. For local development, create .env file:"
echo "   cp .env.example .env"
echo "   # Then edit .env with your dev OAuth credentials"
echo ""
