"""Ingest tool for adding new parliamentary speeches to the database."""

from pydantic import Field


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
    # Placeholder implementation - actual database insert would go here
    # This would:
    # 1. Validate speech_data structure
    # 2. Insert into Cloud SQL PostgreSQL speeches table
    # 3. Generate embeddings with Vertex AI if generate_embeddings=True
    # 4. Insert embeddings into speech_chunks table
    # 5. Return success/error status

    return {
        "status": "success",
        "message": "Tool implemented with ChatGPT Developer Mode enhancements. "
                   "Database integration pending.",
        "speech_id": None
    }


# Tool metadata for FastMCP registration
# NOTE: No readOnlyHint - this is a write operation
INGEST_TOOL_METADATA = {
    "name": "ingest_hansard_speech",
    "icon": "📝",
}
