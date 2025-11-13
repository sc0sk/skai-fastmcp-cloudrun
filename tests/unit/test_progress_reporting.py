"""Unit tests for progress reporting in MCP tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date
from fastmcp import Context

from tools.ingest import ingest_hansard_speech
from storage.vector_store import VectorStoreService
from storage.metadata_store import MetadataStore
from models.speech import SpeechMetadata


@pytest.fixture
def mock_context():
    """Create a mock FastMCP Context for testing."""
    ctx = MagicMock(spec=Context)
    ctx.report_progress = AsyncMock()
    ctx.info = AsyncMock()
    return ctx


@pytest.fixture
def sample_speech_data():
    """Create sample speech data for testing."""
    return {
        "title": "Test Budget Speech 2024",
        "speaker": "Simon Kennedy",
        "party": "Liberal",
        "chamber": "House of Representatives",
        "electorate": "Cook",
        "state": "NSW",
        "date": "2024-06-03",
        "hansard_reference": "House Hansard, 3 June 2024, p.145",
        "full_text": "Mr Speaker, I rise to speak on the Budget measures announced yesterday. " * 50,  # Long enough to chunk
        "topic_tags": ["budget", "economy"],
        "source_url": "https://www.aph.gov.au/test",
    }


@pytest.mark.asyncio
async def test_ingest_with_progress_context(mock_context, sample_speech_data):
    """Verify progress reported at correct milestones when ctx provided."""
    # Mock the storage services
    with patch('tools.ingestion_utils.get_default_metadata_store') as mock_metadata, \
         patch('tools.ingestion_utils.get_default_vector_store') as mock_vector:

        # Setup mocks
        mock_metadata_store = AsyncMock()
        mock_metadata_store.add_speech = AsyncMock(return_value="test-speech-id-123")
        mock_metadata.return_value = mock_metadata_store

        mock_vector_store = AsyncMock()
        mock_vector_store.add_chunks = AsyncMock(return_value=["chunk-1", "chunk-2", "chunk-3"])
        mock_vector.return_value = mock_vector_store

        # Execute ingest with progress context
        result = await ingest_hansard_speech(
            speech_data=sample_speech_data,
            generate_embeddings=True,
            ctx=mock_context
        )

        # Verify result
        assert result["status"] == "success"
        assert result["speech_id"] == "test-speech-id-123"
        assert result["chunk_count"] > 0

        # Verify progress calls were made
        assert mock_context.report_progress.call_count >= 5

        # Verify progress sequence (at least start and end)
        calls = [call[0][0] for call in mock_context.report_progress.call_args_list]
        assert 0 in calls  # Start at 0%
        assert 100 in calls  # End at 100%

        # Verify all progress values in range 0-100
        for progress in calls:
            assert 0 <= progress <= 100


@pytest.mark.asyncio
async def test_ingest_without_progress_context(sample_speech_data):
    """Verify tool works correctly when ctx=None (backward compatibility)."""
    # Mock the storage services
    with patch('tools.ingestion_utils.get_default_metadata_store') as mock_metadata, \
         patch('tools.ingestion_utils.get_default_vector_store') as mock_vector:

        # Setup mocks
        mock_metadata_store = AsyncMock()
        mock_metadata_store.add_speech = AsyncMock(return_value="test-speech-id-456")
        mock_metadata.return_value = mock_metadata_store

        mock_vector_store = AsyncMock()
        mock_vector_store.add_chunks = AsyncMock(return_value=["chunk-1", "chunk-2"])
        mock_vector.return_value = mock_vector_store

        # Execute without context (backward compatibility)
        result = await ingest_hansard_speech(
            speech_data=sample_speech_data,
            generate_embeddings=True,
            ctx=None
        )

        # Should complete successfully without errors
        assert result["status"] == "success"
        assert result["speech_id"] == "test-speech-id-456"


@pytest.mark.asyncio
async def test_progress_stages_reported(mock_context, sample_speech_data):
    """Verify all expected progress stages are reported."""
    # Mock the storage services
    with patch('tools.ingestion_utils.get_default_metadata_store') as mock_metadata, \
         patch('tools.ingestion_utils.get_default_vector_store') as mock_vector:

        # Setup mocks
        mock_metadata_store = AsyncMock()
        mock_metadata_store.add_speech = AsyncMock(return_value="test-speech-id-789")
        mock_metadata.return_value = mock_metadata_store

        mock_vector_store = AsyncMock()
        mock_vector_store.add_chunks = AsyncMock(return_value=["chunk-1"])
        mock_vector.return_value = mock_vector_store

        # Execute ingest
        await ingest_hansard_speech(
            speech_data=sample_speech_data,
            ctx=mock_context
        )

        # Extract progress values
        calls = [call[0][0] for call in mock_context.report_progress.call_args_list]

        # Verify stage boundaries present
        assert 0 in calls  # Validation start
        assert any(15 <= p <= 25 for p in calls)  # Chunking start (~20%)
        assert any(35 <= p <= 45 for p in calls)  # Embedding start (~40%)
        assert any(85 <= p <= 95 for p in calls)  # Metadata start (~90%)
        assert 100 in calls  # Completion

        # Verify info messages were sent
        assert mock_context.info.call_count >= 4


@pytest.mark.asyncio
async def test_final_progress_is_100(mock_context, sample_speech_data):
    """Verify 100% progress reported on successful completion."""
    # Mock the storage services
    with patch('tools.ingestion_utils.get_default_metadata_store') as mock_metadata, \
         patch('tools.ingestion_utils.get_default_vector_store') as mock_vector:

        # Setup mocks
        mock_metadata_store = AsyncMock()
        mock_metadata_store.add_speech = AsyncMock(return_value="test-speech-id-final")
        mock_metadata.return_value = mock_metadata_store

        mock_vector_store = AsyncMock()
        mock_vector_store.add_chunks = AsyncMock(return_value=["chunk-1"])
        mock_vector.return_value = mock_vector_store

        # Execute ingest
        result = await ingest_hansard_speech(
            speech_data=sample_speech_data,
            ctx=mock_context
        )

        assert result["status"] == "success"

        # Last progress call must be 100%
        last_call = mock_context.report_progress.call_args_list[-1]
        assert last_call[0][0] == 100


@pytest.mark.asyncio
async def test_progress_not_100_on_error(mock_context):
    """Verify 100% NOT reported when operation fails."""
    invalid_data = {"invalid": "missing required fields"}

    # Execute with invalid data (should fail validation)
    result = await ingest_hansard_speech(
        speech_data=invalid_data,
        ctx=mock_context
    )

    # Should return error status
    assert result["status"] == "error"
    assert "Validation error" in result["message"]

    # Progress may be called (validation stage), but NOT 100%
    if mock_context.report_progress.called:
        calls = [call[0][0] for call in mock_context.report_progress.call_args_list]
        assert 100 not in calls


@pytest.mark.asyncio
async def test_vector_store_progress_frequency(mock_context):
    """Verify embedding stage reports progress at reasonable intervals."""
    # Create a real VectorStoreService instance with mocked internals
    with patch('storage.vector_store.PostgresEngine') as mock_engine, \
         patch('storage.vector_store.PostgresVectorStore') as mock_vs:

        # Mock vector store
        mock_vs_instance = AsyncMock()
        mock_vs_instance.aadd_texts = AsyncMock(return_value=["id1", "id2", "id3"])
        mock_vs.create = AsyncMock(return_value=mock_vs_instance)

        # Mock engine
        mock_engine_instance = AsyncMock()
        mock_engine_instance.ainit_vectorstore_table = AsyncMock()
        mock_engine.afrom_instance = AsyncMock(return_value=mock_engine_instance)

        # Create service and add chunks
        vector_store = VectorStoreService()
        texts = [f"Chunk {i}" for i in range(30)]
        metadatas = [{"speaker": "Kennedy", "chunk_index": i} for i in range(30)]

        await vector_store.add_chunks(texts, metadatas, "speech-123", ctx=mock_context)

        # Should report at least 2 times (start=40%, end=70%)
        assert mock_context.report_progress.call_count >= 2

        # Verify progress values are in embedding range (40-70%)
        for call in mock_context.report_progress.call_args_list:
            progress = call[0][0]
            assert 40 <= progress <= 70


@pytest.mark.asyncio
async def test_metadata_store_progress():
    """Verify metadata store reports progress at 90% and 100%."""
    mock_context = MagicMock(spec=Context)
    mock_context.report_progress = AsyncMock()
    mock_context.info = AsyncMock()

    # Mock the connection
    with patch.object(MetadataStore, '_get_connection') as mock_conn_method:
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(side_effect=[None, "test-uuid-123"])  # First call checks duplicate, second returns ID
        mock_conn.close = AsyncMock()
        mock_conn_method.return_value = mock_conn

        store = MetadataStore()
        speech = SpeechMetadata(
            title="Test Speech",
            full_text="Content..." * 100,
            speaker="Simon Kennedy",
            party="Liberal",
            chamber="House of Representatives",
            electorate="Cook",
            state="NSW",
            date=date(2024, 6, 3),
            hansard_reference="Test Reference"
        )

        speech_id = await store.add_speech(speech, ctx=mock_context)

        # Verify speech_id returned
        assert speech_id == "test-uuid-123"

        # Verify 90% and 100% reported
        assert mock_context.report_progress.call_count == 2
        calls = [call[0][0] for call in mock_context.report_progress.call_args_list]
        assert 90 in calls
        assert 100 in calls


@pytest.mark.asyncio
async def test_ingest_without_embeddings(mock_context, sample_speech_data):
    """Verify ingest works with generate_embeddings=False."""
    # Mock the storage services
    with patch('tools.ingestion_utils.get_default_metadata_store') as mock_metadata, \
         patch('tools.ingestion_utils.get_default_vector_store') as mock_vector:

        # Setup mocks
        mock_metadata_store = AsyncMock()
        mock_metadata_store.add_speech = AsyncMock(return_value="test-speech-no-embed")
        mock_metadata.return_value = mock_metadata_store

        mock_vector_store = AsyncMock()
        mock_vector.return_value = mock_vector_store

        # Execute without embeddings
        result = await ingest_hansard_speech(
            speech_data=sample_speech_data,
            generate_embeddings=False,
            ctx=mock_context
        )

        # Should complete successfully
        assert result["status"] == "success"
        assert result["speech_id"] == "test-speech-no-embed"
        assert result["chunk_ids"] == []

        # Vector store should NOT be called
        mock_vector_store.add_chunks.assert_not_called()

        # Progress should still be reported
        assert mock_context.report_progress.called


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
