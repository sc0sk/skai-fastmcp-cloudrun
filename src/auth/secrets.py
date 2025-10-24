"""
Secret management with Google Cloud Secret Manager integration.

Provides secure secret retrieval with TTL-based caching.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, SecretStr, model_validator


class SecretBackend(str, Enum):
    """Secret storage backend types"""

    ENV = "env"
    GCP_SECRET_MANAGER = "gcp_secret_manager"


class SecretConfig(BaseModel):
    """Configuration for secret management"""

    backend: SecretBackend = Field(
        default=SecretBackend.ENV, description="Secret storage backend"
    )
    gcp_project_id: str | None = Field(
        None, description="GCP project ID (required for GCP Secret Manager)"
    )
    cache_ttl_seconds: int = Field(
        default=300, description="Secret cache TTL in seconds", ge=0, le=3600
    )

    @model_validator(mode="after")
    def validate_gcp_config(self) -> "SecretConfig":
        """Ensure gcp_project_id required when backend is GCP_SECRET_MANAGER"""
        if (
            self.backend == SecretBackend.GCP_SECRET_MANAGER
            and not self.gcp_project_id
        ):
            raise ValueError(
                "gcp_project_id is required when backend is gcp_secret_manager"
            )
        return self


class CachedSecret(BaseModel):
    """Cached secret with TTL tracking"""

    name: str = Field(description="Secret name")
    value: SecretStr = Field(description="Secret value (masked in logs)")
    cached_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When secret was cached",
    )
    version: str = Field(default="latest", description="Secret version")

    def is_expired(self, ttl_seconds: int) -> bool:
        """
        Check if secret cache has expired.

        Args:
            ttl_seconds: TTL in seconds

        Returns:
            True if cache expired, False otherwise
        """
        if ttl_seconds == 0:
            return True  # TTL=0 means always fetch fresh
        now = datetime.now(timezone.utc)
        age = now - self.cached_at.replace(tzinfo=timezone.utc)
        return age.total_seconds() > ttl_seconds

    @property
    def age_seconds(self) -> float:
        """Get age of cached secret in seconds"""
        now = datetime.now(timezone.utc)
        cached = self.cached_at.replace(tzinfo=timezone.utc)
        return (now - cached).total_seconds()
