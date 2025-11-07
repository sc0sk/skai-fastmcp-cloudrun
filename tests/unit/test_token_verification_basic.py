"""
Basic JWT token verification tests.

Tests for JWT validation, expiration, audience, and scope checking.
"""

import os
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import SecretStr, ValidationError

from models.auth import JWTVerifierConfig, TokenClaims


def test_jwt_clock_skew_constraint():
    """Test that clock_skew is constrained to max 120 seconds"""
    # Valid: 120 seconds
    config = JWTVerifierConfig(
        jwks_uri="https://example.com/.well-known/jwks.json",
        issuer="https://example.com",
        audience="my-api",
        clock_skew=120,
    )
    assert config.clock_skew == 120

    # Invalid: 121 seconds (exceeds limit)
    with pytest.raises(ValidationError) as exc_info:
        JWTVerifierConfig(
            jwks_uri="https://example.com/.well-known/jwks.json",
            issuer="https://example.com",
            audience="my-api",
            clock_skew=121,
        )
    assert "120" in str(exc_info.value) or "less than or equal" in str(
        exc_info.value
    ).lower()


def test_https_enforcement_jwks_production():
    """Test that JWKS URI must use HTTPS in production"""
    # Set production environment
    os.environ["ENVIRONMENT"] = "production"

    try:
        # HTTP should fail in production
        with pytest.raises(ValidationError) as exc_info:
            JWTVerifierConfig(
                jwks_uri="http://example.com/.well-known/jwks.json",
                issuer="https://example.com",
                audience="my-api",
            )
        assert "https" in str(exc_info.value).lower()

        # HTTPS should work
        config = JWTVerifierConfig(
            jwks_uri="https://example.com/.well-known/jwks.json",
            issuer="https://example.com",
            audience="my-api",
        )
        assert config.jwks_uri.startswith("https://")
    finally:
        os.environ.pop("ENVIRONMENT", None)


def test_https_enforcement_jwks_localhost_allowed():
    """Test that localhost HTTP is allowed even in production for testing"""
    os.environ["ENVIRONMENT"] = "production"

    try:
        # localhost should work with HTTP
        config = JWTVerifierConfig(
            jwks_uri="http://localhost:8080/.well-known/jwks.json",
            issuer="https://example.com",
            audience="my-api",
        )
        assert config.jwks_uri.startswith("http://localhost")

        # 127.0.0.1 should also work
        config2 = JWTVerifierConfig(
            jwks_uri="http://127.0.0.1:8080/.well-known/jwks.json",
            issuer="https://example.com",
            audience="my-api",
        )
        assert config2.jwks_uri.startswith("http://127.0.0.1")
    finally:
        os.environ.pop("ENVIRONMENT", None)


def test_https_enforcement_jwks_development():
    """Test that HTTP is allowed in development environment"""
    os.environ["ENVIRONMENT"] = "development"

    try:
        # HTTP should work in development
        config = JWTVerifierConfig(
            jwks_uri="http://example.com/.well-known/jwks.json",
            issuer="https://example.com",
            audience="my-api",
        )
        assert config.jwks_uri.startswith("http://")
    finally:
        os.environ.pop("ENVIRONMENT", None)


def test_secretstr_for_public_key():
    """Test that public_key field uses SecretStr"""
    # Create config with HMAC key
    config = JWTVerifierConfig(
        public_key=SecretStr("my_very_strong_secret_key_that_is_long_enough_for_hs256_security"),
        issuer="https://example.com",
        audience="my-api",
        algorithm="HS256",
    )

    # Verify it's stored as SecretStr
    assert isinstance(config.public_key, SecretStr)

    # Verify string representation doesn't leak the secret
    config_str = str(config)
    assert "my_very_strong" not in config_str
    assert "SecretStr" in config_str or "**" in config_str


def test_token_claims_is_expired():
    """Test TokenClaims.is_expired() method"""
    # Expired token (expired 1 hour ago)
    claims = TokenClaims(
        subject="user123",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    assert claims.is_expired(clock_skew=0) is True

    # Valid token (expires in 1 hour)
    claims = TokenClaims(
        subject="user123",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    assert claims.is_expired(clock_skew=0) is False

    # Token with no expiration
    claims = TokenClaims(subject="user123", expires_at=None)
    assert claims.is_expired(clock_skew=0) is False

    # Token expired 30 seconds ago, but within 60s clock skew
    claims = TokenClaims(
        subject="user123",
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=30),
    )
    assert claims.is_expired(clock_skew=60) is False
    assert claims.is_expired(clock_skew=0) is True


def test_token_claims_is_not_yet_valid():
    """Test TokenClaims.is_not_yet_valid() method"""
    # Not yet valid (valid in 1 hour)
    claims = TokenClaims(
        subject="user123",
        not_before=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    assert claims.is_not_yet_valid(clock_skew=0) is True

    # Already valid (nbf was 1 hour ago)
    claims = TokenClaims(
        subject="user123",
        not_before=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    assert claims.is_not_yet_valid(clock_skew=0) is False

    # Token with no nbf claim
    claims = TokenClaims(subject="user123", not_before=None)
    assert claims.is_not_yet_valid(clock_skew=0) is False

    # Token valid in 30 seconds, but within 60s clock skew
    claims = TokenClaims(
        subject="user123",
        not_before=datetime.now(timezone.utc) + timedelta(seconds=30),
    )
    assert claims.is_not_yet_valid(clock_skew=60) is False
    assert claims.is_not_yet_valid(clock_skew=0) is True
