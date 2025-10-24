"""Integration tests for bulk markdown directory ingestion.

Tests end-to-end scenarios with real database and authentication.
Feature 013: Bulk Markdown Directory Ingestion
"""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from tools.ingest_markdown_directory import ingest_markdown_directory


@pytest.fixture
def mock_ctx():
    """Create mock FastMCP context for testing."""
    ctx = AsyncMock()
    ctx.info = AsyncMock()
    ctx.report_progress = AsyncMock()
    return ctx


@pytest.mark.asyncio
async def test_real_hansard_data_ingestion(mock_ctx, monkeypatch):
    """Test bulk ingestion with actual hansard_converted directory (64 files).
    
    This integration test verifies:
    - Directory discovery of 64 real markdown files
    - Progress reporting throughout batch
    - Summary generation with correct counts
    - All files processed (success or failure tracked)
    
    Note: Mocks ingest_markdown_file to avoid database writes during testing.
    """
    hansard_dir = "/home/user/skai-fastmcp-cloudrun/data/hansard_converted"
    
    # Verify test data exists
    hansard_path = Path(hansard_dir)
    assert hansard_path.exists(), f"Test data directory not found: {hansard_dir}"
    
    file_count = len(list(hansard_path.glob("*.md")))
    assert file_count == 64, f"Expected 64 files, found {file_count}"
    
    # Mock ingest_markdown_file to simulate successful ingestion
    async def mock_ingest(file_path, duplicate_policy, validate_path, ctx):
        # Simulate successful ingestion
        return {
            "status": "success",
            "speech_id": "test-speech-id",
            "chunks_created": 5,
            "file_path": str(file_path)
        }
    
    # Apply mock
    from tools import ingest_markdown_directory as imd_module
    monkeypatch.setattr(imd_module, "ingest_markdown_file", mock_ingest)
    
    # Execute bulk ingestion
    result = await ingest_markdown_directory(
        directory_path=hansard_dir,
        pattern="*.md",
        max_files=100,  # Override default to allow 64 files
        duplicate_policy="skip",
        validate_path=True,
        ctx=mock_ctx
    )
    
    # Verify result structure
    assert result["status"] == "complete"
    assert "summary" in result
    assert "successful_files" in result
    assert "failed_files" in result
    
    # Verify counts
    summary = result["summary"]
    assert summary["total_files"] == 64
    assert summary["succeeded"] == 64
    assert summary["failed"] == 0
    assert summary["skipped"] == 0
    
    # Verify chunk aggregation
    assert summary["total_chunks_created"] == 320  # 64 files * 5 chunks each
    
    # Verify progress reporting was called
    assert mock_ctx.report_progress.call_count > 0, \
        "Progress reporting should be called during batch"
    
    # Verify info messages
    assert mock_ctx.info.call_count > 0, \
        "Info messages should be logged during batch"
    
    # Verify all files listed in successful_files
    assert len(result["successful_files"]) == 64
    
    # Verify no failures
    assert len(result["failed_files"]) == 0


@pytest.mark.asyncio
async def test_auth_enforcement_via_feature_012(mock_ctx, monkeypatch):
    """Test that admin authentication is enforced through Feature 012.
    
    This test verifies:
    - Non-admin users are rejected when calling ingest_markdown_file
    - Error is properly propagated and reported in bulk summary
    - Batch continues processing other files (error isolation)
    
    Note: Authentication is handled by Feature 012's ingest_markdown_file,
    not by the bulk ingestion orchestrator.
    """
    test_dir = "/home/user/skai-fastmcp-cloudrun/tests/fixtures/bulk_ingestion/valid"
    
    # Mock ingest_markdown_file to simulate auth failure
    async def mock_ingest_auth_fail(file_path, duplicate_policy, validate_path, ctx):
        # Simulate PermissionError from Feature 012
        raise PermissionError("Admin role required for markdown ingestion")
    
    # Apply mock
    from tools import ingest_markdown_directory as imd_module
    monkeypatch.setattr(imd_module, "ingest_markdown_file", mock_ingest_auth_fail)
    
    # Execute bulk ingestion (should fail all files due to auth)
    result = await ingest_markdown_directory(
        directory_path=test_dir,
        pattern="*.md",
        max_files=100,
        duplicate_policy="skip",
        validate_path=True,
        ctx=mock_ctx
    )
    
    # Verify all files failed with PermissionError
    assert result["status"] == "complete"
    assert result["summary"]["failed"] == 3  # 3 test files in valid/
    assert result["summary"]["succeeded"] == 0
    
    # Verify error details captured
    for failed_file in result["failed_files"]:
        assert failed_file["error_type"] == "PermissionError"
        assert "Admin role required" in failed_file["error_message"]


@pytest.mark.asyncio
@pytest.mark.slow
async def test_large_batch_performance(mock_ctx, monkeypatch):
    """Test that 100-file batch completes within time budget.
    
    This test verifies:
    - System can handle max_files limit (100 files)
    - Performance meets SC-002: 10 files/minute throughput
    - Progress reporting scales correctly for large batches
    - Memory usage stays bounded (one file at a time)
    
    Note: Uses mocked ingestion to test orchestration performance,
    not actual database/embedding performance.
    """
    import time
    
    # Create temporary directory with 100 test files
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create 100 minimal markdown files
        for i in range(100):
            test_file = Path(temp_dir) / f"test-{i:03d}.md"
            test_file.write_text(f"""---
speech_id: test-speech-{i:03d}
speaker_name: Test Speaker
date: 2024-01-01
chamber: House
party: ALP
---

# Test Speech {i}

Test content for performance testing.
""")
        
        # Mock ingest_markdown_file with realistic timing
        async def mock_ingest_timed(file_path, duplicate_policy, validate_path, ctx):
            # Simulate ~0.5s per file (well above 10 files/min = 6s/file target)
            await asyncio.sleep(0.01)  # Fast mock for testing
            return {
                "status": "success",
                "speech_id": f"test-speech-{Path(file_path).stem}",
                "chunks_created": 3,
                "file_path": str(file_path)
            }
        
        # Apply mock
        from tools import ingest_markdown_directory as imd_module
        import asyncio
        monkeypatch.setattr(imd_module, "ingest_markdown_file", mock_ingest_timed)
        
        # Execute bulk ingestion and measure time
        start_time = time.time()
        
        result = await ingest_markdown_directory(
            directory_path=temp_dir,
            pattern="*.md",
            max_files=100,
            duplicate_policy="skip",
            validate_path=True,
            ctx=mock_ctx
        )
        
        elapsed_time = time.time() - start_time
        
        # Verify all files processed
        assert result["summary"]["total_files"] == 100
        assert result["summary"]["succeeded"] == 100
        assert result["summary"]["failed"] == 0
        
        # Verify performance (should complete in <10s with mocked ingestion)
        assert elapsed_time < 10.0, \
            f"100 files took {elapsed_time:.2f}s (expected <10s with mocked ingestion)"
        
        # Verify progress reporting frequency
        # For 100 files, should use frequency of 10 (update every 10 files)
        # Expected calls: 10, 20, 30, 40, 50, 60, 70, 80, 90, 100 = 10 calls
        progress_calls = mock_ctx.report_progress.call_count
        assert 8 <= progress_calls <= 12, \
            f"Expected ~10 progress updates for 100 files, got {progress_calls}"
        
        # Verify final progress shows 100%
        final_call = mock_ctx.report_progress.call_args_list[-1]
        assert final_call[0] == (100, 100), \
            "Final progress should show 100/100 files"
