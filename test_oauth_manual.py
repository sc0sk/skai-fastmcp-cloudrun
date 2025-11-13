#!/usr/bin/env python3
"""
Manual OAuth flow test - prints URLs for browser-based testing.

This script:
1. Registers an OAuth client
2. Generates authorization URL
3. Prints instructions for manual testing
"""

import requests
import json
import secrets
import hashlib
import base64
from urllib.parse import urlencode

SERVER_URL = "https://hansard-mcp-server-666924716777.us-central1.run.app"


def base64url_encode(data):
    """Base64 URL encode without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


def generate_pkce():
    """Generate PKCE code verifier and challenge."""
    # Generate random code verifier
    code_verifier = base64url_encode(secrets.token_bytes(32))

    # Generate code challenge from verifier
    challenge_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64url_encode(challenge_bytes)

    return code_verifier, code_challenge


def main():
    print("=" * 80)
    print("OAuth Flow Manual Test")
    print("=" * 80)
    print()

    # Step 1: Register OAuth client
    print("Step 1: Registering OAuth client...")
    registration_data = {
        "redirect_uris": ["http://localhost:8080/callback"],
        "token_endpoint_auth_method": "none",
        "grant_types": ["authorization_code", "refresh_token"]
    }

    response = requests.post(
        f"{SERVER_URL}/register",
        json=registration_data,
        headers={"Content-Type": "application/json"}
    )

    if response.status_code not in [200, 201]:
        print(f"❌ Registration failed: {response.status_code}")
        print(response.text)
        return

    client_data = response.json()
    client_id = client_data['client_id']

    print(f"✅ Client registered successfully!")
    print(f"   Client ID: {client_id}")
    print()

    # Step 2: Generate PKCE challenge
    print("Step 2: Generating PKCE challenge...")
    code_verifier, code_challenge = generate_pkce()
    print(f"✅ PKCE generated")
    print(f"   Code Challenge: {code_challenge[:20]}...")
    print()

    # Step 3: Build authorization URL
    print("Step 3: Building authorization URL...")
    auth_params = {
        'client_id': client_id,
        'redirect_uri': 'http://localhost:8080/callback',
        'response_type': 'code',
        'scope': 'read write',
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
        'state': secrets.token_urlsafe(16)
    }

    auth_url = f"{SERVER_URL}/authorize?{urlencode(auth_params)}"

    print("✅ Authorization URL ready!")
    print()
    print("=" * 80)
    print("NEXT STEPS - Open this URL in your browser:")
    print("=" * 80)
    print()
    print(auth_url)
    print()
    print("=" * 80)
    print()
    print("Instructions:")
    print("1. Copy the URL above")
    print("2. Open it in your browser")
    print("3. Sign in with your GitHub account")
    print("4. Grant access to the application")
    print("5. You'll be redirected to http://localhost:8080/callback?code=...")
    print("6. The OAuth flow will complete!")
    print()
    print("Note: Since localhost:8080 isn't running, you'll see a connection error,")
    print("but the OAuth server will have processed the authorization successfully.")
    print()
    print(f"Registered Client ID: {client_id}")
    print(f"Code Verifier (save this): {code_verifier}")
    print()


if __name__ == "__main__":
    main()
