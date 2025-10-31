"""PostgreSQL-backed KVStorage for OAuth client persistence on Cloud Run.

This storage implementation stores OAuth client registrations in PostgreSQL,
ensuring they persist across Cloud Run container restarts and scale events.
"""

import asyncio
import json
import logging
from typing import Any
from sqlalchemy import text

from src.storage.cloud_sql_engine import CloudSQLEngine
from src import config

logger = logging.getLogger(__name__)


class PostgresKVStorage:
    """PostgreSQL-backed key-value storage for OAuth client data.

    Implements the FastMCP KVStorage protocol using Cloud SQL PostgreSQL.
    Client registrations are stored in a simple oauth_clients table.
    """

    def __init__(self, engine_manager: CloudSQLEngine | None = None):
        """Initialize PostgreSQL KV storage.

        Args:
            engine_manager: Optional CloudSQLEngine. If None, creates one lazily on first use.
        """
        self._engine_manager = engine_manager
        self._table_initialized = False

    def _lazy_init_engine(self):
        """Lazily initialize the engine on first use."""
        if self._engine_manager is not None:
            return
        
        # Create engine with environment config on first use
        # Pass user=None, password=None to enable Cloud SQL IAM auth
        project_id = (
            config.get_gcp_project_id()
            or config.DEFAULT_GCP_PROJECT_ID
        )
        self._engine_manager = CloudSQLEngine(
            project_id=project_id,
            region=config.get_gcp_region(),
            instance=(
                config.get_cloudsql_instance()
                or config.CLOUDSQL_INSTANCE_NAME
            ),
            database=config.get_cloudsql_database(),
            user=None,  # Use IAM Auth (will auto-detect service account)
            password=None,  # Use IAM Auth (no password needed)
        )
        logger.info("PostgresKVStorage engine initialized on first use with IAM auth")

    def _ensure_table_sync(self):
        """Ensure the oauth_clients table exists (sync version)."""
        if self._table_initialized:
            return

        self._lazy_init_engine()

        with self._engine_manager.engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS oauth_clients (
                    key TEXT PRIMARY KEY,
                    value JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Create index on updated_at for cleanup queries
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS oauth_clients_updated_at_idx
                ON oauth_clients(updated_at)
            """))

        self._table_initialized = True
        logger.info("OAuth client storage table initialized")

    async def _ensure_table(self):
        """Ensure the oauth_clients table exists."""
        await asyncio.to_thread(self._ensure_table_sync)

    def _compose_key(self, key: str, collection: str | None = None) -> str:
        """Compose a storage key with optional collection namespace.

        Args:
            key: The logical key
            collection: Optional collection namespace

        Returns:
            Composed key string safe for storage
        """
        return f"{collection}:{key}" if collection else key

    async def get(self, key: str, collection: str | None = None) -> dict[str, Any] | None:
        """Get a JSON dict from storage by key.

        Args:
            key: The key to retrieve
            collection: Optional namespace/collection

        Returns:
            The stored dict or None if not found
        """
        await self._ensure_table()
        storage_key = self._compose_key(key, collection)

        def _get_sync():
            self._lazy_init_engine()
            with self._engine_manager.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT value FROM oauth_clients WHERE key = :key"),
                    {"key": storage_key}
                )
                row = result.fetchone()

                if row is None:
                    logger.debug(f"No OAuth client found for key '{storage_key}'")
                    return None

                logger.debug(f"Loaded OAuth client for key '{storage_key}'")
                # JSONB column returns dict directly
                return row[0]

        return await asyncio.to_thread(_get_sync)

    async def put(
        self,
        key: str,
        value: dict[str, Any],
        collection: str | None = None,
        ttl: int | None = None,
    ) -> None:
        """Store a JSON dict under a key (KeyValue.put interface).

        Args:
            key: The key to store under
            value: The dict to store (JSON serializable)
            collection: Optional namespace/collection
            ttl: Optional time-to-live in seconds (ignored; managed via cleanup)
        """
        await self._ensure_table()
        storage_key = self._compose_key(key, collection)

        def _put_sync():
            self._lazy_init_engine()
            with self._engine_manager.engine.begin() as conn:
                conn.execute(
                    text("""
                        INSERT INTO oauth_clients (key, value, updated_at)
                        VALUES (:key, :value::jsonb, CURRENT_TIMESTAMP)
                        ON CONFLICT (key)
                        DO UPDATE SET
                            value = EXCLUDED.value,
                            updated_at = CURRENT_TIMESTAMP
                    """),
                    {"key": storage_key, "value": json.dumps(value)}
                )

            logger.debug(f"Saved OAuth client for key '{storage_key}'")

        await asyncio.to_thread(_put_sync)

    # Back-compat helper for any callers using 'set' instead of 'put'
    async def set(self, key: str, value: dict[str, Any]) -> None:
        """Alias for put without collection/ttl for compatibility."""
        await self.put(key=key, value=value)

    async def delete(self, key: str, collection: str | None = None) -> None:
        """Delete a value from storage.

        Args:
            key: The key to delete
        """
        await self._ensure_table()
        storage_key = self._compose_key(key, collection)

        def _delete_sync():
            self._lazy_init_engine()
            with self._engine_manager.engine.begin() as conn:
                conn.execute(
                    text("DELETE FROM oauth_clients WHERE key = :key"),
                    {"key": storage_key}
                )

            logger.debug(f"Deleted OAuth client for key '{storage_key}'")

        await asyncio.to_thread(_delete_sync)

    async def cleanup_old_entries(
        self,
        max_age_seconds: int = 30 * 24 * 60 * 60,  # 30 days default
    ) -> int:
        """Remove entries older than the specified age.

        Args:
            max_age_seconds: Maximum age in seconds (default 30 days)

        Returns:
            Number of entries removed
        """
        await self._ensure_table()

        def _cleanup_sync():
            self._lazy_init_engine()
            with self._engine_manager.engine.begin() as conn:
                result = conn.execute(
                    text("""
                        DELETE FROM oauth_clients
                        WHERE updated_at < CURRENT_TIMESTAMP
                            - make_interval(secs => :seconds)
                        RETURNING key
                    """),
                    {"seconds": max_age_seconds}
                )
                removed_count = result.rowcount

            if removed_count > 0:
                logger.info(
                    f"Cleaned up {removed_count} old OAuth client entries"
                )

            return removed_count

        return await asyncio.to_thread(_cleanup_sync)

    async def close(self):
        """Close database connections."""
        if self._engine_manager:
            await asyncio.to_thread(self._engine_manager.close)
