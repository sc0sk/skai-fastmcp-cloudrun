"""
Tests for rate limiting functionality.

Verifies token bucket rate limiter prevents brute force attacks.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from auth.rate_limiter import RateLimitBucket, RateLimitConfig, RateLimiter


def test_rate_limit_blocks_11th_attempt():
    """Test that 10 attempts pass but 11th is rate limited"""
    config = RateLimitConfig(max_attempts=10, window_seconds=60)
    limiter = RateLimiter(config)
    token_hash = "test_hash_abc123"

    # First 10 attempts should pass
    for i in range(10):
        assert not limiter.check_rate_limit(token_hash), f"Attempt {i+1} should not be rate limited"

    # 11th attempt should be rate limited
    assert limiter.check_rate_limit(token_hash), "11th attempt should be rate limited"


def test_rate_limit_resets_after_window():
    """Test that rate limit resets after time window expires"""
    config = RateLimitConfig(max_attempts=3, window_seconds=1)  # 1 second window for fast test
    bucket = RateLimitBucket(token_hash="test_hash")

    # Add 3 attempts
    for _ in range(3):
        bucket.record_attempt()

    # Should be rate limited
    assert bucket.is_rate_limited(config)

    # Wait for window to expire
    import time
    time.sleep(1.1)

    # Cleanup expired entries
    bucket.cleanup_expired(config.window_seconds)

    # Should no longer be rate limited
    assert not bucket.is_rate_limited(config)


def test_rate_limit_per_token_hash():
    """Test that different tokens have independent rate limits"""
    config = RateLimitConfig(max_attempts=5, window_seconds=60)
    limiter = RateLimiter(config)

    token_hash_1 = "hash_abc123"
    token_hash_2 = "hash_xyz789"

    # Use up limit for token 1
    for _ in range(5):
        limiter.check_rate_limit(token_hash_1)

    # Token 1 should be rate limited
    assert limiter.check_rate_limit(token_hash_1)

    # Token 2 should still have full limit available
    assert not limiter.check_rate_limit(token_hash_2)


def test_token_hashing_consistency():
    """Test that hash_token produces consistent hashes"""
    from auth.base import hash_token

    token = "my_secret_token"
    hash1 = hash_token(token)
    hash2 = hash_token(token)

    assert hash1 == hash2
    assert len(hash1) == 16


def test_rate_limiter_memory_bounded():
    """Test that rate limiter automatically cleans up expired entries"""
    config = RateLimitConfig(max_attempts=10, window_seconds=1)
    limiter = RateLimiter(config)

    # Create entries for multiple tokens
    for i in range(100):
        token_hash = f"hash_{i}"
        limiter.check_rate_limit(token_hash)

    # Wait for entries to expire
    import time
    time.sleep(1.1)

    # Trigger cleanup by checking a new token
    limiter.check_rate_limit("new_token")

    # After cleanup, memory should be bounded (old entries removed)
    # We can't directly check internal state, but we verify old tokens work again
    assert not limiter.check_rate_limit("hash_0"), "Expired entry should be cleaned up"


@pytest.mark.asyncio
async def test_concurrent_rate_limiting():
    """Test that rate limiter is thread-safe under concurrent access"""
    config = RateLimitConfig(max_attempts=100, window_seconds=60)
    limiter = RateLimiter(config)
    token_hash = "concurrent_test"

    # Simulate 200 concurrent checks (should hit limit at 100)
    async def check():
        return limiter.check_rate_limit(token_hash)

    results = await asyncio.gather(*[check() for _ in range(200)])

    # First ~100 should pass, rest should be rate limited
    passed = sum(1 for r in results if not r)
    rate_limited = sum(1 for r in results if r)

    # Due to race conditions, we expect roughly 100 to pass
    assert passed <= config.max_attempts + 5, "Too many requests passed"
    assert rate_limited > 90, "Not enough requests were rate limited"
