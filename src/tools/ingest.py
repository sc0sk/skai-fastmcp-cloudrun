"""MCP tool for ingesting Markdown speeches into vector database."""

from pathlib import Path
from typing import List, Dict, Any
import asyncio
import time

from src.models.speech import SpeechMetadata
from src.models.results import IngestionResult
from src.processing.validators import parse_markdown_file, validate_file_batch
from src.processing.chunker import TextChunker
from src.storage.metadata_store import get_default_metadata_store
from src.storage.vector_store import get_default_vector_store


async def ingest_markdown_speeches(
    directory_path: str,
    chunk_size: int = 800,
    chunk_overlap: int = 150,
    dry_run: bool = False,
) -> IngestionResult:
    """
    Ingest Markdown speeches from directory into vector database.

    Args:
        directory_path: Path to directory containing Markdown files
        chunk_size: Chunk size in characters (default: 800)
        chunk_overlap: Overlap between chunks (default: 150)
        dry_run: If True, validate files without inserting to database

    Returns:
        IngestionResult with statistics

    Example:
        >>> result = await ingest_markdown_speeches(
        ...     directory_path="data/sk-hansard",
        ...     dry_run=False
        ... )
        >>> result.speeches_processed
        65
        >>> result.chunks_created
        203

    Raises:
        ValueError: If directory not found or invalid
    """
    start_time = time.time()
    directory = Path(directory_path)

    if not directory.exists():
        raise ValueError(f"Directory not found: {directory_path}")

    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory_path}")

    # Validate all files first
    validation_results = validate_file_batch(directory)
    if validation_results["invalid_files"] > 0:
        # Return early with validation errors
        return IngestionResult(
            speeches_processed=0,
            chunks_created=0,
            vectors_stored=0,
            duplicates_skipped=0,
            errors=validation_results["error_messages"],
            processing_time_seconds=time.time() - start_time,
        )

    # If dry run, return validation results
    if dry_run:
        return IngestionResult(
            speeches_processed=validation_results["valid_files"],
            chunks_created=0,  # Not chunked in dry run
            vectors_stored=0,
            duplicates_skipped=0,
            errors=[],
            processing_time_seconds=time.time() - start_time,
        )

    # Initialize services
    metadata_store = await get_default_metadata_store()
    vector_store = await get_default_vector_store()
    chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    # Process all files
    speeches_processed = 0
    chunks_created = 0
    vectors_stored = 0
    duplicates_skipped = 0
    errors = []

    md_files = list(directory.glob("*.md"))

    for file_path in md_files:
        try:
            # Parse Markdown file
            speech_data = parse_markdown_file(file_path)

            # Create SpeechMetadata instance
            speech = SpeechMetadata(
                title=speech_data["debate"],
                full_text=speech_data["full_text"],
                speaker=speech_data["speaker"],
                party=speech_data["party"],
                chamber=speech_data["chamber"],
                electorate=speech_data.get("electorate"),
                state=speech_data.get("state"),
                date=speech_data["date"],
                hansard_reference=speech_data["hansard_reference"],
            )

            # Add to metadata store (checks for duplicates via content_hash)
            is_duplicate = False
            try:
                speech_id = await metadata_store.add_speech(speech)
            except ValueError as e:
                # Duplicate detected - skip this file entirely
                # (Chunk creation should have happened on first ingestion)
                duplicates_skipped += 1
                continue

            # Chunk text
            chunks = chunker.chunk_text(speech.full_text)
            if not chunks:
                errors.append(f"{file_path.name}: No chunks generated (empty text?)")
                continue

            # Prepare chunk metadata
            chunk_metadatas = []
            for idx, chunk_text in enumerate(chunks):
                chunk_metadatas.append({
                    "speech_id": speech_id,
                    "chunk_index": idx,
                    "chunk_size": len(chunk_text),
                    "speaker": speech.speaker,
                    "party": speech.party,
                    "chamber": speech.chamber,
                    "state": speech.state,
                    "date": speech.date,  # Pass date object directly, not ISO string
                    "hansard_reference": speech.hansard_reference,
                })

            # Add chunks to vector store (generates embeddings automatically)
            chunk_ids = await vector_store.add_chunks(
                texts=chunks,
                metadatas=chunk_metadatas,
                speech_id=speech_id,
            )

            speeches_processed += 1
            chunks_created += len(chunks)
            vectors_stored += len(chunk_ids)

        except Exception as e:
            errors.append(f"{file_path.name}: {str(e)}")
            continue

    processing_time = time.time() - start_time

    return IngestionResult(
        speeches_processed=speeches_processed,
        chunks_created=chunks_created,
        vectors_stored=vectors_stored,
        duplicates_skipped=duplicates_skipped,
        errors=errors,
        processing_time_seconds=processing_time,
    )


async def ingest_single_speech(
    file_path: str,
    chunk_size: int = 800,
    chunk_overlap: int = 150,
) -> Dict[str, Any]:
    """
    Ingest a single Markdown speech file.

    Args:
        file_path: Path to Markdown file
        chunk_size: Chunk size in characters (default: 800)
        chunk_overlap: Overlap between chunks (default: 150)

    Returns:
        Dict with keys: speech_id, chunks_created, processing_time_seconds

    Example:
        >>> result = await ingest_single_speech("data/sk-hansard/speech1.md")
        >>> result["speech_id"]
        'abc-123-def'
        >>> result["chunks_created"]
        4
    """
    start_time = time.time()
    file = Path(file_path)

    if not file.exists():
        raise ValueError(f"File not found: {file_path}")

    # Parse Markdown file
    speech_data = parse_markdown_file(file)

    # Create SpeechMetadata instance
    speech = SpeechMetadata(
        title=speech_data["debate"],
        full_text=speech_data["full_text"],
        speaker=speech_data["speaker"],
        party=speech_data["party"],
        chamber=speech_data["chamber"],
        electorate=speech_data.get("electorate"),
        state=speech_data.get("state"),
        date=speech_data["date"],
        hansard_reference=speech_data["hansard_reference"],
    )

    # Initialize services
    metadata_store = await get_default_metadata_store()
    vector_store = await get_default_vector_store()
    chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    # Add to metadata store
    speech_id = await metadata_store.add_speech(speech)

    # Chunk text
    chunks = chunker.chunk_text(speech.full_text)

    # Prepare chunk metadata
    chunk_metadatas = []
    for idx, chunk_text in enumerate(chunks):
        chunk_metadatas.append({
            "speech_id": speech_id,
            "chunk_index": idx,
            "chunk_size": len(chunk_text),
            "speaker": speech.speaker,
            "party": speech.party,
            "chamber": speech.chamber,
            "state": speech.state,
            "date": speech.date.isoformat(),
            "hansard_reference": speech.hansard_reference,
        })

    # Add chunks to vector store
    chunk_ids = await vector_store.add_chunks(
        texts=chunks,
        metadatas=chunk_metadatas,
        speech_id=speech_id,
    )

    processing_time = time.time() - start_time

    return {
        "speech_id": speech_id,
        "chunks_created": len(chunks),
        "chunk_ids": chunk_ids,
        "processing_time_seconds": processing_time,
    }
