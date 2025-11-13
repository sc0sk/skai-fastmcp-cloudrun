#!/usr/bin/env python3
"""
Automated OAuth flow testing using Playwright.
Completes the GitHub OAuth consent flow and retrieves an access token.
Uses GitHub CLI token for automated authentication.
"""

import asyncio
import secrets
import hashlib
import base64
import json
import subprocess
from urllib.parse import urlparse, parse_qs
from playwright.async_api import async_playwright
import httpx

# Get GitHub token from gh CLI
def get_github_token():
    """Get GitHub token from gh CLI."""
    result = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    return None

GITHUB_TOKEN = get_github_token()
if not GITHUB_TOKEN:
    print("❌ GitHub token not found. Run: gh auth login")
    exit(1)

print(f"✅ GitHub token loaded: {GITHUB_TOKEN[:20]}...")

# OAuth client credentials (from registration)
CLIENT_ID = "648d0c96-e200-49dd-b558-afe4dc042cfe"
CLIENT_SECRET = "fb4bf1b3c332dce097d984389d5c1f5f1858a19a124b0339efa8443caf3c2a67"
REDIRECT_URI = "http://localhost:8080/callback"
BASE_URL = "https://mcp.simonkennedymp.com.au"

# Generate PKCE challenge
code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode('utf-8')).digest()
).decode('utf-8').rstrip('=')

print(f"Code Verifier: {code_verifier}")
print(f"Code Challenge: {code_challenge}")

# Build authorization URL
auth_url = (
    f"{BASE_URL}/authorize"
    f"?response_type=code"
    f"&client_id={CLIENT_ID}"
    f"&redirect_uri={REDIRECT_URI}"
    f"&scope=user"
    f"&code_challenge={code_challenge}"
    f"&code_challenge_method=S256"
    f"&state=test123"
)

print(f"\n🔗 Authorization URL: {auth_url}\n")

async def get_oauth_token():
    """Complete OAuth flow using headless browser."""

    async with async_playwright() as p:
        # Launch browser (headless=False for debugging)
        browser = await p.chromium.launch(headless=False)

        # Create context with GitHub authentication
        # Load GitHub cookies if available
        context = await browser.new_context(
            storage_state=None,  # We'll authenticate programmatically
        )
        page = await context.new_page()

        # Set GitHub authentication token as cookie/storage
        # This will help bypass the login page
        await context.add_cookies([
            {
                'name': 'user_session',
                'value': GITHUB_TOKEN,
                'domain': '.github.com',
                'path': '/',
                'httpOnly': True,
                'secure': True,
                'sameSite': 'Lax'
            }
        ])

        # Navigate to authorization URL
        print("📡 Navigating to authorization endpoint...")
        await page.goto(auth_url)

        # Wait for consent page to load
        await page.wait_for_load_state('networkidle')
        print("✅ Consent page loaded")

        # Take screenshot for debugging
        await page.screenshot(path="/tmp/consent_page.png")
        print("📸 Screenshot saved to /tmp/consent_page.png")

        # Try to find and click the "Approve" or "Allow" button
        # Common button selectors for consent pages
        approve_selectors = [
            'button:has-text("Approve")',
            'button:has-text("Allow")',
            'button:has-text("Authorize")',
            'button:has-text("Grant Access")',
            'input[type="submit"][value*="Approve"]',
            'input[type="submit"][value*="Allow"]',
            'form button[type="submit"]',
        ]

        authorization_code = None

        # Set up listener for redirect
        async def handle_response(response):
            nonlocal authorization_code
            url = response.url
            if url.startswith(REDIRECT_URI):
                print(f"🎯 Caught redirect: {url}")
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                if 'code' in params:
                    authorization_code = params['code'][0]
                    print(f"✅ Got authorization code: {authorization_code}")

        page.on('response', handle_response)

        # Try to click "Allow Access" button
        print("🔍 Looking for 'Allow Access' button...")
        try:
            allow_button = page.locator('button:has-text("Allow Access")').first
            if await allow_button.is_visible(timeout=5000):
                print("✅ Found 'Allow Access' button")
                await allow_button.click()
                print("🖱️  Clicked 'Allow Access' button")

                # Wait for GitHub login or redirect
                await page.wait_for_load_state('networkidle', timeout=10000)

                # Check if we're on GitHub login page
                if 'github.com/login' in page.url:
                    print("🔐 Redirected to GitHub login - authentication required")
                    print("⚠️  Cannot proceed without GitHub credentials")
                    print(f"Current URL: {page.url}")

                    # Keep browser open for manual login
                    print("\n📋 You can manually:")
                    print("1. Log in to GitHub in the browser window")
                    print("2. Approve the OAuth app")
                    print("3. Watch the terminal for the authorization code")
                    print("\nWaiting 60 seconds for manual authentication...")

                    await asyncio.sleep(60)
            else:
                print("❌ 'Allow Access' button not visible")
        except Exception as e:
            print(f"❌ Error clicking button: {e}")

        # Wait for redirect or timeout
        print("⏳ Waiting for redirect...")
        try:
            await page.wait_for_url(f"{REDIRECT_URI}*", timeout=10000)
            print("✅ Redirect complete")
        except Exception as e:
            print(f"⚠️  Timeout waiting for redirect: {e}")
            # Check if we already captured the code from response listener
            if not authorization_code:
                # Try to extract from current URL
                current_url = page.url
                if 'code=' in current_url:
                    parsed = urlparse(current_url)
                    params = parse_qs(parsed.query)
                    authorization_code = params['code'][0]

        await browser.close()

        if not authorization_code:
            print("❌ Failed to get authorization code")
            return None

        print(f"\n✅ Authorization code: {authorization_code}\n")

        # Exchange authorization code for access token
        print("🔄 Exchanging code for access token...")
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                f"{BASE_URL}/token",
                data={
                    "grant_type": "authorization_code",
                    "code": authorization_code,
                    "redirect_uri": REDIRECT_URI,
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "code_verifier": code_verifier,
                }
            )

            if token_response.status_code == 200:
                token_data = token_response.json()
                print("✅ Got access token!")
                print(json.dumps(token_data, indent=2))
                return token_data
            else:
                print(f"❌ Token exchange failed: {token_response.status_code}")
                print(token_response.text)
                return None

if __name__ == "__main__":
    token_data = asyncio.run(get_oauth_token())

    if token_data and 'access_token' in token_data:
        access_token = token_data['access_token']
        print(f"\n🎉 Success! Access token: {access_token}\n")

        # Test the token against the MCP endpoint
        print("🧪 Testing token against MCP endpoint...")
        async def test_token():
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{BASE_URL}/mcp",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                print(f"Status: {response.status_code}")
                print(f"Response: {response.text[:500]}")

        asyncio.run(test_token())
