"""
Firestore-backed OAuth storage for FastMCP GitHub Provider.

This module patches FastMCP 2.12.5's GitHubProvider to use Cloud Firestore
instead of disk-based storage, ensuring OAuth clients persist across Cloud Run
container restarts.

Usage:
    from src.auth.firestore_oauth_patch import patch_github_provider_storage
    from fastmcp.server.auth.providers.github import GitHubProvider

    auth_provider = GitHubProvider()
    patch_github_provider_storage(auth_provider)
"""
import json
import logging
from typing import Dict, Optional
from google.cloud import firestore

logger = logging.getLogger(__name__)


class FirestoreOAuthStorage:
    """
    Cloud Firestore storage adapter for FastMCP OAuth clients.

    Stores OAuth client registrations in Firestore collection: oauth_clients
    Each document has:
    - Document ID: client ID (e.g., "abc123")
    - Fields: client_data (dict), created_at (timestamp)

    This persists OAuth clients across Cloud Run container restarts.
    """

    def __init__(self, project_id: Optional[str] = None, collection_name: str = "oauth_clients"):
        """
        Initialize Firestore OAuth storage.

        Args:
            project_id: GCP project ID (defaults to current project)
            collection_name: Firestore collection name (default: "oauth_clients")
        """
        self.db = firestore.Client(project=project_id)
        self.collection = self.db.collection(collection_name)
        logger.info(f"Initialized Firestore OAuth storage (collection: {collection_name})")

    def get(self, key: str) -> Optional[str]:
        """
        Retrieve OAuth client data by key (synchronous).

        Args:
            key: Client identifier

        Returns:
            JSON string of client data or None if not found
        """
        try:
            doc = self.collection.document(key).get()
            if doc.exists:
                data = doc.to_dict()
                # Return the stored JSON string
                value = data.get("value")
                logger.debug(f"Retrieved OAuth client from Firestore: {key}")
                return value

            logger.debug(f"OAuth client not found in Firestore: {key}")
            return None

        except Exception as e:
            logger.error(f"Failed to get OAuth client {key} from Firestore: {e}")
            return None

    def set(self, key: str, value: str) -> None:
        """
        Store OAuth client data (synchronous).

        Args:
            key: Client identifier
            value: JSON string of client data
        """
        try:
            self.collection.document(key).set({
                "value": value,
                "created_at": firestore.SERVER_TIMESTAMP,
            }, merge=True)

            logger.info(f"Stored OAuth client in Firestore: {key}")

        except Exception as e:
            logger.error(f"Failed to store OAuth client {key} in Firestore: {e}")
            raise

    def delete(self, key: str) -> None:
        """
        Delete OAuth client data (synchronous).

        Args:
            key: Client identifier to delete
        """
        try:
            self.collection.document(key).delete()
            logger.info(f"Deleted OAuth client from Firestore: {key}")

        except Exception as e:
            logger.error(f"Failed to delete OAuth client {key} from Firestore: {e}")
            raise

    def list_keys(self, prefix: str = "") -> list[str]:
        """
        List all keys matching a prefix (synchronous).

        Args:
            prefix: Key prefix to filter by

        Returns:
            List of matching keys
        """
        try:
            docs = self.collection.stream()
            keys = []

            for doc in docs:
                if not prefix or doc.id.startswith(prefix):
                    keys.append(doc.id)

            logger.debug(f"Listed {len(keys)} OAuth clients from Firestore with prefix '{prefix}'")
            return keys

        except Exception as e:
            logger.error(f"Failed to list OAuth clients from Firestore with prefix {prefix}: {e}")
            return []


def patch_github_provider_storage(provider, project_id: Optional[str] = None):
    """
    Patch a GitHubProvider instance to use Firestore storage.

    This function monkey-patches the provider's internal storage dictionary
    to use Firestore instead of in-memory storage.

    Args:
        provider: GitHubProvider instance to patch
        project_id: GCP project ID (defaults to current project)

    Example:
        auth_provider = GitHubProvider()
        patch_github_provider_storage(auth_provider)
    """
    storage = FirestoreOAuthStorage(project_id=project_id)

    # Monkey-patch the provider's internal storage
    # GitHubProvider stores clients in a dict-like object
    # We replace it with our Firestore storage that has get/set/delete methods
    if hasattr(provider, '_clients'):
        # Replace the internal clients dict
        provider._clients = storage
        logger.info("Patched GitHubProvider to use Firestore storage")
    elif hasattr(provider, 'client_storage'):
        # Newer FastMCP versions use client_storage
        provider.client_storage = storage
        logger.info("Patched GitHubProvider.client_storage to use Firestore")
    else:
        logger.warning("Could not find storage attribute to patch in GitHubProvider")
