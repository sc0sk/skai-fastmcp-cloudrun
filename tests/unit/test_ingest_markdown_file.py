"""Unit tests for ingest_markdown_file tool."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from tools.ingest_markdown_file import ingest_markdown_file


@pytest.mark.asyncio
async def test_ingest_file_success():
    """Test successful single file ingestion."""
    ctx = MagicMock()
    ctx.user = {"role": "admin"}
    
    with patch('tools.ingest_markdown_file.require_admin_role', new_callable=AsyncMock, return_value=True):
        with patch('tools.ingest_markdown_file.validate_file_path') as mock_validate:
            with patch('tools.ingest_markdown_file.parse_markdown_file') as mock_parse:
                with patch('tools.ingest_markdown_file.MetadataStore') as mock_metadata_cls:
                    with patch('tools.ingest_markdown_file.VectorStoreService') as mock_vector_cls:
                        # Setup mocks
                        mock_validate.return_value = "tests/fixtures/markdown/valid_speech.md"
                        
                        mock_metadata = MagicMock()
                        mock_metadata.speech_id = "test-001"
                        mock_metadata.speaker = "Test Speaker"
                        mock_metadata.party = "Labor"
                        mock_metadata.chamber = "REPS"
                        mock_metadata.date = "2024-01-01"
                        mock_metadata.title = "Test Title"
                        mock_metadata.state = None
                        mock_metadata.hansard_reference = None
                        mock_parse.return_value = (mock_metadata, "Test content with enough words to chunk properly")
                        
                        mock_store = MagicMock()
                        mock_store.check_speech_exists = AsyncMock(return_value=False)
                        mock_store.store_speech = AsyncMock(return_value="test-001")
                        mock_metadata_cls.return_value = mock_store
                        
                        mock_vector = MagicMock()
                        mock_vector.add_chunks = AsyncMock(return_value=["chunk1", "chunk2", "chunk3"])
                        mock_vector_cls.return_value = mock_vector
                        
                        result = await ingest_markdown_file(
                            file_path="tests/fixtures/markdown/valid_speech.md",
                            ctx=ctx
                        )
                        
                        assert result["status"] == "success"
                        assert result["speech_id"] == "test-001"
                        assert result["chunks_created"] > 0


@pytest.mark.asyncio
async def test_ingest_file_admin_required():
    """Test admin role enforcement."""
    ctx = MagicMock()
    ctx.user = {"role": "user"}
    
    with patch('tools.ingest_markdown_file.require_admin_role', new_callable=AsyncMock, side_effect=PermissionError("Admin required")):
        with pytest.raises(PermissionError, match="Admin required"):
            await ingest_markdown_file(
                file_path="test.md",
                ctx=ctx
            )


@pytest.mark.asyncio
async def test_ingest_file_duplicate_skip():
    """Test duplicate handling with skip policy."""
    ctx = MagicMock()
    ctx.user = {"role": "admin"}
    
    with patch('tools.ingest_markdown_file.require_admin_role', new_callable=AsyncMock, return_value=True):
        with patch('tools.ingest_markdown_file.validate_file_path'):
            with patch('tools.ingest_markdown_file.parse_markdown_file') as mock_parse:
                with patch('tools.ingest_markdown_file.MetadataStore') as mock_metadata_cls:
                    mock_metadata = MagicMock()
                    mock_metadata.speech_id = "test-001"
                    mock_parse.return_value = (mock_metadata, "Test content")
                    
                    mock_store = MagicMock()
                    mock_store.check_speech_exists = AsyncMock(return_value=True)
                    mock_metadata_cls.return_value = mock_store
                    
                    result = await ingest_markdown_file(
                        file_path="test.md",
                        duplicate_policy="skip",
                        ctx=ctx
                    )
                    
                    assert result["status"] == "skipped"
                    assert "already exists" in result["message"]


@pytest.mark.asyncio
async def test_ingest_file_duplicate_error():
    """Test duplicate handling with error policy."""
    ctx = MagicMock()
    ctx.user = {"role": "admin"}
    
    with patch('tools.ingest_markdown_file.require_admin_role', new_callable=AsyncMock, return_value=True):
        with patch('tools.ingest_markdown_file.validate_file_path'):
            with patch('tools.ingest_markdown_file.parse_markdown_file') as mock_parse:
                with patch('tools.ingest_markdown_file.MetadataStore') as mock_metadata_cls:
                    mock_metadata = MagicMock()
                    mock_metadata.speech_id = "test-001"
                    mock_parse.return_value = (mock_metadata, "Test content")
                    
                    mock_store = MagicMock()
                    mock_store.check_speech_exists = AsyncMock(return_value=True)
                    mock_metadata_cls.return_value = mock_store
                    
                    with pytest.raises(ValueError, match="already exists"):
                        await ingest_markdown_file(
                            file_path="test.md",
                            duplicate_policy="error",
                            ctx=ctx
                        )


@pytest.mark.asyncio
async def test_ingest_file_transaction_rollback():
    """Test transaction rollback on embedding failure."""
    ctx = MagicMock()
    ctx.user = {"role": "admin"}
    
    with patch('tools.ingest_markdown_file.require_admin_role', new_callable=AsyncMock, return_value=True):
        with patch('tools.ingest_markdown_file.validate_file_path'):
            with patch('tools.ingest_markdown_file.parse_markdown_file') as mock_parse:
                with patch('tools.ingest_markdown_file.MetadataStore') as mock_metadata_cls:
                    with patch('tools.ingest_markdown_file.VectorStoreService') as mock_vector_cls:
                        mock_metadata = MagicMock()
                        mock_metadata.speech_id = "test-001"
                        mock_metadata.speaker = "Test Speaker"
                        mock_metadata.party = "Labor"
                        mock_metadata.chamber = "REPS"
                        mock_metadata.date = "2024-01-01"
                        mock_metadata.title = "Test Title"
                        mock_metadata.state = None
                        mock_metadata.hansard_reference = None
                        mock_parse.return_value = (mock_metadata, "Test content")
                        
                        mock_store = MagicMock()
                        mock_store.check_speech_exists = AsyncMock(return_value=False)
                        mock_store.store_speech = AsyncMock(return_value="test-001")
                        mock_metadata_cls.return_value = mock_store
                        
                        mock_vector = MagicMock()
                        mock_vector.add_chunks = AsyncMock(side_effect=Exception("Embedding failed"))
                        mock_vector_cls.return_value = mock_vector
                        
                        with pytest.raises(Exception, match="Ingestion failed"):
                            await ingest_markdown_file(
                                file_path="test.md",
                                ctx=ctx
                            )
