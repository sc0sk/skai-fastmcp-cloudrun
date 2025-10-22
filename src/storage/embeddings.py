"""Vertex AI embedding service using text-embedding-005."""

from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
from google.cloud import aiplatform
from typing import List
import os


class LangChainEmbeddingsWrapper:
    """
    Synchronous wrapper for LangChain PostgresVectorStore compatibility.

    LangChain's PostgresVectorStore calls embedding methods synchronously within an async context.
    This wrapper provides sync methods that directly call the underlying SDK (not async).
    """

    def __init__(self, project_id=None, location=None, model_name="text-embedding-005", output_dimensionality=768):
        """Initialize Vertex AI SDK directly for synchronous use."""
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        self.location = location or os.getenv("VERTEX_AI_LOCATION", "us-central1")
        self.model_name = model_name
        self.output_dimensionality = output_dimensionality

        # Initialize Vertex AI
        aiplatform.init(project=self.project_id, location=self.location)

        # Load the embedding model
        self.model = TextEmbeddingModel.from_pretrained(self.model_name)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Synchronous document embedding (called by LangChain PostgresVectorStore)."""
        if not texts:
            return []

        inputs = [TextEmbeddingInput(text=text, task_type="RETRIEVAL_DOCUMENT") for text in texts]
        embeddings = self.model.get_embeddings(inputs, output_dimensionality=self.output_dimensionality)
        return [embedding.values for embedding in embeddings]

    def embed_query(self, text: str) -> List[float]:
        """Synchronous query embedding (called by LangChain PostgresVectorStore)."""
        if not text or not text.strip():
            raise ValueError("Query text cannot be empty")

        inputs = [TextEmbeddingInput(text=text, task_type="RETRIEVAL_QUERY")]
        embeddings = self.model.get_embeddings(inputs, output_dimensionality=self.output_dimensionality)
        return embeddings[0].values


class EmbeddingService:
    """Service for generating embeddings using Vertex AI text-embedding-005."""

    def __init__(
        self,
        project_id: str = None,
        location: str = None,
        model_name: str = "text-embedding-005",
        task_type: str = "RETRIEVAL_DOCUMENT",
        output_dimensionality: int = 768,
    ):
        """
        Initialize Vertex AI embedding service.

        Args:
            project_id: GCP project ID (defaults to GCP_PROJECT_ID env var)
            location: Vertex AI location (defaults to VERTEX_AI_LOCATION env var)
            model_name: Embedding model (default: text-embedding-005)
            task_type: Task type for embeddings (default: RETRIEVAL_DOCUMENT)
            output_dimensionality: Vector dimensions (default: 768)

        Note:
            For queries, use task_type="RETRIEVAL_QUERY"
            For documents, use task_type="RETRIEVAL_DOCUMENT"
        """
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        self.location = location or os.getenv("VERTEX_AI_LOCATION", "us-central1")
        self.model_name = model_name
        self.task_type = task_type
        self.output_dimensionality = output_dimensionality

        # Initialize Vertex AI
        aiplatform.init(project=self.project_id, location=self.location)

        # Load the embedding model
        self.model = TextEmbeddingModel.from_pretrained(self.model_name)

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple documents (speech chunks).

        Args:
            texts: List of text chunks to embed

        Returns:
            List of 768-dimensional embedding vectors

        Example:
            >>> service = EmbeddingService()
            >>> chunks = ["Speech chunk 1...", "Speech chunk 2..."]
            >>> vectors = await service.embed_documents(chunks)
            >>> len(vectors[0])
            768
        """
        if not texts:
            return []

        # Create TextEmbeddingInput objects with task type
        inputs = [TextEmbeddingInput(text=text, task_type=self.task_type) for text in texts]

        # Generate embeddings with specified dimensionality
        embeddings = self.model.get_embeddings(
            inputs,
            output_dimensionality=self.output_dimensionality
        )

        # Extract embedding vectors
        return [embedding.values for embedding in embeddings]

    async def embed_query(self, text: str) -> List[float]:
        """
        Generate embedding for a search query.

        Args:
            text: Search query text

        Returns:
            768-dimensional embedding vector

        Note:
            Uses task_type="RETRIEVAL_QUERY" internally (different from documents)

        Example:
            >>> service = EmbeddingService()
            >>> query = "What did the speaker say about climate change?"
            >>> vector = await service.embed_query(query)
            >>> len(vector)
            768
        """
        if not text or not text.strip():
            raise ValueError("Query text cannot be empty")

        # Create input with RETRIEVAL_QUERY task type
        inputs = [TextEmbeddingInput(text=text, task_type="RETRIEVAL_QUERY")]

        # Generate embedding with specified dimensionality
        embeddings = self.model.get_embeddings(
            inputs,
            output_dimensionality=self.output_dimensionality
        )

        # Return the first (and only) embedding vector
        return embeddings[0].values

    def estimate_cost(self, num_chunks: int) -> dict:
        """
        Estimate embedding API costs.

        Args:
            num_chunks: Number of text chunks to embed

        Returns:
            Dict with cost estimate details

        Note:
            Vertex AI Embeddings pricing (as of 2024):
            - $0.00025 per 1,000 characters
            - Assume avg chunk size of 600 chars (800 max, some shorter)
        """
        avg_chunk_size = 600  # Conservative estimate
        total_chars = num_chunks * avg_chunk_size
        cost_per_1k_chars = 0.00025
        estimated_cost = (total_chars / 1000) * cost_per_1k_chars

        return {
            "num_chunks": num_chunks,
            "estimated_chars": total_chars,
            "estimated_cost_usd": round(estimated_cost, 4),
            "model": self.model_name,
            "dimensions": self.output_dimensionality,
        }


# Singleton instance with default configuration
default_embedding_service = EmbeddingService()


async def embed_speech_chunks(chunks: List[str]) -> List[List[float]]:
    """
    Convenience function to embed speech chunks with default configuration.

    Args:
        chunks: List of speech text chunks

    Returns:
        List of 768-dimensional embedding vectors

    Example:
        >>> from src.storage.embeddings import embed_speech_chunks
        >>> chunks = ["Chunk 1 text...", "Chunk 2 text..."]
        >>> vectors = await embed_speech_chunks(chunks)
        >>> all(len(v) == 768 for v in vectors)
        True
    """
    return await default_embedding_service.embed_documents(chunks)
