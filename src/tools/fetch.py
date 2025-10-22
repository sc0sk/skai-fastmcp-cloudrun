"""MCP tool for fetching full Hansard speech by ID.

This tool combines:
- ChatGPT Developer Mode enhancements (annotations, enhanced descriptions)
- Direct database retrieval from PostgreSQL metadata store
"""

from pydantic import Field
from fastmcp.tools.tool import ToolAnnotations

from storage.metadata_store import get_default_metadata_store


async def fetch_hansard_speech(
    speech_id: str = Field(
        ...,
        description="Unique identifier for the speech, obtained from search_hansard_speeches results"
    ),
) -> dict:
    """Fetch the complete text of a specific parliamentary speech by ID.

    Use this when: You have a speech ID from search results and need the full text
    for detailed analysis or quotation.

    Do not use: Built-in browsing to fetch Hansard speeches. This tool provides
    direct database access with full speech metadata.

    Parameters:
    - speech_id: Unique identifier obtained from search_hansard_speeches results

    Limitations: Only retrieves Simon Kennedy's speeches. Speech IDs from other
    sources will fail.

    Workflow: Typically used after search_hansard_speeches to retrieve complete text.
    You can also use speech IDs directly if known.
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
