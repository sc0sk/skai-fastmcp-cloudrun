#!/usr/bin/env python3
"""
Test the authentication layer (without database dependency).

Tests:
1. Bearer token extraction
2. Token hashing
3. Rate limiting
4. Configuration validators
5. SecretStr masking
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


async def test_bearer_token_extraction():
    """Test bearer token extraction from Authorization header"""
    print("\n" + "="*60)
    print("TEST 1: Bearer Token Extraction")
    print("="*60)

    from auth.base import TokenVerifier

    class TestVerifier(TokenVerifier):
        async def verify(self, token):
            return None

    verifier = TestVerifier()

    # Test valid bearer token
    token = verifier.extract_bearer_token("Bearer abc123def456")
    assert token == "abc123def456", "Failed to extract valid token"
    print("✅ Valid bearer token extracted: 'Bearer abc123def456' → 'abc123def456'")

    # Test invalid format
    token = verifier.extract_bearer_token("InvalidFormat")
    assert token is None, "Should return None for invalid format"
    print("✅ Invalid format rejected: 'InvalidFormat' → None")

    # Test missing header
    token = verifier.extract_bearer_token(None)
    assert token is None, "Should return None for None"
    print("✅ Missing header handled: None → None")

    # Test case insensitive
    token = verifier.extract_bearer_token("bearer xyz789")
    assert token == "xyz789", "Should handle lowercase 'bearer'"
    print("✅ Case insensitive: 'bearer xyz789' → 'xyz789'")

    return True


async def test_token_hashing():
    """Test token hashing for logs"""
    print("\n" + "="*60)
    print("TEST 2: Token Hashing (SHA-256)")
    print("="*60)

    from auth.base import hash_token

    # Test basic hashing
    hash1 = hash_token("my_secret_token")
    hash2 = hash_token("my_secret_token")
    assert hash1 == hash2, "Same token should produce same hash"
    assert len(hash1) == 16, "Hash should be 16 chars"
    assert "my_secret_token" not in hash1, "Original token should not appear in hash"
    print(f"✅ Token hashing works:")
    print(f"   Input: 'my_secret_token'")
    print(f"   Hash:  '{hash1}' (16 chars)")

    # Test different tokens produce different hashes
    hash3 = hash_token("different_token")
    assert hash1 != hash3, "Different tokens should produce different hashes"
    print(f"✅ Different tokens produce different hashes:")
    print(f"   'my_secret_token' → '{hash1}'")
    print(f"   'different_token' → '{hash3}'")

    return True


async def test_rate_limiting():
    """Test rate limiter"""
    print("\n" + "="*60)
    print("TEST 3: Rate Limiting")
    print("="*60)

    from auth.rate_limiter import RateLimiter, RateLimitConfig
    from auth.base import hash_token

    # Create rate limiter with low limit for testing
    config = RateLimitConfig(max_attempts=3, window_seconds=60, enabled=True)
    limiter = RateLimiter(config)

    token = "test_token_123"
    token_hash = hash_token(token)

    # First 3 attempts should pass
    for i in range(3):
        is_limited = limiter.check_rate_limit(token_hash)
        assert not is_limited, f"Attempt {i+1} should not be rate limited"
    print(f"✅ First 3 attempts passed (limit: 3/60s)")

    # 4th attempt should be rate limited
    is_limited = limiter.check_rate_limit(token_hash)
    assert is_limited, "4th attempt should be rate limited"
    print(f"✅ 4th attempt rate limited (exceeded 3/60s)")

    # Different token should have independent limit
    different_hash = hash_token("different_token")
    is_limited = limiter.check_rate_limit(different_hash)
    assert not is_limited, "Different token should not be rate limited"
    print(f"✅ Different token has independent rate limit")

    return True


async def test_algorithm_confusion_prevention():
    """Test algorithm confusion attack prevention"""
    print("\n" + "="*60)
    print("TEST 4: Algorithm Confusion Prevention")
    print("="*60)

    from models.auth import JWTVerifierConfig
    from pydantic import ValidationError

    # Test: JWKS with HMAC should fail
    try:
        config = JWTVerifierConfig(
            jwks_uri="https://example.com/.well-known/jwks.json",
            issuer="https://example.com",
            audience="my-api",
            algorithm="HS256"  # HMAC not allowed with JWKS
        )
        print("❌ FAILED: JWKS with HS256 should be rejected")
        return False
    except ValidationError as e:
        print(f"✅ JWKS with HS256 rejected (as expected)")
        print(f"   Error: {str(e).split('n')[0][:80]}...")

    # Test: JWKS with RS256 should work
    config = JWTVerifierConfig(
        jwks_uri="https://example.com/.well-known/jwks.json",
        issuer="https://example.com",
        audience="my-api",
        algorithm="RS256"  # Asymmetric allowed with JWKS
    )
    print(f"✅ JWKS with RS256 accepted (asymmetric algorithm)")

    return True


async def test_secretstr_masking():
    """Test SecretStr prevents credential leakage"""
    print("\n" + "="*60)
    print("TEST 5: SecretStr Credential Masking")
    print("="*60)

    from pydantic import SecretStr
    from models.auth import JWTVerifierConfig

    # Create config with HMAC secret
    config = JWTVerifierConfig(
        public_key=SecretStr("my_super_secret_hmac_key_that_is_very_long_for_hs256_security"),
        issuer="https://example.com",
        audience="my-api",
        algorithm="HS256"
    )

    # Check that secret is masked in string representation
    config_str = str(config)
    assert "my_super_secret" not in config_str, "Secret should not appear in str()"
    print(f"✅ SecretStr masks credential in str() representation")
    print(f"   Secret is NOT visible in: {config_str[:100]}...")

    # Check that secret can be retrieved when needed
    secret_value = config.public_key.get_secret_value()
    assert "my_super_secret" in secret_value, "Secret should be retrievable"
    print(f"✅ Secret retrievable via .get_secret_value()")
    print(f"   Length: {len(secret_value)} chars")

    return True


async def test_https_enforcement():
    """Test HTTPS enforcement in production"""
    print("\n" + "="*60)
    print("TEST 6: HTTPS Enforcement")
    print("="*60)

    from models.auth import JWTVerifierConfig
    from pydantic import ValidationError

    # Set production environment
    os.environ["ENVIRONMENT"] = "production"

    try:
        # HTTP should fail in production (non-localhost)
        try:
            config = JWTVerifierConfig(
                jwks_uri="http://example.com/.well-known/jwks.json",
                issuer="https://example.com",
                audience="my-api"
            )
            print("❌ FAILED: HTTP should be rejected in production")
            return False
        except ValidationError:
            print("✅ HTTP URL rejected in production (non-localhost)")

        # HTTPS should work
        config = JWTVerifierConfig(
            jwks_uri="https://example.com/.well-known/jwks.json",
            issuer="https://example.com",
            audience="my-api"
        )
        print("✅ HTTPS URL accepted in production")

        # Localhost HTTP should work even in production
        config = JWTVerifierConfig(
            jwks_uri="http://localhost:8080/.well-known/jwks.json",
            issuer="https://example.com",
            audience="my-api"
        )
        print("✅ Localhost HTTP allowed in production (for testing)")

        return True
    finally:
        os.environ.pop("ENVIRONMENT", None)


async def main():
    """Run all authentication layer tests"""
    print("\n🔒 MCP Authentication Layer Testing")
    print("=" * 60)
    print("Testing security features without database dependency")
    print("=" * 60)

    results = []

    # Run all tests
    tests = [
        ("Bearer Token Extraction", test_bearer_token_extraction),
        ("Token Hashing (SHA-256)", test_token_hashing),
        ("Rate Limiting", test_rate_limiting),
        ("Algorithm Confusion Prevention", test_algorithm_confusion_prevention),
        ("SecretStr Masking", test_secretstr_masking),
        ("HTTPS Enforcement", test_https_enforcement),
    ]

    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.0f}%)")

    if passed == total:
        print("\n🎉 All authentication layer tests passed!")
        print("\n✅ Security Features Verified:")
        print("   - Bearer token extraction working")
        print("   - SHA-256 token hashing (no plaintext in logs)")
        print("   - Rate limiting active (prevents brute force)")
        print("   - Algorithm confusion attack BLOCKED")
        print("   - Credentials masked with SecretStr")
        print("   - HTTPS enforced in production")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
