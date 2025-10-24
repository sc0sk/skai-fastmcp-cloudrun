# Quickstart: Bulk Markdown Directory Ingestion

**Feature**: 013-bulk-markdown-ingestion
**Estimated Time**: ~45 minutes
**Prerequisites**: Feature 012 (ingest_markdown_file tool) implemented and working

## Overview

This quickstart guide provides a rapid implementation path for the bulk directory ingestion feature. The feature wraps the existing single-file ingestion tool with directory discovery, file filtering, sequential processing, and batch summary reporting.

## Implementation Steps

### Step 1: Create Bulk Ingestion Tool (30 minutes)

Create `src/tools/ingest_markdown_directory.py`:

```python
"""Bulk markdown directory ingestion with progress reporting and error isolation."""
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastmcp import Context
from pydantic import Field

from tools.ingest_markdown_file import ingest_markdown_file


async def ingest_markdown_directory(
    directory_path: str = Field(
        ...,
        description="Path to directory containing markdown files"
    ),
    pattern: str = Field(
        default="*.md",
        description="Glob pattern for file filtering (e.g., '*.md', 'hansard-*.md')"
    ),
    max_files: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of files to process (safety limit)"
    ),
    duplicate_policy: str = Field(
        default="skip",
        description="How to handle duplicates: 'skip', 'update', or 'error'",
        pattern="^(skip|update|error)$"
    ),
    validate_path: bool = Field(
        default=True,
        description="Whether to validate file paths for security"
    ),
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """Ingest all markdown files from a directory with progress reporting.
    
    Features:
    - Sequential processing of discovered files
    - Progress reporting after each file
    - Error isolation (one failure doesn't stop batch)
    - Detailed summary with success/failure counts
    - File pattern filtering support
    - Safety limits to prevent accidental large batches
    
    Args:
        directory_path: Path to directory with markdown files
        pattern: Glob pattern for file filtering
        max_files: Maximum files to process (safety)
        duplicate_policy: How to handle duplicates
        validate_path: Whether to validate paths
        ctx: FastMCP context for auth and progress
        
    Returns:
        Dict with status, summary stats, successful_files, failed_files
        
    Raises:
        FileNotFoundError: Directory doesn't exist
        ValueError: Invalid parameters or exceeded max_files
        PermissionError: User not admin (via ingest_markdown_file)
    """
    # Step 1: Validate directory
    dir_path = Path(directory_path)
    
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory_path}")
    
    if not dir_path.is_dir():
        raise ValueError(f"Path is not a directory: {directory_path}")
    
    if not os.access(dir_path, os.R_OK):
        raise PermissionError(f"Directory not readable: {directory_path}")
    
    # Step 2: Discover files matching pattern
    files = sorted(dir_path.glob(pattern))
    # Filter to keep only files (not directories)
    files = [f for f in files if f.is_file()]
    
    total_files = len(files)
    
    # Handle no files matching pattern
    if total_files == 0:
        return {
            "status": "complete",
            "summary": {
                "total_files": 0,
                "succeeded": 0,
                "skipped": 0,
                "failed": 0,
                "total_chunks_created": 0
            },
            "successful_files": [],
            "failed_files": [],
            "message": f"No files matched pattern '{pattern}' in {directory_path}"
        }
    
    # Step 3: Enforce safety limit
    if total_files > max_files:
        raise ValueError(
            f"Safety limit exceeded: Found {total_files} files, "
            f"max allowed is {max_files}. "
            f"Increase max_files parameter if intentional."
        )
    
    # Step 4: Process files sequentially with error isolation
    successful_files: List[Dict[str, Any]] = []
    failed_files: List[Dict[str, Any]] = []
    total_chunks = 0
    skipped_count = 0
    
    # Calculate progress update frequency
    update_frequency = 1 if total_files < 20 else 5 if total_files < 100 else 10
    
    for idx, file_path in enumerate(files, 1):
        try:
            # Call single-file ingestion tool
            result = await ingest_markdown_file(
                file_path=str(file_path),
                duplicate_policy=duplicate_policy,
                validate_path=validate_path,
                ctx=ctx  # Auth checked here
            )
            
            # Collect success result
            file_result = {
                "file_name": file_path.name,
                "status": result["status"],  # "success" or "skipped"
                "speech_id": result["speech_id"],
                "chunks_created": result["chunks_created"]
            }
            successful_files.append(file_result)
            
            if result["status"] == "skipped":
                skipped_count += 1
            else:
                total_chunks += result["chunks_created"]
                
        except Exception as e:
            # Collect failure result
            failed_files.append({
                "file_name": file_path.name,
                "status": "failed",
                "error_type": type(e).__name__,
                "error_message": str(e)
            })
        
        # Report progress
        if ctx and (idx % update_frequency == 0 or idx == total_files):
            progress_pct = int((idx / total_files) * 100)
            await ctx.report_progress(idx, total_files)
            await ctx.info(
                f"Progress: {idx}/{total_files} files ({progress_pct}%) - "
                f"{len(successful_files)} succeeded, {len(failed_files)} failed"
            )
    
    # Step 5: Generate summary
    succeeded_count = len(successful_files) - skipped_count
    
    summary = {
        "status": "complete",
        "summary": {
            "total_files": total_files,
            "succeeded": succeeded_count,
            "skipped": skipped_count,
            "failed": len(failed_files),
            "total_chunks_created": total_chunks
        },
        "successful_files": successful_files,
        "failed_files": failed_files,
        "message": (
            f"Processed {total_files} files: "
            f"{succeeded_count} succeeded, "
            f"{skipped_count} skipped, "
            f"{len(failed_files)} failed"
        )
    }
    
    return summary
```

**Key Points**:
- Validates directory before processing
- Uses `pathlib.Path.glob()` for pattern matching
- Calls `ingest_markdown_file()` for each file (reuses Feature 012)
- Try-except around each file (error isolation)
- Progress reporting with adaptive frequency
- Returns structured summary with all details

---

### Step 2: Register MCP Tool (5 minutes)

Update `src/server.py`:

```python
# Add import at top
from tools.ingest_markdown_directory import ingest_markdown_directory

# Register tool (after ingest_markdown_file registration)
mcp.tool(
    name="ingest_markdown_directory",
    exclude_args=["ctx"],
    annotations={
        "destructiveHint": True,  # Write operation
        "requiresAuth": True,  # Admin required
        "requiredRole": "admin"
    }
)(ingest_markdown_directory)

# Update startup message
print("   📂 ingest_markdown_directory [bulk directory ingestion with progress]")
```

---

### Step 3: Write Tests (10 minutes)

Create `tests/unit/test_ingest_markdown_directory.py`:

```python
"""Unit tests for bulk markdown directory ingestion."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from tools.ingest_markdown_directory import ingest_markdown_directory


@pytest.mark.asyncio
async def test_directory_not_found():
    """Should raise FileNotFoundError for non-existent directory."""
    with pytest.raises(FileNotFoundError, match="Directory not found"):
        await ingest_markdown_directory(
            directory_path="/nonexistent/path",
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
async def test_progress_reporting(mock_ingest, tmp_path):
    """Should report progress during processing."""
    # Create test files
    for i in range(10):
        (tmp_path / f"speech{i:02d}.md").write_text(f"# Speech {i}")
    
    mock_ingest.return_value = {
        "status": "success",
        "speech_id": "test-id",
        "chunks_created": 5,
        "message": "Success"
    }
    
    # Mock context
    mock_ctx = AsyncMock()
    
    result = await ingest_markdown_directory(
        directory_path=str(tmp_path),
        pattern="*.md",
        ctx=mock_ctx
    )
    
    # Verify progress was reported
    assert mock_ctx.report_progress.called
    assert mock_ctx.info.called
    
    # Should report at end
    mock_ctx.report_progress.assert_any_call(10, 10)


@pytest.mark.asyncio
@patch("tools.ingest_markdown_directory.ingest_markdown_file")
async def test_pattern_filtering(mock_ingest, tmp_path):
    """Should only process files matching pattern."""
    # Create mixed files
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
```

---

## Testing the Implementation

### Manual Test with Real Data

```bash
# Using MCP Inspector or Claude Code:
# Test with real hansard_converted directory

{
  "directory_path": "/home/user/skai-fastmcp-cloudrun/data/hansard_converted",
  "pattern": "*.md",
  "max_files": 100,
  "duplicate_policy": "skip"
}

# Expected output:
# - 64 files processed
# - All successful (assuming valid data)
# - Progress updates every 5 files
# - Detailed summary with file list
```

### Integration Test

```python
# tests/integration/test_bulk_ingestion_e2e.py
@pytest.mark.asyncio
async def test_bulk_ingestion_real_data():
    """Test bulk ingestion with real hansard_converted directory."""
    result = await ingest_markdown_directory(
        directory_path="data/hansard_converted",
        pattern="*.md",
        max_files=100,
        duplicate_policy="skip",
        ctx=test_context  # Mock admin auth
    )
    
    assert result["status"] == "complete"
    assert result["summary"]["total_files"] == 64
    # Allow for some skips if already ingested
    assert result["summary"]["succeeded"] + result["summary"]["skipped"] >= 60
```

---

## Deployment Checklist

- [ ] Tool implementation created (`ingest_markdown_directory.py`)
- [ ] Tool registered in `server.py` with annotations
- [ ] Unit tests written and passing
- [ ] Integration test with real data passing
- [ ] MCP Inspector testing completed
- [ ] Error handling verified (invalid directory, pattern, limits)
- [ ] Progress reporting verified (console logs, client updates)
- [ ] Admin auth working (non-admin users rejected)
- [ ] Summary report format validated
- [ ] Documentation updated (if applicable)

---

## Common Issues & Solutions

### Issue: "Directory not found"
**Solution**: Verify directory path is absolute or relative to working directory

### Issue: "Safety limit exceeded"
**Solution**: Increase `max_files` parameter if intentional large batch

### Issue: "No files matched pattern"
**Solution**: Check glob pattern syntax, verify files have correct extension

### Issue: Progress not showing
**Solution**: Verify ctx parameter passed, check client supports progress reporting

### Issue: All files failing
**Solution**: Check single-file ingestion works first (Feature 012), verify file format

---

## Performance Expectations

- **Small batch (10 files)**: ~1-2 minutes
- **Medium batch (50 files)**: ~5-8 minutes
- **Large batch (100 files)**: ~10-15 minutes
- **Progress updates**: Every 1-5 files depending on batch size
- **Memory usage**: One file in memory at a time (bounded)

---

## Next Steps

After implementation:
1. Run `/speckit.tasks` to generate detailed task breakdown
2. Run `/speckit.implement` to execute tasks with TDD workflow
3. Test with real hansard_converted data (64 files)
4. Monitor performance and error rates
5. Consider future optimizations (parallel processing)

---

## Summary

This quickstart provides a complete implementation in ~45 minutes:
- ✅ 30 min: Bulk ingestion tool
- ✅ 5 min: Tool registration
- ✅ 10 min: Unit tests

The implementation reuses all Feature 012 logic and adds orchestration layer for batch processing with progress reporting and error isolation.
