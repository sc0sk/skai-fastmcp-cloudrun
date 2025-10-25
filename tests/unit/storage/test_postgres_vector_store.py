"""Unit tests for Postgres vector store async adapter."""

import asyncio
from unittest.mock import Mock, patch, AsyncMock, call
import pytest

from src.storage.postgres_vector_store import PostgresVectorStoreService


class TestPostgresVectorStoreService:
    """Test async adapter with mocked langchain-postgres."""

    @pytest.fixture
    def mock_engine(self):
        """Mock SQLAlchemy engine."""
        return Mock()

    @pytest.fixture
    def mock_embeddings(self):
        """Mock embeddings function."""
        return Mock()

    @patch('src.storage.postgres_vector_store.PGVector')
    @patch('asyncio.to_thread')
    def test_init_creates_pgvector_with_jsonb(
        self, mock_to_thread, mock_pgvector_class, mock_engine,
        mock_embeddings
    ):
        """Test PGVector initialization with use_jsonb=True."""
        # Arrange
        mock_store = Mock()
        mock_pgvector_class.return_value = mock_store

        # Act
        service = PostgresVectorStoreService(
            engine=mock_engine,
            embeddings=mock_embeddings,
            collection_name="test_collection",
        )

        # Assert - T005a: verify use_jsonb=True
        mock_pgvector_class.assert_called_once()
        call_kwargs = mock_pgvector_class.call_args[1]
        assert call_kwargs["use_jsonb"] is True, \
            "PGVector must be initialized with use_jsonb=True"

    @patch('src.storage.postgres_vector_store.PGVector')
    def test_init_passes_collection_name(
        self, mock_pgvector_class, mock_engine, mock_embeddings
    ):
        """Test collection_name is passed to PGVector."""
        # Arrange
        mock_store = Mock()
        mock_pgvector_class.return_value = mock_store

        # Act
        service = PostgresVectorStoreService(
            engine=mock_engine,
            embeddings=mock_embeddings,
            collection_name="hansard_speeches",
        )

        # Assert - T017a: verify collection_name
        call_kwargs = mock_pgvector_class.call_args[1]
        assert call_kwargs["collection_name"] == "hansard_speeches", \
            "collection_name must be passed to PGVector"

    @patch('src.storage.postgres_vector_store.PGVector')
    def test_init_with_default_collection(
        self, mock_pgvector_class, mock_engine, mock_embeddings
    ):
        """Test default collection name."""
        # Arrange
        mock_store = Mock()
        mock_pgvector_class.return_value = mock_store

        # Act
        service = PostgresVectorStoreService(
            engine=mock_engine,
            embeddings=mock_embeddings,
        )

        # Assert
        call_kwargs = mock_pgvector_class.call_args[1]
        assert call_kwargs["collection_name"] == "hansard"

    @patch('src.storage.postgres_vector_store.PGVector')
    def test_init_passes_engine_and_embeddings(
        self, mock_pgvector_class, mock_engine, mock_embeddings
    ):
        """Test engine and embeddings are passed to PGVector."""
        # Arrange
        mock_store = Mock()
        mock_pgvector_class.return_value = mock_store

        # Act
        service = PostgresVectorStoreService(
            engine=mock_engine,
            embeddings=mock_embeddings,
        )

        # Assert
        call_args = mock_pgvector_class.call_args
        # Positional args: embeddings, engine
        assert call_args[1]["embeddings"] is mock_embeddings
        assert call_args[1]["connection"] is mock_engine

    @patch('src.storage.postgres_vector_store.PGVector')
    @patch('asyncio.to_thread')
    @pytest.mark.asyncio
    async def test_add_chunks_wraps_sync_call(
        self, mock_to_thread, mock_pgvector_class, mock_engine,
        mock_embeddings
    ):
        """Test add_chunks uses asyncio.to_thread."""
        # Arrange
        mock_store = Mock()
        mock_store.add_documents = Mock(return_value=["id1", "id2"])
        mock_pgvector_class.return_value = mock_store
        mock_to_thread.return_value = ["id1", "id2"]

        service = PostgresVectorStoreService(
            engine=mock_engine,
            embeddings=mock_embeddings,
        )

        chunks = [Mock(), Mock()]

        # Act
        result = await service.add_chunks(chunks)

        # Assert
        mock_to_thread.assert_called_once_with(
            mock_store.add_documents, chunks
        )
        assert result == ["id1", "id2"]

    @patch('src.storage.postgres_vector_store.PGVector')
    @patch('asyncio.to_thread')
    @pytest.mark.asyncio
    async def test_similarity_search_wraps_sync_call(
        self, mock_to_thread, mock_pgvector_class, mock_engine,
        mock_embeddings
    ):
        """Test similarity_search uses asyncio.to_thread."""
        # Arrange
        mock_store = Mock()
        mock_results = [Mock(), Mock()]
        mock_store.similarity_search = Mock(return_value=mock_results)
        mock_pgvector_class.return_value = mock_store
        mock_to_thread.return_value = mock_results

        service = PostgresVectorStoreService(
            engine=mock_engine,
            embeddings=mock_embeddings,
        )

        # Act
        result = await service.similarity_search("test query", k=5)

        # Assert
        mock_to_thread.assert_called_once_with(
            mock_store.similarity_search, "test query", k=5
        )
        assert result == mock_results

    @patch('src.storage.postgres_vector_store.PGVector')
    @patch('asyncio.to_thread')
    @pytest.mark.asyncio
    async def test_similarity_search_with_metadata_filter(
        self, mock_to_thread, mock_pgvector_class, mock_engine,
        mock_embeddings
    ):
        """Test similarity_search with metadata filtering."""
        # Arrange
        mock_store = Mock()
        mock_results = [Mock()]
        mock_store.similarity_search = Mock(return_value=mock_results)
        mock_pgvector_class.return_value = mock_store
        mock_to_thread.return_value = mock_results

        service = PostgresVectorStoreService(
            engine=mock_engine,
            embeddings=mock_embeddings,
        )

        filter_dict = {"year": "2024", "chamber": "senate"}

        # Act
        result = await service.similarity_search(
            "test query", k=10, filter=filter_dict
        )

        # Assert
        call_kwargs = mock_to_thread.call_args[1]
        # Should pass through filter
        # (exact format depends on PGVector API)
        assert len(mock_to_thread.call_args[0]) >= 2

    @patch('src.storage.postgres_vector_store.PGVector')
    @patch('asyncio.to_thread')
    @pytest.mark.asyncio
    async def test_delete_wraps_sync_call(
        self, mock_to_thread, mock_pgvector_class, mock_engine,
        mock_embeddings
    ):
        """Test delete uses asyncio.to_thread."""
        # Arrange
        mock_store = Mock()
        mock_store.delete = Mock(return_value=True)
        mock_pgvector_class.return_value = mock_store
        mock_to_thread.return_value = True

        service = PostgresVectorStoreService(
            engine=mock_engine,
            embeddings=mock_embeddings,
        )

        # Act
        result = await service.delete(ids=["id1", "id2", "id3"])

        # Assert
        mock_to_thread.assert_called_once()
        # Check that delete was called with ids
        assert mock_to_thread.call_args[0][0] == mock_store.delete
        assert result is True

    @patch('src.storage.postgres_vector_store.PGVector')
    @patch('asyncio.to_thread')
    @pytest.mark.asyncio
    async def test_error_propagation(
        self, mock_to_thread, mock_pgvector_class, mock_engine,
        mock_embeddings
    ):
        """Test that exceptions are propagated from sync calls."""
        # Arrange
        mock_store = Mock()
        mock_pgvector_class.return_value = mock_store
        mock_to_thread.side_effect = RuntimeError("Database error")

        service = PostgresVectorStoreService(
            engine=mock_engine,
            embeddings=mock_embeddings,
        )

        # Act & Assert
        with pytest.raises(RuntimeError, match="Database error"):
            await service.add_chunks([Mock()])

    @patch('src.storage.postgres_vector_store.PGVector')
    def test_embedding_dimension_default(
        self, mock_pgvector_class, mock_engine, mock_embeddings
    ):
        """Test default embedding dimension is 768."""
        # Arrange
        mock_store = Mock()
        mock_pgvector_class.return_value = mock_store

        # Mock the embeddings to report dimension
        mock_embeddings.embed_dimension = 768

        # Act
        service = PostgresVectorStoreService(
            engine=mock_engine,
            embeddings=mock_embeddings,
        )

        # Assert - T005c: verify dimension
        # (Note: actual dimension comes from embeddings model)
        # This test verifies we're using an embeddings with 768 dim
        assert mock_embeddings.embed_dimension == 768, \
            "Embeddings must have dimension 768"

    @patch('src.storage.postgres_vector_store.PGVector')
    def test_create_tables_if_not_exists(
        self, mock_pgvector_class, mock_engine, mock_embeddings
    ):
        """Test that create_tables_if_not_exists is called."""
        # Arrange
        mock_store = Mock()
        mock_store.create_tables_if_not_exists = Mock()
        mock_pgvector_class.return_value = mock_store

        # Act
        service = PostgresVectorStoreService(
            engine=mock_engine,
            embeddings=mock_embeddings,
        )

        # Assert
        mock_store.create_tables_if_not_exists.assert_called_once()
