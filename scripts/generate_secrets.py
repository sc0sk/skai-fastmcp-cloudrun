#!/usr/bin/env python3
"""
Generate secure random secrets for OAuth token storage.

Usage:
    python scripts/generate_secrets.py

Generates:
    - JWT_SIGNING_KEY: For signing MCP client JWT tokens
    - TOKEN_ENCRYPTION_KEY: For encrypting GitHub OAuth tokens

Both keys use cryptographically secure random data (256 bits).
"""

import secrets


def generate_key() -> str:
    """Generate a URL-safe base64-encoded random key (32 bytes = 256 bits)."""
    return secrets.token_urlsafe(32)


def main():
    print("Generating secure random secrets for OAuth token storage...")
    print()
    print("Add these to your .env file or Google Secret Manager:")
    print()
    print(f"JWT_SIGNING_KEY={generate_key()}")
    print(f"TOKEN_ENCRYPTION_KEY={generate_key()}")
    print()
    print("⚠️  IMPORTANT:")
    print("  - These keys MUST be different (never reuse the same key)")
    print("  - For production: Store in Google Secret Manager, not .env")
    print("  - For development: Add to .env.local (never commit)")
    print("  - Rotate keys annually for security best practices")


if __name__ == "__main__":
    main()
