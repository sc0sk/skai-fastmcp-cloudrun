"""
JWT token verification implementation.

This module provides JWT validation with support for:
- JWKS endpoints (automatic key rotation)
- Static public keys (RSA/ECDSA)
- HMAC symmetric keys
- Static token mapping for development
- RSA key pair generation for testing
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt import PyJWKClient

from src.auth.base import TokenVerifier, hash_token
from src.models.auth import (
    JWTVerifierConfig,
    StaticTokenVerifierConfig,
    TokenClaims,
    ValidationResult,
)

logger = logging.getLogger(__name__)


class JWTVerifier(TokenVerifier):
    """
    JWT token verifier with support for JWKS, static keys, and HMAC.

    Validates JWT tokens by verifying cryptographic signatures and claims.
    """

    def __init__(self, config: JWTVerifierConfig):
        """
        Initialize JWT verifier.

        Args:
            config: JWT verification configuration
        """
        self.config = config
        self._jwks_client: PyJWKClient | None = None

        # Initialize JWKS client if using JWKS endpoint
        if config.jwks_uri:
            self._jwks_client = PyJWKClient(
                config.jwks_uri,
                lifespan=config.jwks_cache_ttl,
                cache_keys=True,
            )
            logger.info(f"Initialized JWKS client with URI: {config.jwks_uri}")

    async def verify(self, token: str) -> ValidationResult:
        """
        Verify JWT token and extract claims.

        Args:
            token: JWT token string

        Returns:
            ValidationResult with success/failure status and claims
        """
        token_hash = hash_token(token)
        try:
            # Determine verification key
            if self._jwks_client:
                # JWKS endpoint - get signing key
                try:
                    signing_key = self._jwks_client.get_signing_key_from_jwt(token)
                    verification_key = signing_key.key
                    logger.debug(f"[{token_hash}] Using JWKS signing key for verification")
                except Exception as e:
                    logger.error(f"[{token_hash}] Failed to get signing key from JWKS: {e}")
                    return ValidationResult.failure_result(
                        error="server_error",
                        error_description="Failed to fetch signing key from JWKS endpoint",
                        error_code=500,
                    )
            else:
                # Static key (PEM or HMAC secret)
                verification_key = self.config.public_key.get_secret_value() if self.config.public_key else None
                logger.debug(f"[{token_hash}] Using static key for {self.config.algorithm} verification")

            # Decode and validate JWT
            decoded = jwt.decode(
                token,
                verification_key,
                algorithms=[self.config.algorithm],
                audience=self.config.audience,
                issuer=self.config.issuer,
                leeway=self.config.clock_skew,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                },
            )

            # Extract claims
            claims = self._extract_claims(decoded)

            # Verify required scopes
            if self.config.required_scopes and not self.verify_scopes(
                claims, self.config.required_scopes
            ):
                logger.warning(
                    f"[{token_hash}] Token missing required scopes. Has: {claims.scopes}, Required: {self.config.required_scopes}"
                )
                return ValidationResult.failure_result(
                    error="insufficient_scope",
                    error_description="Insufficient scope",
                    error_code=403,
                )

            logger.info(f"[{token_hash}] Successfully validated JWT token for identity: {claims.identity}")
            return ValidationResult.success_result(claims)

        except jwt.ExpiredSignatureError:
            logger.warning(f"[{token_hash}] Token has expired")
            return ValidationResult.failure_result(
                error="invalid_token", error_description="Token has expired"
            )
        except jwt.InvalidAudienceError:
            logger.warning(f"[{token_hash}] Invalid audience. Expected: {self.config.audience}")
            return ValidationResult.failure_result(
                error="invalid_token",
                error_description="Invalid token",
            )
        except jwt.InvalidIssuerError:
            logger.warning(f"[{token_hash}] Invalid issuer. Expected: {self.config.issuer}")
            return ValidationResult.failure_result(
                error="invalid_token",
                error_description="Invalid token",
            )
        except jwt.InvalidSignatureError:
            logger.warning(f"[{token_hash}] Token signature verification failed")
            return ValidationResult.failure_result(
                error="invalid_token", error_description="Invalid token"
            )
        except jwt.DecodeError as e:
            logger.warning(f"[{token_hash}] Token decode error: {e}")
            return ValidationResult.failure_result(
                error="invalid_token", error_description="Invalid token"
            )
        except Exception as e:
            logger.error(f"[{token_hash}] Unexpected error during token validation: {e}", exc_info=True)
            return ValidationResult.failure_result(
                error="server_error",
                error_description="Internal server error",
                error_code=500,
            )

    def _extract_claims(self, decoded: dict[str, Any]) -> TokenClaims:
        """
        Extract token claims from decoded JWT.

        Args:
            decoded: Decoded JWT payload

        Returns:
            TokenClaims object
        """
        # Extract scopes (can be space-separated string or list)
        scopes = []
        if "scope" in decoded:
            scope_value = decoded["scope"]
            if isinstance(scope_value, str):
                scopes = scope_value.split()
            elif isinstance(scope_value, list):
                scopes = scope_value
        elif "scopes" in decoded:
            scopes = decoded.get("scopes", [])

        # Extract timestamps
        issued_at = None
        if "iat" in decoded:
            issued_at = datetime.fromtimestamp(decoded["iat"])

        expires_at = None
        if "exp" in decoded:
            expires_at = datetime.fromtimestamp(decoded["exp"])

        not_before = None
        if "nbf" in decoded:
            not_before = datetime.fromtimestamp(decoded["nbf"])

        return TokenClaims(
            subject=decoded.get("sub"),
            client_id=decoded.get("client_id") or decoded.get("azp"),
            username=decoded.get("username") or decoded.get("preferred_username"),
            issuer=decoded.get("iss"),
            audience=decoded.get("aud"),
            issued_at=issued_at,
            expires_at=expires_at,
            not_before=not_before,
            scopes=scopes,
            extra_claims={
                k: v for k, v in decoded.items() if k not in {
                    "sub", "client_id", "azp", "username", "preferred_username",
                    "iss", "aud", "iat", "exp", "nbf", "scope", "scopes"
                }
            },
        )


class StaticTokenVerifier(TokenVerifier):
    """
    Static token verifier for development and testing.

    Maps predefined token strings to claims without cryptographic verification.
    """

    def __init__(self, config: StaticTokenVerifierConfig):
        """
        Initialize static token verifier.

        Args:
            config: Static token verification configuration
        """
        self.config = config
        logger.warning(
            "StaticTokenVerifier initialized - FOR DEVELOPMENT ONLY. "
            "Do not use in production!"
        )

    async def verify(self, token: str) -> ValidationResult:
        """
        Verify static token by dictionary lookup.

        Args:
            token: Token string

        Returns:
            ValidationResult with success/failure status and claims
        """
        token_hash = hash_token(token)

        # Look up token in configured mapping
        if token not in self.config.tokens:
            logger.warning(f"[{token_hash}] Unknown static token")
            return ValidationResult.failure_result(
                error="invalid_token", error_description="Invalid token"
            )

        # Extract configured claims
        token_claims = self.config.tokens[token]
        claims = TokenClaims(
            subject=token_claims.get("subject"),
            client_id=token_claims.get("client_id"),
            username=token_claims.get("username"),
            scopes=token_claims.get("scopes", []),
            extra_claims=token_claims,
        )

        # Verify required scopes
        if self.config.required_scopes and not self.verify_scopes(
            claims, self.config.required_scopes
        ):
            logger.warning(
                f"[{token_hash}] Static token missing required scopes. Has: {claims.scopes}, Required: {self.config.required_scopes}"
            )
            return ValidationResult.failure_result(
                error="insufficient_scope",
                error_description="Insufficient scope",
                error_code=403,
            )

        logger.info(f"[{token_hash}] Validated static token for identity: {claims.identity}")
        return ValidationResult.success_result(claims)


class RSAKeyPair:
    """
    RSA key pair for JWT signing and verification.

    DEVELOPMENT USE ONLY - generates test keys and tokens.
    """

    def __init__(self, private_key: Any, public_key: Any, key_id: str | None = None):
        """
        Initialize RSA key pair.

        Args:
            private_key: Cryptography RSA private key object
            public_key: Cryptography RSA public key object
            key_id: Optional key identifier (kid)
        """
        self.private_key = private_key
        self.public_key = public_key
        self.key_id = key_id or str(uuid.uuid4())

    @property
    def private_key_pem(self) -> str:
        """Export private key as PEM string"""
        return self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()

    @property
    def public_key_pem(self) -> str:
        """Export public key as PEM string"""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

    def create_token(
        self,
        subject: str,
        issuer: str,
        audience: str,
        scopes: list[str] | None = None,
        expiration: int = 3600,
        **extra_claims,
    ) -> str:
        """
        Create signed JWT token for testing.

        Args:
            subject: Token subject (sub claim)
            issuer: Token issuer (iss claim)
            audience: Token audience (aud claim)
            scopes: Token scopes (scope claim)
            expiration: Token lifetime in seconds
            **extra_claims: Additional claims to include

        Returns:
            Signed JWT token string
        """
        now = datetime.utcnow()
        payload = {
            "sub": subject,
            "iss": issuer,
            "aud": audience,
            "iat": now,
            "exp": now + timedelta(seconds=expiration),
            **extra_claims,
        }

        if scopes:
            payload["scope"] = " ".join(scopes)

        return jwt.encode(
            payload,
            self.private_key_pem,
            algorithm="RS256",
            headers={"kid": self.key_id},
        )

    @classmethod
    def generate(cls, key_size: int = 2048) -> "RSAKeyPair":
        """
        Generate new RSA key pair.

        Args:
            key_size: RSA key size in bits (default: 2048)

        Returns:
            RSAKeyPair instance
        """
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
        public_key = private_key.public_key()
        return cls(private_key=private_key, public_key=public_key)
