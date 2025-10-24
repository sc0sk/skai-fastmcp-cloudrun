"""
Tests for token hashing in log output.

Verifies no plaintext tokens appear in logs.
"""

import pytest

from src.auth.base import hash_token


def test_hash_token_same_input_same_output():
    """Test that same token produces same hash"""
    token = "my_secret_token_123"
    hash1 = hash_token(token)
    hash2 = hash_token(token)
    assert hash1 == hash2


def test_hash_token_different_inputs_different_outputs():
    """Test that different tokens produce different hashes"""
    token1 = "token_abc"
    token2 = "token_xyz"
    hash1 = hash_token(token1)
    hash2 = hash_token(token2)
    assert hash1 != hash2


def test_hash_token_returns_16_chars():
    """Test that hash is exactly 16 characters (first 16 of SHA-256 hex)"""
    token = "test_token"
    result = hash_token(token)
    assert len(result) == 16
    assert all(c in "0123456789abcdef" for c in result)


def test_hash_token_irreversible():
    """Test that hash doesn't contain original token"""
    token = "my_sensitive_token"
    result = hash_token(token)
    assert token not in result
    assert token.lower() not in result.lower()
