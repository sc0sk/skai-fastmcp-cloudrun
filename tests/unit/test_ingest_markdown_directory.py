"""Unit tests for bulk markdown directory ingestion tool.

Feature 013: Bulk Markdown Directory Ingestion
"""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from tools.ingest_markdown_directory import ingest_markdown_directory


@pytest.fixture
def mock_ctx():
    """Create mock FastMCP context for testing."""
    ctx = AsyncMock()
    ctx.info = AsyncMock()
    ctx.report_progress = AsyncMock()
    return ctx


@pytest.mark.asyncio
async def test_directory_not_found():
    """Should raise FileNotFoundError for non-existent directory."""
    with pytest.raises(FileNotFoundError, match="Directory not found"):
        await ingest_markdown_directory(
            directory_path="/nonexistent/path/that/does/not/exist",
            ctx=None
        )


@pytest.mark.asyncio
async def test_path_not_directory(tmp_path):
    """Should raise ValueError if path is a file not directory."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("test")
    
    with pytest.raises(ValueError, match="not a directory"):
        await ingest_markdown_directory(
            directory_path=str(file_path),
            ctx=None
        )


@pytest.mark.asyncio
async def test_directory_not_readable(tmp_path):
    """Should raise PermissionError if directory not readable."""
    # Create directory and remove read permissions
    test_dir = tmp_path / "no_read_dir"
    test_dir.mkdir()
    
    # Note: In practice, permission errors may be OS-dependent
    # This test validates the check exists
    import os
    old_mode = test_dir.stat().st_mode
    try:
        os.chmod(test_dir, 0o000)
        with pytest.raises(PermissionError, match="not readable"):
            await ingest_markdown_directory(
                directory_path=str(test_dir),
                ctx=None
            )
    finally:
        # Restore permissions for cleanup
        os.chmod(test_dir, old_mode)


@pytest.mark.asyncio
async def test_discover_markdown_files(tmp_path):
    """Should discover all markdown files in directory."""
    # Create test markdown files
    (tmp_path / "file1.md").write_text("# Test 1")
    (tmp_path / "file2.md").write_text("# Test 2")
    (tmp_path / "file3.md").write_text("# Test 3")
    (tmp_path / "not_md.txt").write_text("Not markdown")
    
    # Mock ingest_markdown_file to avoid actual ingestion
    with patch('tools.ingest_markdown_directory.ingest_markdown_file') as mock_ingest:
        mock_ingest.return_value = {
            "status": "success",
            "speech_id": "test-id",
            "chunks_created": 5,
            "message": "Success"
        }
        
        result = await ingest_markdown_directory(
            directory_path=str(tmp_path),
            pattern="*.md",
            ctx=None
        )
        
        # Should have processed 3 markdown files
        assert mock_ingest.call_count == 3


@pytest.mark.asyncio
async def test_no_files_matching_pattern(tmp_path):
    """Should return empty result when no files match pattern."""
    # Create directory with non-matching file
    (tmp_path / "test.txt").write_text("test")
    
    result = await ingest_markdown_directory(
        directory_path=str(tmp_path),
        pattern="*.md",
        ctx=None
    )
    
    assert result["status"] == "complete"
    assert result["summary"]["total_files"] == 0
    assert "No files matched" in result["message"]


@pytest.mark.asyncio
async def test_exceeds_max_files_limit(tmp_path):
    """Should raise ValueError when file count exceeds max_files."""
    # Create 11 markdown files
    for i in range(11):
        (tmp_path / f"file{i:02d}.md").write_text("# Test")
    
    with pytest.raises(ValueError, match="Safety limit exceeded"):
        await ingest_markdown_directory(
            directory_path=str(tmp_path),
            max_files=10,
            ctx=None
        )


@pytest.mark.asyncio
@patch("tools.ingest_markdown_directory.ingest_markdown_file")
async def test_successful_batch(mock_ingest, tmp_path):
    """Should process all files successfully."""
    # Create test files
    for i in range(3):
        (tmp_path / f"speech{i}.md").write_text(f"# Speech {i}")
    
    # Mock successful ingestion
    mock_ingest.return_value = {
        "status": "success",
        "speech_id": "test-id",
        "chunks_created": 10,
        "message": "Success"
    }
    
    result = await ingest_markdown_directory(
        directory_path=str(tmp_path),
        pattern="*.md",
        ctx=None
    )
    
    assert result["status"] == "complete"
    assert result["summary"]["total_files"] == 3
    assert result["summary"]["succeeded"] == 3
    assert result["summary"]["failed"] == 0
    assert result["summary"]["total_chunks_created"] == 30
    assert len(result["successful_files"]) == 3
    assert len(result["failed_files"]) == 0


@pytest.mark.asyncio
@patch("tools.ingest_markdown_directory.ingest_markdown_file")
async def test_mixed_success_failure(mock_ingest, tmp_path):
    """Should handle mixed success and failure."""
    # Create test files
    for i in range(5):
        (tmp_path / f"speech{i}.md").write_text(f"# Speech {i}")
    
    # Mock: first 3 succeed, last 2 fail
    def side_effect(*args, **kwargs):
        file_path = kwargs.get("file_path") or args[0]
        if "speech4" in file_path:
            raise ValueError("Missing required field")
        elif "speech3" in file_path:
            raise FileNotFoundError("File not readable")
        else:
            return {
                "status": "success",
                "speech_id": f"test-{file_path}",
                "chunks_created": 8,
                "message": "Success"
            }
    
    mock_ingest.side_effect = side_effect
    
    result = await ingest_markdown_directory(
        directory_path=str(tmp_path),
        pattern="*.md",
        ctx=None
    )
    
    assert result["status"] == "complete"
    assert result["summary"]["total_files"] == 5
    assert result["summary"]["succeeded"] == 3
    assert result["summary"]["failed"] == 2
    assert result["summary"]["total_chunks_created"] == 24
    assert len(result["successful_files"]) == 3
    assert len(result["failed_files"]) == 2
    
    # Check error details
    failed = result["failed_files"]
    assert any(f["error_type"] == "ValueError" for f in failed)
    assert any(f["error_type"] == "FileNotFoundError" for f in failed)


@pytest.mark.asyncio
@patch("tools.ingest_markdown_directory.ingest_markdown_file")
async def test_duplicate_handling_skip(mock_ingest, tmp_path):
    """Test duplicate_policy='skip' skips duplicate files without error."""
    (tmp_path / "speech.md").write_text("# Test")
    
    mock_ingest.return_value = {
        "status": "skipped",
        "speech_id": "duplicate-id",
        "chunks_created": 0,
        "message": "Skipped duplicate"
    }
    
    result = await ingest_markdown_directory(
        directory_path=str(tmp_path),
        duplicate_policy="skip",
        ctx=None
    )
    
    assert result["summary"]["skipped"] == 1
    assert result["summary"]["succeeded"] == 0
    mock_ingest.assert_called_once()
    call_kwargs = mock_ingest.call_args[1]
    assert call_kwargs["duplicate_policy"] == "skip"


@pytest.mark.asyncio
@patch("tools.ingest_markdown_directory.ingest_markdown_file")
async def test_duplicate_handling_error(mock_ingest, tmp_path):
    """Test duplicate_policy='error' fails batch with clear error."""
    (tmp_path / "speech.md").write_text("# Test")
    
    mock_ingest.side_effect = ValueError("Duplicate speech_id found")
    
    result = await ingest_markdown_directory(
        directory_path=str(tmp_path),
        duplicate_policy="error",
        ctx=None
    )
    
    assert result["summary"]["failed"] == 1
    assert "ValueError" in result["failed_files"][0]["error_type"]
    mock_ingest.assert_called_once()
    call_kwargs = mock_ingest.call_args[1]
    assert call_kwargs["duplicate_policy"] == "error"


@pytest.mark.asyncio
@patch("tools.ingest_markdown_directory.ingest_markdown_file")
async def test_duplicate_handling_update(mock_ingest, tmp_path):
    """Test duplicate_policy='update' overwrites existing speech_id."""
    (tmp_path / "speech.md").write_text("# Test")
    
    mock_ingest.return_value = {
        "status": "success",
        "speech_id": "updated-id",
        "chunks_created": 5,
        "message": "Updated duplicate"
    }
    
    result = await ingest_markdown_directory(
        directory_path=str(tmp_path),
        duplicate_policy="update",
        ctx=None
    )
    
    assert result["summary"]["succeeded"] == 1
    assert result["summary"]["total_chunks_created"] == 5
    mock_ingest.assert_called_once()
    call_kwargs = mock_ingest.call_args[1]
    assert call_kwargs["duplicate_policy"] == "update"


@pytest.mark.asyncio
@patch("tools.ingest_markdown_directory.ingest_markdown_file")
async def test_summary_structure(mock_ingest, tmp_path):
    """Test summary has all required fields."""
    (tmp_path / "speech.md").write_text("# Test")
    
    mock_ingest.return_value = {
        "status": "success",
        "speech_id": "test-id",
        "chunks_created": 5,
        "message": "Success"
    }
    
    result = await ingest_markdown_directory(
        directory_path=str(tmp_path),
        ctx=None
    )
    
    # Verify structure
    assert "status" in result
    assert "summary" in result
    assert "successful_files" in result
    assert "failed_files" in result
    assert "message" in result
    
    # Verify summary fields
    summary = result["summary"]
    assert "total_files" in summary
    assert "succeeded" in summary
    assert "skipped" in summary
    assert "failed" in summary
    assert "total_chunks_created" in summary


@pytest.mark.asyncio
@patch("tools.ingest_markdown_directory.ingest_markdown_file")
async def test_chunk_aggregation(mock_ingest, tmp_path):
    """Test total_chunks_created sums correctly."""
    for i in range(3):
        (tmp_path / f"speech{i}.md").write_text(f"# Speech {i}")
    
    # Each file creates different number of chunks
    chunks = [3, 5, 7]
    call_count = [0]
    
    def side_effect(*args, **kwargs):
        result = {
            "status": "success",
            "speech_id": f"test-{call_count[0]}",
            "chunks_created": chunks[call_count[0]],
            "message": "Success"
        }
        call_count[0] += 1
        return result
    
    mock_ingest.side_effect = side_effect
    
    result = await ingest_markdown_directory(
        directory_path=str(tmp_path),
        ctx=None
    )
    
    # Should sum to 3 + 5 + 7 = 15
    assert result["summary"]["total_chunks_created"] == 15


@pytest.mark.asyncio
@patch("tools.ingest_markdown_directory.ingest_markdown_file")
async def test_error_details(mock_ingest, tmp_path):
    """Test failed_files list contains error_type and error_message."""
    (tmp_path / "speech.md").write_text("# Test")
    
    mock_ingest.side_effect = ValueError("Invalid YAML frontmatter")
    
    result = await ingest_markdown_directory(
        directory_path=str(tmp_path),
        ctx=None
    )
    
    assert len(result["failed_files"]) == 1
    failed_file = result["failed_files"][0]
    
    assert "file_name" in failed_file
    assert "status" in failed_file
    assert failed_file["status"] == "failed"
    assert "error_type" in failed_file
    assert failed_file["error_type"] == "ValueError"
    assert "error_message" in failed_file
    assert "Invalid YAML frontmatter" in failed_file["error_message"]


# Phase 2: Progress Monitoring Tests

@pytest.mark.asyncio
@patch("tools.ingest_markdown_directory.ingest_markdown_file")
async def test_progress_reporting_called(mock_ingest, tmp_path):
    """Test ctx.report_progress called with correct arguments."""
    for i in range(5):
        (tmp_path / f"speech{i}.md").write_text(f"# Speech {i}")
    
    mock_ingest.return_value = {
        "status": "success",
        "speech_id": "test-id",
        "chunks_created": 5,
        "message": "Success"
    }
    
    # Mock context
    mock_ctx = AsyncMock()
    
    await ingest_markdown_directory(
        directory_path=str(tmp_path),
        ctx=mock_ctx
    )
    
    # Verify progress was reported
    assert mock_ctx.report_progress.called
    assert mock_ctx.info.called
    
    # Should report at end
    mock_ctx.report_progress.assert_any_call(5, 5)


@pytest.mark.asyncio
@patch("tools.ingest_markdown_directory.ingest_markdown_file")
async def test_progress_frequency_small_batch(mock_ingest, tmp_path):
    """Test progress updates every file for batches < 20 files."""
    for i in range(10):
        (tmp_path / f"speech{i:02d}.md").write_text(f"# Speech {i}")
    
    mock_ingest.return_value = {
        "status": "success",
        "speech_id": "test-id",
        "chunks_created": 5,
        "message": "Success"
    }
    
    mock_ctx = AsyncMock()
    
    await ingest_markdown_directory(
        directory_path=str(tmp_path),
        ctx=mock_ctx
    )
    
    # Small batch (<20) should update every file
    assert mock_ctx.report_progress.call_count == 10


@pytest.mark.asyncio
@patch("tools.ingest_markdown_directory.ingest_markdown_file")
async def test_progress_at_completion(mock_ingest, tmp_path):
    """Test final progress report shows 100%."""
    for i in range(7):
        (tmp_path / f"speech{i}.md").write_text(f"# Speech {i}")
    
    mock_ingest.return_value = {
        "status": "success",
        "speech_id": "test-id",
        "chunks_created": 5,
        "message": "Success"
    }
    
    mock_ctx = AsyncMock()
    
    await ingest_markdown_directory(
        directory_path=str(tmp_path),
        ctx=mock_ctx
    )
    
    # Final call should show 100% (7/7)
    mock_ctx.report_progress.assert_any_call(7, 7)
    
    # Check last info message contains 100%
    last_info_call = mock_ctx.info.call_args_list[-1][0][0]
    assert "100%" in last_info_call or "7/7" in last_info_call


# Phase 3: Selective File Filtering Tests

@pytest.mark.asyncio
@patch("tools.ingest_markdown_directory.ingest_markdown_file")
async def test_pattern_matching_basic(mock_ingest, tmp_path):
    """Test pattern '*.md' matches all markdown files."""
    (tmp_path / "speech1.md").write_text("# Test 1")
    (tmp_path / "speech2.md").write_text("# Test 2")
    (tmp_path / "notes.txt").write_text("Notes")
    
    mock_ingest.return_value = {
        "status": "success",
        "speech_id": "test-id",
        "chunks_created": 5,
        "message": "Success"
    }
    
    result = await ingest_markdown_directory(
        directory_path=str(tmp_path),
        pattern="*.md",
        ctx=None
    )
    
    # Should only process .md files
    assert result["summary"]["total_files"] == 2
    assert mock_ingest.call_count == 2


@pytest.mark.asyncio
@patch("tools.ingest_markdown_directory.ingest_markdown_file")
async def test_pattern_filtering_prefix(mock_ingest, tmp_path):
    """Test pattern 'speech-*.md' filters correctly."""
    (tmp_path / "speech-001.md").write_text("# Speech 1")
    (tmp_path / "speech-002.md").write_text("# Speech 2")
    (tmp_path / "notes.md").write_text("# Notes")
    (tmp_path / "readme.txt").write_text("Readme")
    
    mock_ingest.return_value = {
        "status": "success",
        "speech_id": "test-id",
        "chunks_created": 5,
        "message": "Success"
    }
    
    result = await ingest_markdown_directory(
        directory_path=str(tmp_path),
        pattern="speech-*.md",
        ctx=None
    )
    
    # Should only process 2 files matching "speech-*.md"
    assert result["summary"]["total_files"] == 2
    assert mock_ingest.call_count == 2


@pytest.mark.asyncio
async def test_no_matches_returns_empty(tmp_path):
    """Test pattern with no matches returns informative message."""
    (tmp_path / "notes.txt").write_text("Notes")
    (tmp_path / "readme.md").write_text("# Readme")
    
    result = await ingest_markdown_directory(
        directory_path=str(tmp_path),
        pattern="speech-*.md",
        ctx=None
    )
    
    assert result["status"] == "complete"
    assert result["summary"]["total_files"] == 0
    assert "No files matched" in result["message"]
    assert "speech-*.md" in result["message"]


# Edge Case Tests (Phase 5)


@pytest.mark.asyncio
@patch("tools.ingest_markdown_directory.ingest_markdown_file")
async def test_symbolic_links_followed(mock_ingest, tmp_path):
    """Test symbolic links are followed if they point to regular files."""
    # Create real file
    real_file = tmp_path / "real-file.md"
    real_file.write_text("# Real File")
    
    # Create symlink to file
    symlink_file = tmp_path / "symlink-file.md"
    symlink_file.symlink_to(real_file)
    
    mock_ingest.return_value = {
        "status": "success",
        "speech_id": "test-id",
        "chunks_created": 5,
        "message": "Success"
    }
    
    result = await ingest_markdown_directory(
        directory_path=str(tmp_path),
        pattern="*.md",
        ctx=None
    )
    
    # Should process both real file and symlink (2 files total)
    assert result["summary"]["total_files"] == 2
    assert mock_ingest.call_count == 2


@pytest.mark.asyncio
@patch("tools.ingest_markdown_directory.ingest_markdown_file")
async def test_file_deleted_during_processing(mock_ingest, tmp_path, mock_ctx):
    """Test file deleted between discovery and processing is handled gracefully."""
    # Create 3 files
    for i in range(3):
        (tmp_path / f"file-{i}.md").write_text(f"# File {i}")
    
    # Mock ingest_markdown_file to delete file 1 on second call
    call_count = 0
    
    async def mock_ingest_with_deletion(file_path, duplicate_policy, validate_path, ctx):
        nonlocal call_count
        call_count += 1
        
        if call_count == 2:
            # Simulate file deleted during processing
            raise FileNotFoundError(f"File not found: {file_path}")
        
        return {
            "status": "success",
            "speech_id": f"test-id-{call_count}",
            "chunks_created": 5,
            "message": "Success"
        }
    
    mock_ingest.side_effect = mock_ingest_with_deletion
    
    result = await ingest_markdown_directory(
        directory_path=str(tmp_path),
        pattern="*.md",
        ctx=mock_ctx
    )
    
    # Should process all 3 files, with 1 failure
    assert result["summary"]["total_files"] == 3
    assert result["summary"]["succeeded"] == 2
    assert result["summary"]["failed"] == 1
    
    # Verify error details captured
    failed = result["failed_files"][0]
    assert failed["error_type"] == "FileNotFoundError"
    assert "not found" in failed["error_message"].lower()


@pytest.mark.asyncio
@patch("tools.ingest_markdown_directory.ingest_markdown_file")
async def test_very_large_file_handled(mock_ingest, tmp_path):
    """Test very large file (50MB+) doesn't cause memory issues.
    
    Note: This test simulates large file handling without actually
    creating a 50MB file (which would slow down tests).
    The actual implementation processes files sequentially,
    so memory usage is bounded by single file size.
    """
    # Create small file for testing
    large_file = tmp_path / "large-file.md"
    large_file.write_text("# Large File\n\n" + "x" * 1000)  # Small for test speed
    
    mock_ingest.return_value = {
        "status": "success",
        "speech_id": "large-file-id",
        "chunks_created": 100,  # Many chunks for large file
        "message": "Success"
    }
    
    result = await ingest_markdown_directory(
        directory_path=str(tmp_path),
        pattern="*.md",
        ctx=None
    )
    
    # Should process successfully
    assert result["summary"]["total_files"] == 1
    assert result["summary"]["succeeded"] == 1
    assert result["summary"]["total_chunks_created"] == 100
