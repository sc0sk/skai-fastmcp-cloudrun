"""
Tests for algorithm confusion attack prevention.

Verifies JWT algorithm whitelisting and HMAC key strength validation.
"""

import pytest
from pydantic import ValidationError

from src.models.auth import JWTVerifierConfig


def test_jwks_rejects_hmac_algorithm():
    """Test that JWKS configuration rejects HMAC algorithms (HS256/HS384/HS512)"""
    with pytest.raises(ValidationError) as exc_info:
        JWTVerifierConfig(
            jwks_uri="https://example.com/.well-known/jwks.json",
            issuer="https://example.com",
            audience="my-api",
            algorithm="HS256",  # HMAC not allowed with JWKS
        )
    assert "asymmetric" in str(exc_info.value).lower() or "hmac" in str(
        exc_info.value
    ).lower()


def test_hmac_rejects_jwks_uri():
    """Test that HMAC configuration rejects jwks_uri (mutual exclusion)"""
    with pytest.raises(ValidationError) as exc_info:
        JWTVerifierConfig(
            jwks_uri="https://example.com/.well-known/jwks.json",
            public_key="my_secret_key_that_is_at_least_32_bytes_long_for_hs256",
            issuer="https://example.com",
            audience="my-api",
            algorithm="HS256",
        )
    assert "cannot specify both" in str(exc_info.value).lower()


def test_asymmetric_algorithms_allowed_with_jwks():
    """Test that RS256/RS384/RS512/ES256/ES384/ES512 are allowed with JWKS"""
    safe_algorithms = ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]

    for algo in safe_algorithms:
        config = JWTVerifierConfig(
            jwks_uri="https://example.com/.well-known/jwks.json",
            issuer="https://example.com",
            audience="my-api",
            algorithm=algo,
        )
        assert config.algorithm == algo


def test_weak_hmac_key_rejected():
    """Test that weak HMAC keys (repeated chars, test strings) are rejected"""
    weak_keys = [
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",  # Repeated 'a'
        "test" * 10,  # Repeated "test"
        "password" * 5,  # Repeated "password"
        "1234567890" * 4,  # Repeated digits
    ]

    for weak_key in weak_keys:
        with pytest.raises(ValidationError) as exc_info:
            JWTVerifierConfig(
                public_key=weak_key,
                issuer="https://example.com",
                audience="my-api",
                algorithm="HS256",
            )
        # Should fail due to weak pattern detection
        assert "weak" in str(exc_info.value).lower() or "pattern" in str(
            exc_info.value
        ).lower()


def test_short_hmac_key_rejected():
    """Test that HMAC keys shorter than algorithm requirements are rejected"""
    # HS256 requires >=32 bytes
    with pytest.raises(ValidationError) as exc_info:
        JWTVerifierConfig(
            public_key="short_key_only_20_chars",  # Only 22 bytes
            issuer="https://example.com",
            audience="my-api",
            algorithm="HS256",
        )
    assert "32" in str(exc_info.value) or "length" in str(exc_info.value).lower()

    # HS384 requires >=48 bytes
    with pytest.raises(ValidationError) as exc_info:
        JWTVerifierConfig(
            public_key="a" * 40,  # Only 40 bytes, needs 48
            issuer="https://example.com",
            audience="my-api",
            algorithm="HS384",
        )
    assert "48" in str(exc_info.value) or "length" in str(exc_info.value).lower()

    # HS512 requires >=64 bytes
    with pytest.raises(ValidationError) as exc_info:
        JWTVerifierConfig(
            public_key="a" * 50,  # Only 50 bytes, needs 64
            issuer="https://example.com",
            audience="my-api",
            algorithm="HS512",
        )
    assert "64" in str(exc_info.value) or "length" in str(exc_info.value).lower()
