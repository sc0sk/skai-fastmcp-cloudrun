"""Bulk markdown directory ingestion with progress reporting and error isolation.

This module provides functionality to ingest entire directories of markdown files
in a single operation, with progress reporting, error isolation, and detailed
batch summary reporting.

Feature 013: Bulk Markdown Directory Ingestion
"""
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastmcp import Context

from tools.ingest_markdown_file import ingest_markdown_file


async def ingest_markdown_directory(
    directory_path: str,
    pattern: str = "*.md",
    max_files: int = 100,
    duplicate_policy: str = "skip",
    validate_path: bool = True,
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
    
    Performance Characteristics:
    - Sequential processing (one file at a time)
    - Memory bounded by single file size
    - Expected maximum file size: 50MB
    - Files larger than 50MB may work but are not optimized
    - Typical throughput: 10-12 files per minute
    
    Args:
        directory_path: Path to directory with markdown files
        pattern: Glob pattern for file filtering (e.g. "*.md", "speech-*.md")
        max_files: Maximum files to process (default 100, safety limit)
        duplicate_policy: How to handle duplicates ("skip", "update", "error")
        validate_path: Whether to validate paths (default True)
        ctx: FastMCP context for auth and progress (optional)
        
    Returns:
        Dict with:
        - status: "complete"
        - summary: Dict with total_files, succeeded, failed, skipped counts
        - successful_files: List of successfully ingested file details
        - failed_files: List of failed file details with error info
        - message: Human-readable summary message
        
    Raises:
        FileNotFoundError: Directory doesn't exist
        ValueError: Invalid parameters or exceeded max_files
        PermissionError: User not admin (via ingest_markdown_file)
    """
    # Step 1: Validate directory exists
    dir_path = Path(directory_path)
    
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory_path}")
    
    if not dir_path.is_dir():
        raise ValueError(f"Path is not a directory: {directory_path}")
    
    if not os.access(dir_path, os.R_OK):
        raise PermissionError(f"Directory not readable: {directory_path}")
    
    # Step 2: Discover files matching pattern
    files = sorted(dir_path.glob(pattern))
    # Filter to keep only files (not directories), follow symlinks
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
            "message": (
                f"No files matched pattern '{pattern}' "
                f"in {directory_path}"
            )
        }
    
    # Step 2b: Enforce safety limit
    if total_files > max_files:
        raise ValueError(
            f"Safety limit exceeded: Found {total_files} files, "
            f"max allowed is {max_files}. "
            f"Increase max_files parameter if intentional."
        )
    
    # Step 3: Process files with progress reporting
    successful_files: List[Dict[str, Any]] = []
    failed_files: List[Dict[str, Any]] = []
    total_chunks = 0
    skipped_count = 0
    
    # Calculate progress update frequency (adaptive)
    if total_files < 20:
        update_frequency = 1  # Every file for small batches
    elif total_files < 100:
        update_frequency = 5  # Every 5 files for medium batches
    else:
        update_frequency = 10  # Every 10 files for large batches
    
    for idx, file_path in enumerate(files, 1):
        try:
            result = await ingest_markdown_file(
                file_path=str(file_path),
                duplicate_policy=duplicate_policy,
                validate_path=validate_path,
                ctx=ctx
            )
            
            file_result = {
                "file_name": file_path.name,
                "status": result["status"],
                "speech_id": result["speech_id"],
                "chunks_created": result["chunks_created"]
            }
            successful_files.append(file_result)
            
            if result["status"] == "skipped":
                skipped_count += 1
            else:
                total_chunks += result["chunks_created"]
                
        except Exception as e:
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
                f"{len(successful_files)} succeeded, "
                f"{len(failed_files)} failed"
            )
    
    # Step 4: Generate summary
    succeeded_count = len(successful_files) - skipped_count
    
    return {
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
