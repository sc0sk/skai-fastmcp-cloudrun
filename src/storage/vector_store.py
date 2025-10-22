"""PostgreSQL vector store using LangChain PostgresVectorStore with pgvector."""

from langchain_google_cloud_sql_pg import PostgresVectorStore, PostgresEngine
from langchain_google_vertexai import VertexAIEmbeddings
from typing import List, Optional, Dict, Any
import os
import asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class VectorStoreService:
    """Service for managing speech chunks in PostgreSQL with pgvector."""

    def __init__(
        self,
        project_id: str = None,
        region: str = None,
        instance: str = None,
        database: str = None,
        user: str = None,
        password: str = None,
        embedding_service: Any = None,
        table_name: str = "speech_chunks",
    ):
        """
        Initialize PostgreSQL vector store with Cloud SQL connection.

        Args:
            project_id: GCP project ID (defaults to GCP_PROJECT_ID env var)
            region: Cloud SQL region (defaults to GCP_REGION env var)
            instance: Cloud SQL instance name (defaults to CLOUDSQL_INSTANCE env var)
            database: Database name (defaults to CLOUDSQL_DATABASE env var)
            user: Database user (defaults to CLOUDSQL_USER env var)
            password: Database password (defaults to DATABASE_PASSWORD env var, None for IAM)
            embedding_service: VertexAIEmbeddings instance (auto-created if None)
            table_name: Vector table name (default: speech_chunks)

        Note:
            Uses Cloud SQL Python Connector. Provide both user and password for basic auth,
            or neither for IAM authentication.
        """
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        self.region = region or os.getenv("GCP_REGION", "us-central1")
        self.instance = instance or os.getenv("CLOUDSQL_INSTANCE")
        self.database = database or os.getenv("CLOUDSQL_DATABASE", "hansard")
        self.user = user or os.getenv("CLOUDSQL_USER")  # None for IAM auth
        self.password = password or os.getenv("DATABASE_PASSWORD")  # None for IAM auth
        self.table_name = table_name

        # Create embedding service if not provided
        if embedding_service is None:
            from src.storage.embeddings import LangChainEmbeddingsWrapper
            # Use wrapper directly for LangChain PostgresVectorStore compatibility
            self.embeddings = LangChainEmbeddingsWrapper(
                project_id=self.project_id,
                location=os.getenv("VERTEX_AI_LOCATION", "us-central1"),
                model_name="text-embedding-005",
                output_dimensionality=768
            )
        else:
            # If provided a custom EmbeddingService, extract wrapper if available
            if hasattr(embedding_service, 'embeddings'):
                self.embeddings = embedding_service.embeddings
            else:
                self.embeddings = embedding_service

        # Store for lazy initialization
        self._vector_store: Optional[PostgresVectorStore] = None

    async def _get_vector_store(self) -> PostgresVectorStore:
        """
        Lazy initialization of PostgresVectorStore.

        Returns:
            Initialized PostgresVectorStore instance

        Note:
            Uses LangChain's default table structure with auto-initialization.
            Table is created automatically with proper schema if it doesn't exist.
        """
        if self._vector_store is None:
            # Determine auth method - for IAM auth, both user and password must be None
            # If only one is set, force both to None for IAM auth
            use_user = self.user if (self.user and self.password) else None
            use_password = self.password if (self.user and self.password) else None

            # Create PostgresEngine for Cloud SQL connection
            engine = await PostgresEngine.afrom_instance(
                project_id=self.project_id,
                region=self.region,
                instance=self.instance,
                database=self.database,
                user=use_user,
                password=use_password,
            )

            # Initialize table with proper schema (auto-creates if not exists)
            # This uses LangChain's standard column names: langchain_id, content, embedding, langchain_metadata
            await engine.ainit_vectorstore_table(
                table_name=self.table_name,
                vector_size=768,  # Match text-embedding-005 output
            )

            # Create PostgresVectorStore with LangChain defaults
            # This uses standard column names that match the initialized table
            self._vector_store = await PostgresVectorStore.create(
                engine=engine,
                table_name=self.table_name,
                embedding_service=self.embeddings,
            )

        return self._vector_store

    async def add_chunks(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        speech_id: str,
    ) -> List[str]:
        """
        Add speech chunks to vector store with embeddings.

        Args:
            texts: List of chunk texts
            metadatas: List of metadata dicts (one per chunk)
            speech_id: Parent speech ID (UUID)

        Returns:
            List of generated chunk IDs

        Example:
            >>> store = VectorStoreService()
            >>> chunks = ["Chunk 1 text...", "Chunk 2 text..."]
            >>> metadata = [
            ...     {"speech_id": "123", "chunk_index": 0, "speaker": "Kennedy"},
            ...     {"speech_id": "123", "chunk_index": 1, "speaker": "Kennedy"}
            ... ]
            >>> chunk_ids = await store.add_chunks(chunks, metadata, "123")
            >>> len(chunk_ids) == 2
            True
        """
        if not texts:
            return []

        if len(texts) != len(metadatas):
            raise ValueError("texts and metadatas must have same length")

        # Add speech_id to all metadata dicts and ensure date is a date object
        from datetime import date, datetime
        for meta in metadatas:
            meta["speech_id"] = speech_id

            # Convert date string to date object if needed
            if "date" in meta and isinstance(meta["date"], str):
                meta["date"] = datetime.fromisoformat(meta["date"]).date()

        vector_store = await self._get_vector_store()

        # Add documents with embeddings (LangChain handles embedding generation)
        chunk_ids = await vector_store.aadd_texts(
            texts=texts,
            metadatas=metadatas,
        )

        return chunk_ids

    async def similarity_search(
        self,
        query: str,
        k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using vector similarity.

        Args:
            query: Search query text
            k: Number of results to return (default: 10)
            filter: Optional metadata filter dict

        Returns:
            List of dicts with keys: chunk_id, chunk_text, score, metadata

        Example:
            >>> store = VectorStoreService()
            >>> results = await store.similarity_search(
            ...     query="climate change policy",
            ...     k=5,
            ...     filter={"chamber": "House of Representatives"}
            ... )
            >>> len(results) <= 5
            True
        """
        vector_store = await self._get_vector_store()

        # Perform similarity search with optional filter
        docs_with_scores = await vector_store.asimilarity_search_with_score(
            query=query,
            k=k,
            filter=filter,
        )

        # Format results
        # With LangChain defaults, metadata is stored in doc.metadata
        results = []
        for doc, score in docs_with_scores:
            results.append({
                "chunk_id": doc.id if hasattr(doc, 'id') else None,
                "chunk_text": doc.page_content,
                "score": float(score),
                "metadata": doc.metadata,
            })

        return results

    async def hybrid_search(
        self,
        query: str,
        k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
        keyword_weight: float = 0.3,
        vector_weight: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining vector similarity and keyword matching.

        Args:
            query: Search query text
            k: Number of results to return (default: 10)
            filter: Optional metadata filter dict
            keyword_weight: Weight for keyword score (default: 0.3)
            vector_weight: Weight for vector score (default: 0.7)

        Returns:
            List of dicts with combined scores

        Note:
            Uses pgvector's <=> operator for vector similarity
            Uses PostgreSQL full-text search for keyword matching
        """
        # TODO: Implement hybrid search in Phase 4
        # For now, fall back to vector-only search
        return await self.similarity_search(query=query, k=k, filter=filter)

    async def delete_by_speech_id(self, speech_id: str) -> int:
        """
        Delete all chunks for a given speech.

        Args:
            speech_id: Speech UUID to delete

        Returns:
            Number of chunks deleted

        Example:
            >>> store = VectorStoreService()
            >>> deleted = await store.delete_by_speech_id("speech-123")
            >>> deleted >= 0
            True
        """
        vector_store = await self._get_vector_store()

        # Delete by metadata filter
        deleted = await vector_store.adelete(
            filter={"speech_id": speech_id}
        )

        return deleted

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get vector store statistics.

        Returns:
            Dict with chunk_count, unique_speeches, avg_chunks_per_speech

        Example:
            >>> store = VectorStoreService()
            >>> stats = await store.get_stats()
            >>> "chunk_count" in stats
            True
        """
        # TODO: Implement stats query
        # For now, return placeholder
        return {
            "chunk_count": 0,
            "unique_speeches": 0,
            "avg_chunks_per_speech": 0.0,
        }

    async def close(self):
        """Close vector store connection."""
        if self._vector_store:
            # LangChain PostgresVectorStore handles cleanup
            self._vector_store = None


# Singleton instance with default configuration
_default_vector_store: Optional[VectorStoreService] = None


async def get_default_vector_store() -> VectorStoreService:
    """
    Get or create default vector store instance.

    Returns:
        Singleton VectorStoreService instance

    Example:
        >>> from src.storage.vector_store import get_default_vector_store
        >>> store = await get_default_vector_store()
        >>> results = await store.similarity_search("climate policy", k=5)
    """
    global _default_vector_store
    if _default_vector_store is None:
        _default_vector_store = VectorStoreService()
    return _default_vector_store
