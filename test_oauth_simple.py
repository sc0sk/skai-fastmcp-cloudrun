#!/usr/bin/env python3
"""
Simplified OAuth flow - uses persistent browser context with existing GitHub session.
"""

import asyncio
import secrets
import hashlib
import base64
import json
from urllib.parse import urlparse, parse_qs
from playwright.async_api import async_playwright
import httpx

# OAuth client credentials
CLIENT_ID = "648d0c96-e200-49dd-b558-afe4dc042cfe"
CLIENT_SECRET = "fb4bf1b3c332dce097d984389d5c1f5f1858a19a124b0339efa8443caf3c2a67"
REDIRECT_URI = "http://localhost:8080/callback"
BASE_URL = "https://mcp.simonkennedymp.com.au"

# Generate PKCE challenge
code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode('utf-8')).digest()
).decode('utf-8').rstrip('=')

print(f"✅ Code Verifier: {code_verifier}")
print(f"✅ Code Challenge: {code_challenge}")

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

print(f"\n🔗 Authorization URL:\n{auth_url}\n")

async def get_oauth_token():
    """Complete OAuth flow using browser with existing GitHub session."""

    authorization_code = None

    async with async_playwright() as p:
        # Use persistent context to preserve GitHub login
        # This uses a temporary browser profile
        browser = await p.chromium.launch(
            headless=False,  # Keep visible so you can see what's happening
            slow_mo=500      # Slow down actions for visibility
        )
        context = await browser.new_context()
        page = await context.new_page()

        # Monitor all navigation to catch the redirect
        authorization_code_captured = asyncio.Event()

        async def handle_request(request):
            nonlocal authorization_code
            url = request.url
            if url.startswith(REDIRECT_URI):
                print(f"🎯 Caught redirect: {url}")
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                if 'code' in params:
                    authorization_code = params['code'][0]
                    print(f"✅ Got authorization code: {authorization_code}")
                    authorization_code_captured.set()

        page.on('request', handle_request)

        # Navigate to authorization URL
        print("📡 Navigating to authorization endpoint...")
        await page.goto(auth_url)
        await page.wait_for_load_state('networkidle')
        print("✅ Page loaded")

        # Take screenshot
        await page.screenshot(path="/tmp/oauth_page1.png")
        print("📸 Screenshot 1: /tmp/oauth_page1.png")

        # Check what page we're on
        current_url = page.url
        print(f"📍 Current URL: {current_url}")

        # If on consent page, click "Allow Access"
        if 'consent' in current_url or BASE_URL in current_url:
            print("✅ On consent page")
            try:
                # Wait for and click "Allow Access" button
                allow_button = page.locator('button:has-text("Allow Access")')
                await allow_button.wait_for(state='visible', timeout=5000)
                print("✅ Found 'Allow Access' button")
                await allow_button.click()
                print("🖱️  Clicked 'Allow Access'")

                # Wait for next page
                await page.wait_for_load_state('networkidle', timeout=15000)
                await page.screenshot(path="/tmp/oauth_page2.png")
                print("📸 Screenshot 2: /tmp/oauth_page2.png")

                current_url = page.url
                print(f"📍 New URL: {current_url}")

            except Exception as e:
                print(f"⚠️  Error with consent page: {e}")

        # If on GitHub login, you need to log in manually
        if 'github.com/login' in current_url:
            print("\n" + "="*60)
            print("🔐 MANUAL ACTION REQUIRED")
            print("="*60)
            print("The browser window is waiting for you to:")
            print("1. Log in to GitHub")
            print("2. Authorize the application")
            print("3. The script will automatically detect the redirect")
            print("\nWaiting for you to complete the OAuth flow...")
            print("="*60 + "\n")

            # Wait for authorization code (up to 120 seconds)
            try:
                await asyncio.wait_for(authorization_code_captured.wait(), timeout=120)
            except asyncio.TimeoutError:
                print("⏱️  Timeout waiting for authorization")

        # Also check final URL
        if not authorization_code:
            final_url = page.url
            if 'code=' in final_url:
                parsed = urlparse(final_url)
                params = parse_qs(parsed.query)
                if 'code' in params:
                    authorization_code = params['code'][0]
                    print(f"✅ Extracted code from final URL: {authorization_code}")

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
            },
            timeout=30.0
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

async def test_mcp_endpoint(access_token):
    """Test the MCP endpoint with the access token."""
    print("\n🧪 Testing MCP endpoint with access token...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test /mcp endpoint
        response = await client.get(
            f"{BASE_URL}/mcp",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ MCP endpoint authentication successful!")
            data = response.json()
            print(f"Response preview: {json.dumps(data, indent=2)[:500]}...")
        else:
            print(f"❌ MCP endpoint returned error")
            print(f"Response: {response.text[:500]}")

        return response.status_code == 200

if __name__ == "__main__":
    print("🚀 Starting OAuth flow automation\n")

    token_data = asyncio.run(get_oauth_token())

    if token_data and 'access_token' in token_data:
        access_token = token_data['access_token']
        print(f"\n🎉 SUCCESS! Access token obtained")
        print(f"Token: {access_token[:50]}...")

        # Save token to file for later use
        with open('/tmp/mcp_oauth_token.json', 'w') as f:
            json.dump(token_data, f, indent=2)
        print("\n💾 Token saved to: /tmp/mcp_oauth_token.json")

        # Test the token
        success = asyncio.run(test_mcp_endpoint(access_token))

        if success:
            print("\n✅ All tests passed! OAuth flow working correctly.")
        else:
            print("\n⚠️  OAuth flow completed but endpoint test failed.")
    else:
        print("\n❌ Failed to obtain access token")
