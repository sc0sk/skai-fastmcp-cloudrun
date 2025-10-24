"""
Token verification module for FastMCP servers.

This module provides token verification functionality for OAuth resource servers,
enabling validation of JWT tokens, opaque tokens via introspection, and development
utilities for testing.

Public API:
    - JWTVerifier: JWT token verification (JWKS, static keys, HMAC)
    - IntrospectionTokenVerifier: OAuth 2.0 token introspection (RFC 7662)
    - StaticTokenVerifier: Static token mapping for development
    - RSAKeyPair: RSA key pair generation for testing
    - Configuration models: JWTVerifierConfig, IntrospectionVerifierConfig, StaticTokenVerifierConfig
    - load_auth_config_from_env: Load verifier from environment variables
"""

from src.auth.base import TokenValidationError, TokenVerifier, SystemAuthError
from src.auth.config import load_auth_config_from_env
from src.auth.introspection import IntrospectionTokenVerifier
from src.auth.jwt import JWTVerifier, RSAKeyPair, StaticTokenVerifier
from src.auth.fastmcp_adapter import TokenVerifierAuthProvider
from src.models.auth import (
    IntrospectionVerifierConfig,
    JWTVerifierConfig,
    StaticTokenVerifierConfig,
    TokenClaims,
    ValidationResult,
)

__all__ = [
    # Verifiers
    "JWTVerifier",
    "IntrospectionTokenVerifier",
    "StaticTokenVerifier",
    "TokenVerifier",
    # FastMCP Integration
    "TokenVerifierAuthProvider",
    # Utilities
    "RSAKeyPair",
    "load_auth_config_from_env",
    # Models
    "JWTVerifierConfig",
    "IntrospectionVerifierConfig",
    "StaticTokenVerifierConfig",
    "TokenClaims",
    "ValidationResult",
    # Exceptions
    "TokenValidationError",
    "SystemAuthError",
]
