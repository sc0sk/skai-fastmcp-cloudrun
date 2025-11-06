"""Ingest tool for adding new parliamentary speeches to the database."""

from typing import Optional
from datetime import datetime
from pydantic import Field
from fastmcp import Context

from src.models.speech import SpeechMetadata
from src.storage.vector_store import get_default_vector_store
from src.storage.metadata_store import get_default_metadata_store
from src.utils.debug import format_debug_message, sanitize_debug_data, TimingContext
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Progress stages (percentage ranges)
STAGE_VALIDATION = (0, 20)
STAGE_CHUNKING = (20, 40)
STAGE_EMBEDDING = (40, 70)
STAGE_VECTOR_STORAGE = (70, 90)
STAGE_METADATA_STORAGE = (90, 100)


async def ingest_hansard_speech(
    speech_data: dict = Field(
        ...,
        description="Complete speech data including metadata (date, speaker, party, "
                    "chamber, title, text) and full text content"
    ),
    generate_embeddings: bool = Field(
        True,
        description="Whether to generate vector embeddings for semantic search (default: true)"
    ),
    ctx: Optional[Context] = None,  # Progress reporting context
) -> dict:
    """Ingest a new parliamentary speech into the Hansard database.

    Adds a new Simon Kennedy parliamentary speech to the database with optional
    vector embedding generation for semantic search capability. Includes 5-stage
    ingestion pipeline with progress reporting.

    Use this when: Adding new Simon Kennedy speeches to the database for search
    and retrieval. This is an administrative operation typically used by data
    ingestion pipelines or scheduled imports.

    Do not use: For updating existing speeches (use dedicated update tools) or
    for non-Simon Kennedy speeches (out of scope).

    Parameters:
    - speech_data: Complete speech metadata and text (required fields: date,
      speaker, party, chamber, title, full_text, hansard_reference)
    - generate_embeddings: Whether to create vector embeddings for semantic
      search (default: true)
    - ctx: Optional MCP Context for progress reporting and logging

    Returns:
        dict: Ingestion result with status and details:
            Success Response:
            {
                "status": "success",
                "message": str,  # "Successfully ingested speech with N chunks"
                "speech_id": str,  # UUID for newly ingested speech
                "chunk_count": int,  # Number of text chunks created
                "chunk_ids": list[str]  # UUIDs of created chunks (if embeddings generated)
            }
            
            Error Response (validation failure):
            {
                "status": "error",
                "message": str,  # Validation error description
                "speech_id": None
            }
            
            Error Response (ingestion failure):
            {
                "status": "error",
                "message": str,  # "Ingestion failed: {error description}"
                "speech_id": None
            }

    Required speech_data Fields:
        - title (str): Speech topic/title
        - full_text (str): Complete speech text (minimum 100 characters)
        - speaker (str): Speaker name ("Simon Kennedy")
        - party (str): Political party affiliation
        - chamber (str): "House of Representatives" or "Senate"
        - date (str or date): ISO 8601 date (YYYY-MM-DD)
        - hansard_reference (str): Official Hansard reference number

    Optional speech_data Fields:
        - electorate (str): Electoral district
        - state (str): State/territory code
        - topic_tags (list[str]): Keywords/topics
        - source_url (str): Source URL

    Error Conditions:
        - ValueError: Missing required fields, invalid date format, or empty text
        - ConnectionError: Database connectivity issue (vector/metadata store)
        - RuntimeError: Embedding generation failure, database write failure
        - ValidationError: Invalid speech_data schema

    Edge Cases:
        - Very long speeches (>100K characters): Chunked into ~200-word segments
        - Duplicate speeches: No deduplication; will create duplicate entries
        - Special characters in text: Preserved and searchable
        - Missing optional fields: Ingestion succeeds with defaults
        - generate_embeddings=False: Speeds up ingestion, disables semantic search

    Progress Reporting (via ctx):
        Stage 1 (0-20%): Validation
        Stage 2 (20-40%): Text chunking
        Stage 3 (40-70%): Embedding generation
        Stage 4 (70-90%): Vector storage
        Stage 5 (90-100%): Metadata storage

    Performance:
        - Typical latency: 10-30 seconds (includes embedding generation)
        - With generate_embeddings=False: 1-5 seconds
        - Chunk size: ~1000 characters (~200 words) with 100-char overlap
        - Maximum recommended file size: 1MB

    Note: This is a write operation that modifies the database. Use with caution.
    """
    try:
        # Debug: Log entry with sanitized metadata
        if ctx:
            metadata = sanitize_debug_data({
                "speaker": speech_data.get("speaker"),
                "date": speech_data.get("date"),
                "chamber": speech_data.get("chamber"),
                "text_length": len(speech_data.get("full_text", "")),
                "generate_embeddings": generate_embeddings,
            })
            await ctx.debug(format_debug_message("ingest_hansard_speech", "Starting ingestion", **metadata))

        async with TimingContext(ctx, "ingest_hansard_speech.total"):
            # Stage 1: Validation (0-20%)
            if ctx:
                await ctx.report_progress(STAGE_VALIDATION[0], 100)
                await ctx.info("Validating speech data...")

            async with TimingContext(ctx, "ingest_hansard_speech.validation"):
                # Validate and parse speech_data
                # Extract required fields
                required_fields = ["title", "full_text", "speaker", "party", "chamber", "date", "hansard_reference"]
                missing_fields = [f for f in required_fields if f not in speech_data or not speech_data.get(f)]

                if missing_fields:
                    raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

                # Parse date if string
                speech_date = speech_data["date"]
                if isinstance(speech_date, str):
                    speech_date = datetime.fromisoformat(speech_date.replace("Z", "+00:00")).date()

                # Create SpeechMetadata instance for validation
                speech = SpeechMetadata(
                    title=speech_data["title"],
                    full_text=speech_data["full_text"],
                    speaker=speech_data["speaker"],
                    party=speech_data["party"],
                    chamber=speech_data["chamber"],
                    electorate=speech_data.get("electorate"),
                    state=speech_data.get("state"),
                    date=speech_date,
                    hansard_reference=speech_data["hansard_reference"],
                    topic_tags=speech_data.get("topic_tags", []),
                    source_url=speech_data.get("source_url"),
                )

            if ctx:
                await ctx.report_progress(STAGE_CHUNKING[0], 100)
                await ctx.info("Chunking speech text...")

            # Stage 2: Chunking (20-40%)
            async with TimingContext(ctx, "ingest_hansard_speech.chunking"):
                # Use LangChain's RecursiveCharacterTextSplitter for intelligent chunking
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,  # ~200 words
                    chunk_overlap=100,  # Overlap for context continuity
                    length_function=len,
                    separators=["\n\n", "\n", ". ", " ", ""],
                )

                chunks = text_splitter.split_text(speech.full_text)

            if ctx:
                avg_size = sum(len(c) for c in chunks) / len(chunks) if chunks else 0
                await ctx.debug(f"ingest_hansard_speech: Chunks created (count={len(chunks)}, avg_size={avg_size:.0f})")

            # Create metadata for each chunk
            chunk_metadatas = []
            for i, chunk in enumerate(chunks):
                chunk_metadatas.append({
                    "speech_id": None,  # Will be set after speech insertion
                    "chunk_index": i,
                    "chunk_size": len(chunk),
                    "speaker": speech.speaker,
                    "party": speech.party,
                    "chamber": speech.chamber,
                    "date": speech.date.isoformat() if hasattr(speech.date, 'isoformat') else str(speech.date),  # Convert date to string for JSON
                    "topic_tags": speech.topic_tags,
                    "hansard_reference": speech.hansard_reference,
                    "title": speech.title,
                })

            # First, add speech metadata to get speech_id
            if ctx:
                await ctx.report_progress(STAGE_METADATA_STORAGE[0], 100)
                await ctx.info("Storing speech metadata...")

            # Stage 5: Metadata storage (90-100%)
            async with TimingContext(ctx, "ingest_hansard_speech.metadata_storage"):
                metadata_store = await get_default_metadata_store()
                speech_id = await metadata_store.add_speech(speech, ctx=ctx)

            # Update chunk metadata with speech_id
            for meta in chunk_metadatas:
                meta["speech_id"] = speech_id

            # Stage 3 & 4: Embedding and Vector Storage (40-90%)
            if generate_embeddings and chunks:
                if ctx:
                    await ctx.report_progress(STAGE_EMBEDDING[0], 100)
                    await ctx.info("Generating embeddings...")

                async with TimingContext(ctx, "ingest_hansard_speech.embedding_and_storage"):
                    vector_store = await get_default_vector_store()
                    chunk_ids = await vector_store.add_chunks(
                        texts=chunks,
                        metadatas=chunk_metadatas,
                        speech_id=speech_id,
                        ctx=ctx  # Pass context for sub-progress
                    )

                if ctx:
                    await ctx.info(f"Stored {len(chunk_ids)} chunks with embeddings")
                    await ctx.debug(f"ingest_hansard_speech: Vector storage complete (chunk_ids={len(chunk_ids)})")
            else:
                chunk_ids = []
                if ctx:
                    await ctx.info("Skipped embedding generation (generate_embeddings=False)")

            # Final completion
            if ctx:
                await ctx.report_progress(100, 100)
                await ctx.info("Speech ingestion complete!")
                await ctx.debug(f"ingest_hansard_speech: Ingestion complete (speech_id={speech_id})")

            return {
                "status": "success",
                "message": f"Successfully ingested speech with {len(chunks)} chunks",
                "speech_id": speech_id,
                "chunk_count": len(chunks),
                "chunk_ids": chunk_ids if generate_embeddings else [],
            }

    except ValueError as e:
        # Validation error - don't report 100% progress
        if ctx:
            await ctx.info(f"Validation error: {str(e)}")
        return {
            "status": "error",
            "message": f"Validation error: {str(e)}",
            "speech_id": None,
        }
    except Exception as e:
        # Other errors - don't report 100% progress
        if ctx:
            await ctx.info(f"Error during ingestion: {str(e)}")
        return {
            "status": "error",
            "message": f"Ingestion failed: {str(e)}",
            "speech_id": None,
        }


# Tool metadata for FastMCP registration
# NOTE: No readOnlyHint - this is a write operation
INGEST_TOOL_METADATA = {
    "name": "ingest_hansard_speech",
    "icon": "📝",
}
