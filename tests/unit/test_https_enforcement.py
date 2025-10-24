"""
Tests for HTTPS enforcement in production.

Verifies external endpoints require HTTPS except localhost in development.
"""

import os

import pytest
from pydantic import ValidationError

models.auth import IntrospectionVerifierConfig, JWTVerifierConfig


def test_introspection_https_enforcement_production():
    """Test that introspection URL must use HTTPS in production"""
    os.environ["ENVIRONMENT"] = "production"

    try:
        # HTTP should fail in production (non-localhost)
        with pytest.raises(ValidationError) as exc_info:
            IntrospectionVerifierConfig(
                introspection_url="http://example.com/oauth/introspect",
                client_id="my-client",
                client_secret="my-secret",
            )
        assert "https" in str(exc_info.value).lower()

        # HTTPS should work
        config = IntrospectionVerifierConfig(
            introspection_url="https://example.com/oauth/introspect",
            client_id="my-client",
            client_secret="my-secret",
        )
        assert config.introspection_url.startswith("https://")
    finally:
        os.environ.pop("ENVIRONMENT", None)


def test_introspection_https_localhost_allowed():
    """Test that localhost HTTP is allowed for introspection even in production"""
    os.environ["ENVIRONMENT"] = "production"

    try:
        # localhost should work with HTTP
        config = IntrospectionVerifierConfig(
            introspection_url="http://localhost:8080/oauth/introspect",
            client_id="my-client",
            client_secret="my-secret",
        )
        assert config.introspection_url.startswith("http://localhost")

        # 127.0.0.1 should also work
        config2 = IntrospectionVerifierConfig(
            introspection_url="http://127.0.0.1:8080/oauth/introspect",
            client_id="my-client",
            client_secret="my-secret",
        )
        assert config2.introspection_url.startswith("http://127.0.0.1")
    finally:
        os.environ.pop("ENVIRONMENT", None)


def test_introspection_https_development():
    """Test that HTTP is allowed in development for introspection"""
    os.environ["ENVIRONMENT"] = "development"

    try:
        # HTTP should work in development
        config = IntrospectionVerifierConfig(
            introspection_url="http://example.com/oauth/introspect",
            client_id="my-client",
            client_secret="my-secret",
        )
        assert config.introspection_url.startswith("http://")
    finally:
        os.environ.pop("ENVIRONMENT", None)
