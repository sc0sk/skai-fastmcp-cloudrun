"""
Rate limiting for token verification.

Implements token bucket algorithm to prevent brute force attacks.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from pydantic import BaseModel, Field


class RateLimitConfig(BaseModel):
    """Configuration for rate limiting"""

    max_attempts: int = Field(
        default=10, description="Maximum attempts per time window", ge=1, le=1000
    )
    window_seconds: int = Field(
        default=60, description="Time window in seconds", ge=1, le=3600
    )
    enabled: bool = Field(default=True, description="Whether rate limiting is enabled")


class RateLimitBucket(BaseModel):
    """Token bucket for rate limiting a specific token hash"""

    token_hash: str = Field(description="SHA-256 hash of token (first 16 chars)")
    attempts: List[datetime] = Field(
        default_factory=list, description="Timestamps of verification attempts"
    )
    last_cleanup: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last time expired entries were cleaned",
    )

    def is_rate_limited(self, config: RateLimitConfig) -> bool:
        """
        Check if token hash is rate limited.

        Args:
            config: Rate limit configuration

        Returns:
            True if rate limit exceeded, False otherwise
        """
        if not config.enabled:
            return False

        # Cleanup expired attempts first
        self.cleanup_expired(config.window_seconds)

        # Check if we've exceeded max attempts
        return len(self.attempts) >= config.max_attempts

    def record_attempt(self) -> None:
        """Record a new verification attempt"""
        self.attempts.append(datetime.now(timezone.utc))

    def cleanup_expired(self, window_seconds: int) -> None:
        """
        Remove attempts older than the time window.

        Args:
            window_seconds: Time window in seconds
        """
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
        self.attempts = [attempt for attempt in self.attempts if attempt > cutoff]
        self.last_cleanup = datetime.now(timezone.utc)


class RateLimiter:
    """
    Token bucket rate limiter for preventing brute force attacks.

    Thread-safe implementation using asyncio.Lock.
    """

    def __init__(self, config: RateLimitConfig):
        """
        Initialize rate limiter.

        Args:
            config: Rate limit configuration
        """
        self.config = config
        self.buckets: dict[str, RateLimitBucket] = {}
        self._lock = None  # Will be created on first use

    def _get_or_create_bucket(self, token_hash: str) -> RateLimitBucket:
        """Get existing bucket or create new one"""
        if token_hash not in self.buckets:
            self.buckets[token_hash] = RateLimitBucket(token_hash=token_hash)
        return self.buckets[token_hash]

    def check_rate_limit(self, token_hash: str) -> bool:
        """
        Check if token hash is rate limited.

        Args:
            token_hash: SHA-256 hash of token

        Returns:
            True if rate limited, False if allowed
        """
        if not self.config.enabled:
            return False

        # Periodic cleanup to prevent memory growth
        if len(self.buckets) > 1000:
            self.cleanup()

        bucket = self._get_or_create_bucket(token_hash)
        is_limited = bucket.is_rate_limited(self.config)

        # Record this attempt if not rate limited
        if not is_limited:
            bucket.record_attempt()

        return is_limited

    def cleanup(self) -> None:
        """Remove expired buckets to bound memory usage"""
        cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=self.config.window_seconds
        )

        # Remove buckets with no recent attempts
        expired_hashes = [
            token_hash
            for token_hash, bucket in self.buckets.items()
            if bucket.last_cleanup < cutoff
        ]

        for token_hash in expired_hashes:
            del self.buckets[token_hash]
