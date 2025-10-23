"""Debug utilities for MCP tools.

Provides:
- Structured debug message formatting
- Sensitive data sanitization
- Automatic operation timing

All utilities are safe to use with ctx=None (no-op when context not provided).
"""

from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
import time
import re


# Patterns for sensitive field names (case-insensitive matching)
SENSITIVE_PATTERNS = [
    "password", "passwd", "pwd",
    "token", "auth_token", "access_token", "refresh_token",
    "api_key", "apikey", "secret", "secret_key",
    "private_key", "credential", "credentials",
    "authorization", "bearer"
]

# Maximum value length before truncation (1KB)
MAX_VALUE_LENGTH = 1024


def format_debug_message(context: str, description: str, **kwargs) -> str:
    """Format debug message with consistent structure.

    Args:
        context: Operation context (e.g., "search_hansard_speeches")
        description: Human-readable description (e.g., "Starting search")
        **kwargs: Additional key-value pairs to include

    Returns:
        Formatted debug string: "context: description (key1=value1, key2=value2)"

    Example:
        >>> format_debug_message("search", "Starting", query="test", limit=10)
        "search: Starting (query='test', limit=10)"
    """
    message = f"{context}: {description}"

    if kwargs:
        # Format kwargs as key=value pairs
        pairs = []
        for key, value in kwargs.items():
            # Handle string values with quotes
            if isinstance(value, str):
                # Truncate long strings
                if len(value) > MAX_VALUE_LENGTH:
                    value = value[:MAX_VALUE_LENGTH] + "...truncated"
                pairs.append(f"{key}='{value}'")
            else:
                pairs.append(f"{key}={value}")

        message += f" ({', '.join(pairs)})"

    return message


def sanitize_debug_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Redact sensitive fields and truncate long values.

    Args:
        data: Dictionary potentially containing sensitive data

    Returns:
        New dictionary with sensitive fields redacted and long values truncated

    Example:
        >>> sanitize_debug_data({"password": "secret123", "user": "alice"})
        {"password": "***REDACTED***", "user": "alice"}
    """
    sanitized = {}

    for key, value in data.items():
        # Check if key matches sensitive patterns (case-insensitive)
        is_sensitive = any(
            pattern.lower() in key.lower()
            for pattern in SENSITIVE_PATTERNS
        )

        if is_sensitive:
            sanitized[key] = "***REDACTED***"
        elif isinstance(value, dict):
            # Recursively sanitize nested dicts
            sanitized[key] = sanitize_debug_data(value)
        elif isinstance(value, str) and len(value) > MAX_VALUE_LENGTH:
            # Truncate long strings
            sanitized[key] = value[:MAX_VALUE_LENGTH] + "...truncated"
        else:
            sanitized[key] = value

    return sanitized


class TimingContext:
    """Async context manager for timing operations.

    Automatically logs operation duration to ctx.debug() when exiting.
    Safe to use with ctx=None (no-op).

    Example:
        async with TimingContext(ctx, "database_query"):
            results = await db.query()
        # Logs: "database_query (duration=123.45ms)"
    """

    def __init__(self, ctx: Optional[Any], operation_name: str):
        """Initialize timing context.

        Args:
            ctx: FastMCP Context object (or None for no-op)
            operation_name: Name of operation being timed
        """
        self.ctx = ctx
        self.operation_name = operation_name
        self.start_time: Optional[float] = None

    async def __aenter__(self):
        """Start timing."""
        self.start_time = time.perf_counter()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and log duration."""
        if self.start_time is not None and self.ctx:
            duration_ms = (time.perf_counter() - self.start_time) * 1000
            await self.ctx.debug(f"{self.operation_name} (duration={duration_ms:.2f}ms)")

        # Don't suppress exceptions
        return False
