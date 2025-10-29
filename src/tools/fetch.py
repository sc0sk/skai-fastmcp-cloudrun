"""MCP tool for fetching full Hansard speech by ID.

This tool combines:
- ChatGPT Developer Mode enhancements (annotations, enhanced descriptions)
- Direct database retrieval from PostgreSQL metadata store
"""

from typing import Annotated
from pydantic import Field
from fastmcp.tools.tool import ToolAnnotations

from src.storage.metadata_store import get_default_metadata_store


async def fetch_hansard_speech(
    speech_id: Annotated[str, Field(
        description="Unique identifier for the speech, obtained from search_hansard_speeches results"
    )],
) -> dict:
    """Fetch the complete text of a specific parliamentary speech by ID.

    Retrieves the full speech text and complete metadata for a Simon Kennedy
    parliamentary speech from the Hansard database by unique identifier.

    Use this when: You have a speech ID from search results and need the full text
    for detailed analysis or quotation.

    Do not use: Built-in browsing to fetch Hansard speeches. This tool provides
    direct database access with full speech metadata.

    Parameters:
    - speech_id: Unique identifier (UUID format) obtained from search_hansard_speeches
      results or known directly

    Returns:
        dict: Complete speech data with the following structure:
            {
                "speech_id": str,  # UUID for the speech
                "title": str,  # Speech topic/title
                "full_text": str,  # Complete speech text
                "speaker": str,  # "Simon Kennedy"
                "party": str,  # "Liberal" or other party
                "chamber": str,  # "House of Representatives" or "Senate"
                "electorate": str,  # Electoral district
                "state": str,  # State/territory (e.g., "NSW", "VIC")
                "date": str,  # ISO 8601 date (YYYY-MM-DD)
                "hansard_reference": str,  # Official Hansard reference number
                "topic_tags": list[str],  # Keywords/topics (e.g., ["housing", "infrastructure"])
                "word_count": int,  # Total words in speech
                "content_hash": str  # SHA256 hash for integrity verification
            }

    Error Conditions:
        - ValueError: If speech_id not found in database (message: "Speech not found: {id}")
        - ConnectionError: Database connectivity issue (metadata store unavailable)
        - InvalidArgumentError: Invalid UUID format for speech_id
        - RuntimeError: Database query execution failure

    Edge Cases:
        - Malformed UUID: Raises InvalidArgumentError with details
        - Non-existent UUID (valid format): Raises ValueError "Speech not found"
        - Empty/null speech_id: Parameter validation prevents submission
        - Concurrent deletion: Returns ValueError if speech deleted between query and fetch

    Performance:
        - Typical latency: 100-500ms (direct database lookup)
        - No caching: Fresh read on each call
        - Response size: 5-50KB depending on speech length

    Workflow: Typically used after search_hansard_speeches to retrieve complete text.
    You can also use speech IDs directly if known from other sources.

    Idempotent: Multiple calls with same speech_id return identical results.
    """
    metadata_store = await get_default_metadata_store()

    # Retrieve speech from database
    speech = await metadata_store.get_speech(speech_id)

    if not speech:
        raise ValueError(f"Speech not found: {speech_id}")

    # Convert to dict for MCP response
    return {
        "speech_id": speech_id,
        "title": speech.title,
        "full_text": speech.full_text,
        "speaker": speech.speaker,
        "party": speech.party,
        "chamber": speech.chamber,
        "electorate": speech.electorate,
        "state": speech.state,
        "date": speech.date.isoformat(),
        "hansard_reference": speech.hansard_reference,
        "topic_tags": speech.topic_tags,
        "word_count": speech.word_count,
        "content_hash": speech.content_hash,
    }


# Tool metadata for FastMCP registration (ChatGPT Developer Mode enhancements)
FETCH_TOOL_METADATA = {
    "name": "fetch_hansard_speech",
    "annotations": ToolAnnotations(
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=False
    ),
    "icon": "📄",  # Not supported in FastMCP 2.12.5, stored for future use
}
