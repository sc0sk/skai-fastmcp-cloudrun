"""In-memory KVStorage for OAuth client registration persistence.

This simple implementation stores OAuth client data in a thread-safe dict
with optional TTL (time-to-live) cleanup. Suitable for single-instance
deployments and testing. For multi-instance production, use Redis backend.
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class MemoryKVStorage:
    """In-memory key-value storage implementing FastMCP's KVStorage protocol.
    
    Thread-safe dict-based storage with optional TTL cleanup.
    Automatically removes expired entries on access.
    """

    def __init__(self, cleanup_interval_seconds: int = 3600):
        """Initialize memory storage.
        
        Args:
            cleanup_interval_seconds: How often to run TTL cleanup (default 1 hour)
        """
        self._data: Dict[str, tuple[dict[str, Any], float]] = {}
        self._lock = asyncio.Lock()
        self._cleanup_interval = cleanup_interval_seconds
        self._cleanup_task: Optional[asyncio.Task[None]] = None
        logger.info("MemoryKVStorage initialized")

    async def get(
        self, key: str, collection: str | None = None
    ) -> dict[str, Any] | None:
        """Get a value from storage.
        
        Args:
            key: The key to retrieve
            collection: Optional namespace (prefixed to key)
            
        Returns:
            The stored dict or None if not found or expired
        """
        storage_key = self._compose_key(key, collection)
        
        async with self._lock:
            if storage_key not in self._data:
                return None
            
            value, ttl_end = self._data[storage_key]
            
            # Check if expired
            if ttl_end > 0 and time.time() >= ttl_end:
                del self._data[storage_key]
                logger.debug(f"Expired OAuth client: {storage_key}")
                return None
            
            logger.debug(f"Retrieved OAuth client: {storage_key}")
            return value

    async def put(
        self,
        key: str,
        value: dict[str, Any],
        collection: str | None = None,
        ttl: int | None = None,
    ) -> None:
        """Store a value in memory.
        
        Args:
            key: The key to store under
            value: The dict to store
            collection: Optional namespace (prefixed to key)
            ttl: Optional time-to-live in seconds (None = no expiration)
        """
        storage_key = self._compose_key(key, collection)
        ttl_end = (time.time() + ttl) if ttl else 0
        
        async with self._lock:
            self._data[storage_key] = (value, ttl_end)
            logger.debug(
                f"Stored OAuth client: {storage_key}, TTL: {ttl}s"
            )

    async def set(
        self, key: str, value: dict[str, Any], collection: str | None = None
    ) -> None:
        """Alias for put() for backwards compatibility.
        
        Args:
            key: The key to store under
            value: The dict to store
            collection: Optional namespace (prefixed to key)
        """
        await self.put(key=key, value=value, collection=collection)

    async def delete(
        self, key: str, collection: str | None = None
    ) -> None:
        """Delete a value from storage.
        
        Args:
            key: The key to delete
            collection: Optional namespace (prefixed to key)
        """
        storage_key = self._compose_key(key, collection)
        
        async with self._lock:
            if storage_key in self._data:
                del self._data[storage_key]
                logger.debug(f"Deleted OAuth client: {storage_key}")

    def _compose_key(self, key: str, collection: str | None = None) -> str:
        """Compose a storage key with optional collection namespace.
        
        Args:
            key: The logical key
            collection: Optional collection namespace
            
        Returns:
            Composed key string
        """
        return f"{collection}:{key}" if collection else key

    async def cleanup_old_entries(
        self, max_age_seconds: int = 30 * 24 * 60 * 60
    ) -> int:
        """Remove expired entries.
        
        Args:
            max_age_seconds: Not used (TTL handled per-entry)
            
        Returns:
            Number of entries removed
        """
        now = time.time()
        removed = 0
        
        async with self._lock:
            expired_keys = [
                k for k, (_, ttl_end) in self._data.items()
                if ttl_end > 0 and now >= ttl_end
            ]
            for k in expired_keys:
                del self._data[k]
                removed += 1
        
        if removed > 0:
            logger.info(f"Cleaned up {removed} expired OAuth clients")
        
        return removed

    async def close(self) -> None:
        """Cleanup and close storage."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("MemoryKVStorage closed")
