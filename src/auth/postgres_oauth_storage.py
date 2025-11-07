"""
PostgreSQL-backed AsyncKeyValue store for FastMCP OAuth client storage.

This module provides a PostgreSQL implementation compatible with FastMCP 2.13+
AsyncKeyValue protocol. OAuth clients are stored in the `oauth_clients` table
and persist across Cloud Run deployments.

Usage:
    from src.auth.postgres_oauth_storage import PostgreSQLOAuthStorage
    from src.storage.cloud_sql_engine import CloudSQLEngine
    from fastmcp.server.auth.providers.github import GitHubProvider

    # Create storage
    engine = CloudSQLEngine(...)
    pool = await engine.get_asyncpg_pool()
    storage = PostgreSQLOAuthStorage(pool)

    # Use with GitHubProvider
    auth_provider = GitHubProvider(client_storage=storage)
"""

import asyncpg
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PostgreSQLOAuthStorage:
    """
    PostgreSQL-backed storage for FastMCP OAuth clients.

    Implements the AsyncKeyValue protocol required by FastMCP 2.13+.
    Stores OAuth client data in the `oauth_clients` table.

    The AsyncKeyValue protocol requires:
    - async def get(key: str, default=None) -> Optional[bytes]
    - async def set(key: str, value: bytes) -> None
    - async def delete(key: str) -> None
    - async def exists(key: str) -> bool
    - async def keys(prefix: str = "") -> list[str]
    """

    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize PostgreSQL OAuth storage.

        Args:
            pool: asyncpg connection pool
        """
        self.pool = pool
        self._initialized = False
        logger.info("Initialized PostgreSQL OAuth storage")

    async def _ensure_table(self):
        """Ensure oauth_clients table exists (called lazily)."""
        if self._initialized:
            return

        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS oauth_clients (
                        client_id TEXT PRIMARY KEY,
                        value BYTEA NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_oauth_clients_created_at
                    ON oauth_clients(created_at)
                """)

            self._initialized = True
            logger.info("OAuth clients table ready")

        except Exception as e:
            logger.error(f"Failed to ensure oauth_clients table: {e}")
            raise

    async def get(self, key: str, default: Optional[bytes] = None) -> Optional[bytes]:
        """
        Retrieve OAuth client data by key.

        Args:
            key: Client identifier
            default: Default value if key not found

        Returns:
            Stored bytes value or default
        """
        await self._ensure_table()

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT value FROM oauth_clients WHERE client_id = $1",
                    key
                )

                if row:
                    logger.debug(f"Retrieved OAuth client: {key}")
                    return bytes(row['value'])

                logger.debug(f"OAuth client not found: {key}")
                return default

        except Exception as e:
            logger.error(f"Failed to get OAuth client {key}: {e}")
            return default

    async def set(self, key: str, value: bytes) -> None:
        """
        Store OAuth client data.

        Args:
            key: Client identifier
            value: OAuth client data (bytes)
        """
        await self._ensure_table()

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO oauth_clients (client_id, value, created_at, updated_at)
                    VALUES ($1, $2, NOW(), NOW())
                    ON CONFLICT (client_id)
                    DO UPDATE SET value = $2, updated_at = NOW()
                    """,
                    key, value
                )

            logger.info(f"Stored OAuth client: {key}")

        except Exception as e:
            logger.error(f"Failed to store OAuth client {key}: {e}")
            raise

    async def delete(self, key: str) -> None:
        """
        Delete OAuth client data.

        Args:
            key: Client identifier to delete
        """
        await self._ensure_table()

        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM oauth_clients WHERE client_id = $1",
                    key
                )

            logger.info(f"Deleted OAuth client: {key} (rows affected: {result})")

        except Exception as e:
            logger.error(f"Failed to delete OAuth client {key}: {e}")
            raise

    async def exists(self, key: str) -> bool:
        """
        Check if key exists.

        Args:
            key: Client identifier

        Returns:
            True if key exists, False otherwise
        """
        await self._ensure_table()

        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM oauth_clients WHERE client_id = $1)",
                    key
                )
                return bool(result)

        except Exception as e:
            logger.error(f"Failed to check existence of OAuth client {key}: {e}")
            return False

    async def keys(self, prefix: str = "") -> list[str]:
        """
        List all keys matching a prefix.

        Args:
            prefix: Key prefix to filter by

        Returns:
            List of matching keys
        """
        await self._ensure_table()

        try:
            async with self.pool.acquire() as conn:
                if prefix:
                    rows = await conn.fetch(
                        "SELECT client_id FROM oauth_clients WHERE client_id LIKE $1 ORDER BY created_at DESC",
                        f"{prefix}%"
                    )
                else:
                    rows = await conn.fetch(
                        "SELECT client_id FROM oauth_clients ORDER BY created_at DESC"
                    )

                keys = [row['client_id'] for row in rows]
                logger.debug(f"Listed {len(keys)} OAuth clients with prefix '{prefix}'")
                return keys

        except Exception as e:
            logger.error(f"Failed to list OAuth clients with prefix {prefix}: {e}")
            return []

    async def close(self) -> None:
        """Close the connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Closed PostgreSQL OAuth storage pool")
