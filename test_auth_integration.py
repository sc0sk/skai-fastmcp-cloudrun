#!/usr/bin/env python3
"""
Integration test for FastMCP token authentication.

This test verifies that:
1. Valid tokens are accepted and verified
2. Invalid tokens are rejected
3. Tokens without required scopes are rejected
4. Token claims are properly extracted
"""
import asyncio
from src.auth import StaticTokenVerifier, TokenVerifierAuthProvider
from src.models.auth import StaticTokenVerifierConfig


async def test_auth_integration():
    """Test complete authentication flow"""
    print("=" * 70)
    print("FastMCP Token Authentication Integration Test")
    print("=" * 70)

    # Create verifier with test tokens
    verifier = StaticTokenVerifier(
        StaticTokenVerifierConfig(
            tokens={
                "admin-token-12345": {
                    "client_id": "admin@example.com",
                    "scopes": ["read:data", "write:data", "admin"]
                },
                "readonly-token-67890": {
                    "subject": "readonly-user",
                    "scopes": ["read:data"]
                },
                "guest-token-abcde": {
                    "client_id": "guest",
                    "scopes": []
                }
            },
            required_scopes=["read:data"]
        )
    )

    # Create FastMCP adapter
    auth_provider = TokenVerifierAuthProvider(verifier, required_scopes=["read:data"])

    # Test cases
    test_cases = [
        ("admin-token-12345", True, "admin@example.com"),
        ("readonly-token-67890", True, "readonly-user"),
        ("guest-token-abcde", False, None),  # Missing required scope
        ("invalid-token-xyz", False, None),  # Invalid token
    ]

    print("\nTest Results:")
    print("-" * 70)

    for token, should_succeed, expected_identity in test_cases:
        print(f"\n🔑 Token: {token}")

        # Call verify_token directly
        access_token = await auth_provider.verify_token(token)

        if should_succeed:
            if access_token:
                print(f"   ✅ PASS - Authenticated as: {access_token.client_id}")
                print(f"      Scopes: {access_token.scopes}")
                if access_token.expires_at:
                    print(f"      Expires: {access_token.expires_at}")
                assert access_token.client_id == expected_identity, f"Expected {expected_identity}, got {access_token.client_id}"
            else:
                print(f"   ❌ FAIL - Expected success but got None")
                raise AssertionError(f"Token {token} should have been accepted")
        else:
            if access_token is None:
                print(f"   ✅ PASS - Correctly rejected")
            else:
                print(f"   ❌ FAIL - Expected rejection but got: {access_token}")
                raise AssertionError(f"Token {token} should have been rejected")

    print("\n" + "=" * 70)
    print("All authentication tests passed! ✅")
    print("=" * 70)
    print("\n✨ Integration successful!")
    print("\n📋 Summary:")
    print("  • StaticTokenVerifier working correctly")
    print("  • TokenVerifierAuthProvider properly adapted to FastMCP")
    print("  • AccessToken construction fixed (token + client_id fields)")
    print("  • Scope validation working")
    print("  • Token claim extraction working")
    print("\n🎯 Ready for Claude Code CLI testing!")
    print("\nTo test with Claude Code CLI:")
    print("  1. Start server: PYTHONPATH=. fastmcp run test_auth_server.py --transport http --port 8000")
    print("  2. Use bearer token: admin-token-12345")
    print()


if __name__ == "__main__":
    asyncio.run(test_auth_integration())
