"""Unit tests for vector store backend selection."""

from unittest.mock import Mock, patch, AsyncMock
import pytest

from src.storage import vector_store


class TestBackendSelection:
    """Test backend factory selection logic."""

    @patch('src.storage.vector_store.app_config.get_vector_backend')
    async def test_default_to_legacy_backend(self, mock_get_backend):
        """Test that legacy backend is default."""
        # Arrange
        mock_get_backend.return_value = "legacy"
        vector_store._default_vector_store = None

        # Act
        store = await vector_store.get_default_vector_store()

        # Assert
        assert isinstance(store, vector_store.VectorStoreService)
        assert not isinstance(store, vector_store._PostgresVectorFacade)

    @patch('src.storage.vector_store.app_config.get_vector_backend')
    async def test_select_postgres_backend(self, mock_get_backend):
        """Test postgres backend selection."""
        # Arrange
        mock_get_backend.return_value = "postgres"
        vector_store._default_vector_store = None

        # Act
        store = await vector_store.get_default_vector_store()

        # Assert
        assert isinstance(store, vector_store._PostgresVectorFacade)

    @patch('src.storage.vector_store.app_config.get_vector_backend')
    async def test_singleton_pattern_legacy(self, mock_get_backend):
        """Test that legacy backend returns same instance."""
        # Arrange
        mock_get_backend.return_value = "legacy"
        vector_store._default_vector_store = None

        # Act
        store1 = await vector_store.get_default_vector_store()
        store2 = await vector_store.get_default_vector_store()

        # Assert
        assert store1 is store2

    @patch('src.storage.vector_store.app_config.get_vector_backend')
    async def test_singleton_pattern_postgres(self, mock_get_backend):
        """Test that postgres backend returns same instance."""
        # Arrange
        mock_get_backend.return_value = "postgres"
        vector_store._default_vector_store = None

        # Act
        store1 = await vector_store.get_default_vector_store()
        store2 = await vector_store.get_default_vector_store()

        # Assert
        assert store1 is store2


class TestPostgresFacade:
    """Test _PostgresVectorFacade adapter."""

    @patch('src.storage.vector_store._PGStore')
    def test_facade_lazy_init(self, mock_pgstore_class):
        """Test facade defers initialization until first use."""
        # Arrange
        mock_store = Mock()
        mock_pgstore_class.return_value = mock_store

        # Act
        facade = vector_store._PostgresVectorFacade()

        # Assert - store not created until _ensure_store called
        assert facade._store is None
        mock_pgstore_class.assert_not_called()

        # Act - trigger init
        facade._ensure_store()

        # Assert - now created
        mock_pgstore_class.assert_called_once_with(connection=None)
        assert facade._store is mock_store

    @patch('src.storage.vector_store._PGStore')
    @pytest.mark.asyncio
    async def test_facade_add_chunks(self, mock_pgstore_class):
        """Test facade passes through add_chunks correctly."""
        # Arrange
        mock_store = Mock()
        mock_store.add_chunks = AsyncMock(return_value=["id1", "id2"])
        mock_pgstore_class.return_value = mock_store

        facade = vector_store._PostgresVectorFacade()
        texts = ["chunk1", "chunk2"]
        metadatas = [{"idx": 0}, {"idx": 1}]

        # Act
        result = await facade.add_chunks(
            texts=texts,
            metadatas=metadatas,
            speech_id="speech-123"
        )

        # Assert
        assert result == ["id1", "id2"]
        mock_store.add_chunks.assert_called_once_with(
            texts=texts,
            metadatas=metadatas
        )
        # Verify speech_id was added to metadata
        assert metadatas[0]["speech_id"] == "speech-123"
        assert metadatas[1]["speech_id"] == "speech-123"

    @patch('src.storage.vector_store._PGStore')
    @pytest.mark.asyncio
    async def test_facade_similarity_search(self, mock_pgstore_class):
        """Test facade passes through similarity search."""
        # Arrange
        mock_doc1 = Mock()
        mock_doc1.id = "id1"
        mock_doc1.page_content = "content1"
        mock_doc1.metadata = {"key": "val1"}

        mock_doc2 = Mock()
        mock_doc2.id = "id2"
        mock_doc2.page_content = "content2"
        mock_doc2.metadata = {"key": "val2"}

        mock_store = Mock()
        mock_store.similarity_search = AsyncMock(
            return_value=[(mock_doc1, 0.95), (mock_doc2, 0.85)]
        )
        mock_pgstore_class.return_value = mock_store

        facade = vector_store._PostgresVectorFacade()

        # Act
        result = await facade.similarity_search(
            query="test query",
            k=5,
            filter={"year": "2024"}
        )

        # Assert
        assert len(result) == 2
        assert result[0]["chunk_id"] == "id1"
        assert result[0]["chunk_text"] == "content1"
        assert result[0]["score"] == 0.95
        assert result[0]["metadata"] == {"key": "val1"}

        mock_store.similarity_search.assert_called_once_with(
            query="test query",
            k=5,
            filter={"year": "2024"}
        )

    @patch('src.storage.vector_store._PGStore')
    @pytest.mark.asyncio
    async def test_facade_delete_by_speech_id(self, mock_pgstore_class):
        """Test facade passes through delete operation."""
        # Arrange
        mock_store = Mock()
        mock_store.delete = AsyncMock(return_value=5)
        mock_pgstore_class.return_value = mock_store

        facade = vector_store._PostgresVectorFacade()

        # Act
        result = await facade.delete_by_speech_id("speech-456")

        # Assert
        assert result == 5
        mock_store.delete.assert_called_once_with(
            filter={"speech_id": "speech-456"}
        )

    @patch('src.storage.vector_store._PGStore', None)
    def test_facade_fails_fast_if_backend_unavailable(self):
        """Test facade raises clear error if postgres backend not available."""
        # Arrange
        facade = vector_store._PostgresVectorFacade()

        # Act & Assert
        with pytest.raises(
            RuntimeError,
            match="langchain-postgres backend requested but not available"
        ):
            facade._ensure_store()

    @patch('src.storage.vector_store._PGStore')
    @pytest.mark.asyncio
    async def test_facade_empty_texts_returns_empty(self, mock_pgstore_class):
        """Test facade handles empty input gracefully."""
        # Arrange
        facade = vector_store._PostgresVectorFacade()

        # Act
        result = await facade.add_chunks(
            texts=[],
            metadatas=[],
            speech_id="speech-789"
        )

        # Assert
        assert result == []
        # Store should not be initialized for empty input
        mock_pgstore_class.assert_not_called()


class TestInvalidBackendValue:
    """Test invalid VECTOR_BACKEND value handling."""

    @patch('src.storage.vector_store.app_config.get_vector_backend')
    async def test_invalid_backend_fails_fast(self, mock_get_backend):
        """Test unknown backend values fail with clear error message.
        
        This is a critical safety feature - we want to fail immediately
        if VECTOR_BACKEND is misconfigured, rather than silently defaulting
        to a backend that might not be what the operator intended.
        """
        # Arrange
        mock_get_backend.return_value = "invalid_value"
        vector_store._default_vector_store = None

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await vector_store.get_default_vector_store()
        
        # Verify error message is clear and actionable
        error_msg = str(exc_info.value)
        assert "invalid_value" in error_msg
        assert "legacy" in error_msg
        assert "postgres" in error_msg
        assert "VECTOR_BACKEND" in error_msg

    @patch('src.storage.vector_store.app_config.get_vector_backend')
    async def test_empty_backend_fails_fast(self, mock_get_backend):
        """Test empty backend value fails with clear error."""
        # Arrange
        mock_get_backend.return_value = ""
        vector_store._default_vector_store = None

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await vector_store.get_default_vector_store()
        
        error_msg = str(exc_info.value)
        assert "VECTOR_BACKEND" in error_msg

    @patch('src.storage.vector_store.app_config.get_vector_backend')
    async def test_typo_postgres_fails_fast(self, mock_get_backend):
        """Test common typo 'postgress' fails with clear error."""
        # Arrange
        mock_get_backend.return_value = "postgress"  # Common typo
        vector_store._default_vector_store = None

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await vector_store.get_default_vector_store()
        
        error_msg = str(exc_info.value)
        assert "postgress" in error_msg
        assert "postgres" in error_msg  # Suggests correct value

    @patch('src.storage.vector_store.app_config.get_vector_backend')
    async def test_typo_legacy_fails_fast(self, mock_get_backend):
        """Test common typo 'legasy' fails with clear error."""
        # Arrange
        mock_get_backend.return_value = "legasy"  # Common typo
        vector_store._default_vector_store = None

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await vector_store.get_default_vector_store()
        
        error_msg = str(exc_info.value)
        assert "legasy" in error_msg
        assert "legacy" in error_msg  # Suggests correct value

    @patch('src.storage.vector_store.app_config.get_vector_backend')
    async def test_case_sensitive_postgres_fails(self, mock_get_backend):
        """Test that VECTOR_BACKEND is case-sensitive."""
        # Arrange
        mock_get_backend.return_value = "Postgres"  # Wrong case
        vector_store._default_vector_store = None

        # Act & Assert
        with pytest.raises(ValueError):
            await vector_store.get_default_vector_store()

    @patch('src.storage.vector_store.app_config.get_vector_backend')
    async def test_case_sensitive_legacy_fails(self, mock_get_backend):
        """Test that VECTOR_BACKEND is case-sensitive."""
        # Arrange
        mock_get_backend.return_value = "Legacy"  # Wrong case
        vector_store._default_vector_store = None

        # Act & Assert
        with pytest.raises(ValueError):
            await vector_store.get_default_vector_store()

    @patch('src.storage.vector_store.app_config.get_vector_backend')
    async def test_valid_legacy_succeeds(self, mock_get_backend):
        """Test that valid 'legacy' value succeeds."""
        # Arrange
        mock_get_backend.return_value = "legacy"
        vector_store._default_vector_store = None

        # Act
        store = await vector_store.get_default_vector_store()

        # Assert - no exception raised
        assert isinstance(store, vector_store.VectorStoreService)

    @patch('src.storage.vector_store.app_config.get_vector_backend')
    async def test_valid_postgres_succeeds(self, mock_get_backend):
        """Test that valid 'postgres' value succeeds."""
        # Arrange
        mock_get_backend.return_value = "postgres"
        vector_store._default_vector_store = None

        # Act
        store = await vector_store.get_default_vector_store()

        # Assert - no exception raised
        assert isinstance(store, vector_store._PostgresVectorFacade)


class TestStartupValidation:
    """Test startup validation behavior for production safety."""

    @patch('src.storage.vector_store.app_config.get_vector_backend')
    async def test_misconfigured_backend_detected_at_startup(
        self, mock_get_backend
    ):
        """Test that misconfiguration is detected immediately on first call.
        
        In production, this would happen during application startup,
        failing fast before accepting any requests.
        """
        # Arrange - simulate misconfigured environment
        mock_get_backend.return_value = "prod"  # Operator error
        vector_store._default_vector_store = None

        # Act & Assert - fails on first access
        with pytest.raises(ValueError) as exc_info:
            await vector_store.get_default_vector_store()
        
        # Error message guides operator to fix configuration
        error_msg = str(exc_info.value)
        assert "Invalid VECTOR_BACKEND" in error_msg
        assert "'prod'" in error_msg
        assert "legacy" in error_msg or "postgres" in error_msg

    @patch('src.storage.vector_store.app_config.get_vector_backend')
    async def test_error_message_includes_valid_options(
        self, mock_get_backend
    ):
        """Test that error message clearly lists valid options."""
        # Arrange
        mock_get_backend.return_value = "unknown"
        vector_store._default_vector_store = None

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await vector_store.get_default_vector_store()
        
        error_msg = str(exc_info.value).lower()
        # Should list both valid options
        assert "legacy" in error_msg
        assert "postgres" in error_msg
        # Should indicate it's an environment variable
        assert "vector_backend" in error_msg
