"""PostgreSQL vector store using LangChain 1.0 with langchain-postgres.

This module provides vector storage via langchain-postgres PGVector backend.

Auth Modes:
- IAM (recommended): Set USE_IAM_AUTH=true to force IAM DB auth via
    Cloud SQL Connector (no passwords). In this mode, we do not pass
    user/password and rely on the service account.
- Password (legacy/local): Provide CLOUDSQL_USER and DATABASE_PASSWORD
    (or CLOUDSQL_PASSWORD for backward-compat) and leave USE_IAM_AUTH unset
    or false.
"""

from typing import List, Optional, Dict, Any
import os
from dotenv import load_dotenv
from fastmcp import Context
import logging

try:
    # Optional import; only required if VECTOR_BACKEND=postgres
    from src.storage.postgres_vector_store import PostgresVectorStoreService as _PGStore
except Exception:  # pragma: no cover - optional dependency path
    _PGStore = None  # type: ignore[assignment]

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


# Singleton instance with default configuration
_default_vector_store: Optional["_PostgresVectorFacade"] = None


async def get_default_vector_store() -> "_PostgresVectorFacade":
    """
    Get or create default vector store instance.

    Returns:
        Singleton _PostgresVectorFacade instance

    Example:
        >>> from src.storage.vector_store import get_default_vector_store
        >>> store = await get_default_vector_store()
        >>> results = await store.similarity_search("climate policy", k=5)
    """
    global _default_vector_store

    if _default_vector_store is None:
        _default_vector_store = _PostgresVectorFacade()
    return _default_vector_store


class _PostgresVectorFacade:
    """Facade implementing VectorStoreService-like API on top of langchain-postgres backend.

    Note: This defers actual PGVector initialization until first use.
    """

    def __init__(self) -> None:
        self._store = None

    def _ensure_store(self):
        if self._store is None:
            if _PGStore is None:
                raise RuntimeError(
                    "langchain-postgres backend requested but not available"
                )
            # Connection will be provided via environment/engine.
            # Determine auth mode (IAM vs Password) consistently with metadata_store
            use_iam_env = (os.getenv("USE_IAM_AUTH", "").strip().lower())
            use_iam = use_iam_env in ("1", "true", "yes")

            # Read credentials (legacy/local). Prefer DATABASE_PASSWORD; fallback CLOUDSQL_PASSWORD
            db_user = os.getenv("CLOUDSQL_USER")
            db_password = os.getenv("DATABASE_PASSWORD") or os.getenv("CLOUDSQL_PASSWORD")

            user = None
            password = None
            if not use_iam and db_user and db_password:
                user = db_user
                password = db_password
                logger.info("Vector store using password auth (legacy/local)")
            else:
                # Force IAM by clearing credentials
                logger.info("Vector store using IAM DB authentication via Cloud SQL Connector")

            self._store = _PGStore(
                project_id=os.getenv("GCP_PROJECT_ID"),
                region=os.getenv("GCP_REGION"),
                instance=os.getenv("CLOUDSQL_INSTANCE"),
                database=os.getenv("CLOUDSQL_DATABASE"),
                user=user,
                password=password,
            )

    async def add_chunks(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        speech_id: str,
        ctx: Optional[Context] = None,
    ) -> List[str]:
        if not texts:
            return []
        # Ensure speech_id is present
        for m in metadatas:
            m.setdefault("speech_id", speech_id)
        self._ensure_store()
        # Progress hooks minimal for now
        if ctx:
            await ctx.report_progress(40, 100)
        ids = await self._store.add_chunks(texts=texts, metadatas=metadatas)  # type: ignore[assignment]
        if ctx:
            await ctx.report_progress(70, 100)
        return ids

    async def similarity_search(
        self,
        query: str,
        k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        self._ensure_store()
        docs_scores = await self._store.similarity_search(query=query, k=k, filter=filter)  # type: ignore[union-attr]
        results: List[Dict[str, Any]] = []
        for doc, score in docs_scores:
            results.append(
                {
                    "chunk_id": getattr(doc, "id", None),
                    "chunk_text": getattr(doc, "page_content", None),
                    "score": float(score),
                    "metadata": getattr(doc, "metadata", {}),
                }
            )
        return results

    async def delete_by_speech_id(self, speech_id: str) -> int:
        self._ensure_store()
        return await self._store.delete(filter={"speech_id": speech_id})  # type: ignore[union-attr]

    async def get_stats(self) -> Dict[str, Any]:
        # TODO: implement real stats later
        return {
            "chunk_count": 0,
            "unique_speeches": 0,
            "avg_chunks_per_speech": 0.0,
        }

    async def close(self):
        self._store = None
