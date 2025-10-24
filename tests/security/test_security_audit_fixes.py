"""
Security audit verification tests.

Verifies all vulnerabilities identified in SECURITY_AUDIT.md are fixed.
"""

import jwt
import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import ValidationError

from src.models.auth import JWTVerifierConfig


def test_algorithm_confusion_attack_rejected():
    """
    Test that algorithm confusion attack is prevented at configuration level.

    This verifies CVE-level vulnerability mitigation where:
    - Server configuration prevents HMAC algorithms with JWKS endpoints
    - This blocks the attack vector where attacker changes RS256 to HS256
    - Our defense: configuration validation rejects HS256 with JWKS
    """
    # ATTACK SCENARIO: Attacker tries to configure server to accept HS256 with JWKS
    # This would allow them to sign tokens with public key as HMAC secret
    with pytest.raises(ValidationError) as exc_info:
        JWTVerifierConfig(
            jwks_uri="https://example.com/.well-known/jwks.json",
            issuer="https://example.com",
            audience="my-api",
            algorithm="HS256",  # HMAC not allowed with JWKS
        )

    # Verify the config creation fails with clear error about asymmetric algorithms
    error_msg = str(exc_info.value).lower()
    assert "asymmetric" in error_msg or "algorithm" in error_msg
    assert "hs256" in error_msg or "hmac" in error_msg

    # VERIFY: All HMAC variants are rejected
    for hmac_algo in ["HS256", "HS384", "HS512"]:
        with pytest.raises(ValidationError):
            JWTVerifierConfig(
                jwks_uri="https://example.com/.well-known/jwks.json",
                issuer="https://example.com",
                audience="my-api",
                algorithm=hmac_algo,
            )

    # VERIFY: Asymmetric algorithms are allowed
    for safe_algo in ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]:
        config = JWTVerifierConfig(
            jwks_uri="https://example.com/.well-known/jwks.json",
            issuer="https://example.com",
            audience="my-api",
            algorithm=safe_algo,
        )
        assert config.algorithm == safe_algo
