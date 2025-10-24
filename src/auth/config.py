"""
Environment-based configuration loader for token verification.

This module provides utilities to load authentication configuration from
environment variables, enabling deployment flexibility across different environments.
"""

import logging
import os

from src.auth.introspection import IntrospectionTokenVerifier
from src.auth.jwt import JWTVerifier, StaticTokenVerifier
from src.models.auth import (
    IntrospectionVerifierConfig,
    JWTVerifierConfig,
    StaticTokenVerifierConfig,
)

logger = logging.getLogger(__name__)


def load_auth_config_from_env():
    """
    Load authentication configuration from environment variables.

    Automatically detects and configures the appropriate verifier based on
    FASTMCP_SERVER_AUTH environment variable.

    Supported values:
    - "jwt": JWT token verification (JWKS or static keys)
    - "introspection": OAuth 2.0 Token Introspection
    - "static": Static token mapping (development only)

    Returns:
        Configured TokenVerifier instance

    Raises:
        ValueError: If configuration is invalid or missing required variables
    """
    auth_type = os.getenv("FASTMCP_SERVER_AUTH", "").lower()

    if not auth_type:
        logger.info("No FASTMCP_SERVER_AUTH configured - authentication disabled")
        return None

    if auth_type == "jwt":
        logger.info("Loading JWT verifier configuration from environment")
        config = JWTVerifierConfig.from_env()
        logger.info(
            f"JWT verifier configured: issuer={config.issuer}, "
            f"algorithm={config.algorithm}, "
            f"key_source={'JWKS' if config.jwks_uri else 'static'}"
        )
        return JWTVerifier(config)

    elif auth_type == "introspection":
        logger.info("Loading introspection verifier configuration from environment")
        config = IntrospectionVerifierConfig.from_env()
        logger.info(
            f"Introspection verifier configured: endpoint={config.introspection_url}"
        )
        return IntrospectionTokenVerifier(config)

    elif auth_type == "static":
        logger.warning(
            "Static token verification requested - FOR DEVELOPMENT ONLY"
        )
        # Static tokens must be configured programmatically, not via env
        raise ValueError(
            "Static token verification must be configured programmatically "
            "(not via environment variables). Use StaticTokenVerifier directly."
        )

    else:
        raise ValueError(
            f"Unknown FASTMCP_SERVER_AUTH value: '{auth_type}'. "
            f"Expected: jwt, introspection, or static"
        )
