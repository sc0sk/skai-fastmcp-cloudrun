"""
PostgreSQL-backed AsyncKeyValue store using synchronous pg8000 driver.

Uses Unix socket connection with IAM token authentication to avoid
Cloud SQL Connector event loop issues.
"""

import logging
from typing import Optional
import asyncio

logger = logging.getLogger(__name__)


class PostgreSQLOAuthStorageSync:
    """
    PostgreSQL-backed storage for FastMCP OAuth clients using sync driver.

    Uses pg8000 (synchronous) instead of asyncpg to avoid event loop issues
    with Cloud SQL Connector in uvicorn/Cloud Run environments.
    """

    def __init__(self, project_id: str, region: str, instance: str, database: str, user: str):
        """
        Initialize PostgreSQL OAuth storage with sync operations.

        Args:
            project_id: GCP project ID
            region: Cloud SQL region
            instance: Cloud SQL instance name
            database: Database name
            user: Database user (for IAM auth)
        """
        self.project_id = project_id
        self.region = region
        self.instance = instance
        self.database = database
        self.user = user
        # Unix socket path for Cloud SQL (includes .s.PGSQL.5432)
        self.unix_socket = f"/cloudsql/{project_id}:{region}:{instance}/.s.PGSQL.5432"
        self._initialized = False
        logger.info(f"Initialized PostgreSQL OAuth storage (pg8000 via {self.unix_socket})")

    def _get_iam_token(self):
        """Get IAM access token for Cloud SQL."""
        import google.auth
        import google.auth.transport.requests

        credentials, _ = google.auth.default()
        # Request Cloud SQL scope
        if hasattr(credentials, 'refresh'):
            request = google.auth.transport.requests.Request()
            credentials.refresh(request)

        return credentials.token

    def _get_conn(self):
        """Get a database connection using pg8000 via Unix socket."""
        import pg8000

        # Get IAM token for password
        password = self._get_iam_token()

        # Connect via Unix socket with IAM token as password
        conn = pg8000.dbapi.connect(
            unix_sock=self.unix_socket,
            user=self.user,
            database=self.database,
            password=password,
        )
        return conn

    def _ensure_table_sync(self):
        """Ensure oauth_clients table exists (synchronous)."""
        if self._initialized:
            return

        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS oauth_clients (
                        client_id TEXT PRIMARY KEY,
                        value BYTEA NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_oauth_clients_created_at
                    ON oauth_clients(created_at)
                """)
                conn.commit()
                self._initialized = True
                logger.info("OAuth clients table ready")
            finally:
                cursor.close()
        finally:
            conn.close()

    async def _ensure_table(self):
        """Async wrapper for table creation."""
        await asyncio.to_thread(self._ensure_table_sync)

    async def get(self, key: str, default: Optional[bytes] = None, collection: Optional[str] = None) -> Optional[bytes]:
        """Retrieve OAuth client data by key."""
        await self._ensure_table()

        def _get_sync():
            conn = self._get_conn()
            try:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "SELECT value FROM oauth_clients WHERE client_id = %s",
                        (key,)
                    )
                    row = cursor.fetchone()
                    if row:
                        logger.debug(f"Retrieved OAuth client: {key}")
                        return bytes(row[0])
                    logger.debug(f"OAuth client not found: {key}")
                    return default
                finally:
                    cursor.close()
            finally:
                conn.close()

        try:
            return await asyncio.to_thread(_get_sync)
        except Exception as e:
            logger.error(f"Failed to get OAuth client {key}: {e}")
            return default

    async def set(self, key: str, value: bytes) -> None:
        """Store OAuth client data."""
        await self._ensure_table()

        def _set_sync():
            conn = self._get_conn()
            try:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        """
                        INSERT INTO oauth_clients (client_id, value, created_at, updated_at)
                        VALUES (%s, %s, NOW(), NOW())
                        ON CONFLICT (client_id)
                        DO UPDATE SET value = %s, updated_at = NOW()
                        """,
                        (key, value, value)
                    )
                    conn.commit()
                    logger.info(f"Stored OAuth client: {key}")
                finally:
                    cursor.close()
            finally:
                conn.close()

        try:
            await asyncio.to_thread(_set_sync)
        except Exception as e:
            logger.error(f"Failed to store OAuth client {key}: {e}")
            raise

    async def put(self, key: str, value: bytes, collection: Optional[str] = None, ttl: Optional[int] = None) -> None:
        """Store OAuth client data (PydanticAdapter compatibility)."""
        await self.set(key, value)

    async def delete(self, key: str) -> None:
        """Delete OAuth client data."""
        await self._ensure_table()

        def _delete_sync():
            conn = self._get_conn()
            try:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "DELETE FROM oauth_clients WHERE client_id = %s",
                        (key,)
                    )
                    conn.commit()
                    logger.info(f"Deleted OAuth client: {key}")
                finally:
                    cursor.close()
            finally:
                conn.close()

        try:
            await asyncio.to_thread(_delete_sync)
        except Exception as e:
            logger.error(f"Failed to delete OAuth client {key}: {e}")
            raise

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        await self._ensure_table()

        def _exists_sync():
            conn = self._get_conn()
            try:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "SELECT EXISTS(SELECT 1 FROM oauth_clients WHERE client_id = %s)",
                        (key,)
                    )
                    result = cursor.fetchone()
                    return bool(result[0]) if result else False
                finally:
                    cursor.close()
            finally:
                conn.close()

        try:
            return await asyncio.to_thread(_exists_sync)
        except Exception as e:
            logger.error(f"Failed to check existence of OAuth client {key}: {e}")
            return False

    async def keys(self, prefix: str = "") -> list[str]:
        """List all keys matching a prefix."""
        await self._ensure_table()

        def _keys_sync():
            conn = self._get_conn()
            try:
                cursor = conn.cursor()
                try:
                    if prefix:
                        cursor.execute(
                            "SELECT client_id FROM oauth_clients WHERE client_id LIKE %s ORDER BY created_at DESC",
                            (f"{prefix}%",)
                        )
                    else:
                        cursor.execute(
                            "SELECT client_id FROM oauth_clients ORDER BY created_at DESC"
                        )
                    rows = cursor.fetchall()
                    keys = [row[0] for row in rows]
                    logger.debug(f"Listed {len(keys)} OAuth clients with prefix '{prefix}'")
                    return keys
                finally:
                    cursor.close()
            finally:
                conn.close()

        try:
            return await asyncio.to_thread(_keys_sync)
        except Exception as e:
            logger.error(f"Failed to list OAuth clients with prefix {prefix}: {e}")
            return []

    async def close(self) -> None:
        """Close resources (no persistent connections)."""
        # No persistent connections to close
        pass
