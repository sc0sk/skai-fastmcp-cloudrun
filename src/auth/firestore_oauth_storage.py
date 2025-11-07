"""
Firestore-backed AsyncKeyValue store for FastMCP OAuth client storage.

Uses Google Cloud Firestore for persistent, serverless OAuth client storage.
Perfect for Cloud Run deployments - no connection pooling or event loop issues.
"""

import logging
from typing import Optional
from google.cloud import firestore

logger = logging.getLogger(__name__)


class FirestoreOAuthStorage:
    """
    Firestore-backed storage for FastMCP OAuth clients.

    Implements the AsyncKeyValue protocol required by FastMCP 2.13+.
    Stores OAuth client data in Firestore collection 'oauth_clients'.

    Benefits:
    - No event loop issues (HTTP/gRPC API)
    - Automatic IAM authentication
    - Built for serverless (Cloud Run, Cloud Functions)
    - Persistent across container restarts
    - Auto-scaling and high availability
    """

    def __init__(self, project_id: Optional[str] = None, collection_name: str = "oauth_clients"):
        """
        Initialize Firestore OAuth storage.

        Args:
            project_id: GCP project ID (optional, uses default from environment)
            collection_name: Firestore collection name for OAuth clients
        """
        self.project_id = project_id
        self.collection_name = collection_name
        self.db = firestore.AsyncClient(project=project_id)
        self.collection = self.db.collection(collection_name)
        logger.info(f"Initialized Firestore OAuth storage (collection: {collection_name})")

    async def get(self, key: str, default: Optional[bytes] = None, collection: Optional[str] = None) -> Optional[bytes]:
        """
        Retrieve OAuth client data by key.

        Args:
            key: Client identifier (document ID)
            default: Default value if key not found
            collection: Collection name (ignored, uses configured collection)

        Returns:
            Stored bytes value or default
        """
        try:
            doc_ref = self.collection.document(key)
            doc = await doc_ref.get()

            if doc.exists:
                data = doc.to_dict()
                value = data.get('value')
                logger.debug(f"Retrieved OAuth client: {key}")
                return value if isinstance(value, bytes) else default

            logger.debug(f"OAuth client not found: {key}")
            return default

        except Exception as e:
            logger.error(f"Failed to get OAuth client {key}: {e}")
            return default

    async def set(self, key: str, value: bytes) -> None:
        """
        Store OAuth client data.

        Args:
            key: Client identifier (document ID)
            value: OAuth client data (bytes)
        """
        try:
            doc_ref = self.collection.document(key)
            await doc_ref.set({
                'value': value,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            logger.info(f"Stored OAuth client: {key}")

        except Exception as e:
            logger.error(f"Failed to store OAuth client {key}: {e}")
            raise

    async def put(self, key: str, value: bytes, collection: Optional[str] = None, ttl: Optional[int] = None) -> None:
        """
        Store OAuth client data (PydanticAdapter compatibility).

        Args:
            key: Client identifier (document ID)
            value: OAuth client data (bytes)
            collection: Collection name (ignored, uses configured collection)
            ttl: Time-to-live in seconds (not supported, ignored)
        """
        await self.set(key, value)

    async def delete(self, key: str) -> None:
        """
        Delete OAuth client data.

        Args:
            key: Client identifier to delete
        """
        try:
            doc_ref = self.collection.document(key)
            await doc_ref.delete()
            logger.info(f"Deleted OAuth client: {key}")

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
        try:
            doc_ref = self.collection.document(key)
            doc = await doc_ref.get()
            return doc.exists

        except Exception as e:
            logger.error(f"Failed to check existence of OAuth client {key}: {e}")
            return False

    async def keys(self, prefix: str = "") -> list[str]:
        """
        List all keys matching a prefix.

        Args:
            prefix: Key prefix to filter by

        Returns:
            List of matching keys (document IDs)
        """
        try:
            # Query all documents in collection
            docs = self.collection.stream()

            keys = []
            async for doc in docs:
                doc_id = doc.id
                if not prefix or doc_id.startswith(prefix):
                    keys.append(doc_id)

            logger.debug(f"Listed {len(keys)} OAuth clients with prefix '{prefix}'")
            return keys

        except Exception as e:
            logger.error(f"Failed to list OAuth clients with prefix {prefix}: {e}")
            return []

    async def close(self) -> None:
        """Close the Firestore client."""
        try:
            await self.db.close()
            logger.info("Closed Firestore client")
        except Exception as e:
            logger.warning(f"Error closing Firestore client: {e}")
