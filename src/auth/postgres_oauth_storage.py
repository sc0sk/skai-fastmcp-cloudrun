"""
PostgreSQL-backed OAuth client storage for FastMCP.

Stores OAuth client registrations in the PostgreSQL database to persist
across Cloud Run deployments (ephemeral containers).
"""
import json
import logging
from typing import Dict, Optional
from fastmcp.server.auth.kv_storage import KVStorage
from src.storage.cloud_sql_engine import get_db_connection

logger = logging.getLogger(__name__)


class PostgresOAuthStorage(KVStorage):
    """
    PostgreSQL implementation of FastMCP's KVStorage for OAuth clients.

    Stores OAuth client registrations in a dedicated table:
    - oauth_clients (key TEXT PRIMARY KEY, value JSONB, created_at TIMESTAMP)

    This persists OAuth clients across Cloud Run container restarts.
    """

    def __init__(self):
        """Initialize and ensure the oauth_clients table exists."""
        self._ensure_table_exists()
        logger.info("Initialized PostgreSQL OAuth storage")

    def _ensure_table_exists(self):
        """Create oauth_clients table if it doesn't exist."""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS oauth_clients (
                    key TEXT PRIMARY KEY,
                    value JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create index on created_at for cleanup queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_oauth_clients_created_at
                ON oauth_clients(created_at)
            """)

            conn.commit()
            cursor.close()
            conn.close()
            logger.info("OAuth clients table ready")

        except Exception as e:
            logger.error(f"Failed to create oauth_clients table: {e}")
            raise

    async def get(self, key: str) -> Optional[str]:
        """
        Retrieve OAuth client data by key.

        Args:
            key: Client identifier (e.g., "client:abc123")

        Returns:
            JSON string of client data or None if not found
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT value FROM oauth_clients WHERE key = %s",
                (key,)
            )

            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if row:
                # PostgreSQL JSONB returns dict, convert to JSON string
                value = json.dumps(row[0]) if isinstance(row[0], dict) else row[0]
                logger.debug(f"Retrieved OAuth client: {key}")
                return value

            logger.debug(f"OAuth client not found: {key}")
            return None

        except Exception as e:
            logger.error(f"Failed to get OAuth client {key}: {e}")
            return None

    async def set(self, key: str, value: str) -> None:
        """
        Store OAuth client data.

        Args:
            key: Client identifier (e.g., "client:abc123")
            value: JSON string of client data
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Parse JSON string to JSONB
            value_dict = json.loads(value) if isinstance(value, str) else value

            # Upsert: insert or update if exists
            cursor.execute("""
                INSERT INTO oauth_clients (key, value, updated_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (key)
                DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_at = CURRENT_TIMESTAMP
            """, (key, json.dumps(value_dict)))

            conn.commit()
            cursor.close()
            conn.close()

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
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("DELETE FROM oauth_clients WHERE key = %s", (key,))

            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"Deleted OAuth client: {key}")

        except Exception as e:
            logger.error(f"Failed to delete OAuth client {key}: {e}")
            raise

    async def list_keys(self, prefix: str = "") -> list[str]:
        """
        List all keys matching a prefix.

        Args:
            prefix: Key prefix to filter by (e.g., "client:")

        Returns:
            List of matching keys
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            if prefix:
                cursor.execute(
                    "SELECT key FROM oauth_clients WHERE key LIKE %s ORDER BY created_at DESC",
                    (f"{prefix}%",)
                )
            else:
                cursor.execute("SELECT key FROM oauth_clients ORDER BY created_at DESC")

            keys = [row[0] for row in cursor.fetchall()]

            cursor.close()
            conn.close()

            logger.debug(f"Listed {len(keys)} OAuth clients with prefix '{prefix}'")
            return keys

        except Exception as e:
            logger.error(f"Failed to list OAuth clients with prefix {prefix}: {e}")
            return []
