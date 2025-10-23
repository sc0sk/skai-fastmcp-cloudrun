"""Ingest tool for adding new parliamentary speeches to the database."""

from typing import Optional
from datetime import datetime
from pydantic import Field
from fastmcp import Context

from src.models.speech import SpeechMetadata
from src.storage.vector_store import get_default_vector_store
from src.storage.metadata_store import get_default_metadata_store
from langchain.text_splitter import RecursiveCharacterTextSplitter

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

    Use this when: Adding new Simon Kennedy speeches to the database for search
    and retrieval. This is an administrative operation typically used by data
    ingestion pipelines or scheduled imports.

    Do not use: For updating existing speeches (use dedicated update tools) or
    for non-Simon Kennedy speeches (out of scope).

    Parameters:
    - speech_data: Complete speech metadata and text (required fields: date,
      speaker, party, chamber, title, text)
    - generate_embeddings: Whether to create vector embeddings for semantic
      search (default: true)

    Limitations: Requires valid speech metadata. Does not validate speech
    authenticity or check for duplicates.

    Workflow: Typically used by admin tools or scheduled imports. After ingestion,
    speeches become searchable via search_hansard_speeches.

    Note: This is a write operation that modifies the database. Use with caution.
    """
    try:
        # Stage 1: Validation (0-20%)
        if ctx:
            await ctx.report_progress(STAGE_VALIDATION[0], 100)
            await ctx.info("Validating speech data...")

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
        # Use LangChain's RecursiveCharacterTextSplitter for intelligent chunking
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,  # ~200 words
            chunk_overlap=100,  # Overlap for context continuity
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        chunks = text_splitter.split_text(speech.full_text)

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
                "date": speech.date,
                "topic_tags": speech.topic_tags,
                "hansard_reference": speech.hansard_reference,
                "title": speech.title,
            })

        # First, add speech metadata to get speech_id
        if ctx:
            await ctx.report_progress(STAGE_METADATA_STORAGE[0], 100)
            await ctx.info("Storing speech metadata...")

        # Stage 5: Metadata storage (90-100%)
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

            vector_store = await get_default_vector_store()
            chunk_ids = await vector_store.add_chunks(
                texts=chunks,
                metadatas=chunk_metadatas,
                speech_id=speech_id,
                ctx=ctx  # Pass context for sub-progress
            )

            if ctx:
                await ctx.info(f"Stored {len(chunk_ids)} chunks with embeddings")
        else:
            chunk_ids = []
            if ctx:
                await ctx.info("Skipped embedding generation (generate_embeddings=False)")

        # Final completion
        if ctx:
            await ctx.report_progress(100, 100)
            await ctx.info("Speech ingestion complete!")

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
