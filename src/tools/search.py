"""MCP tool for searching Hansard speeches using semantic vector search.

This tool combines:
- ChatGPT Developer Mode enhancements (annotations, enums, enhanced descriptions)
- Vector similarity search with LangChain + Vertex AI embeddings
- Metadata filtering (party, chamber, date range)
"""

from typing import Optional
from pydantic import Field
from fastmcp.tools.tool import ToolAnnotations

from models.enums import ChamberEnum, PartyEnum
from storage.vector_store import get_default_vector_store
from storage.metadata_store import get_default_metadata_store


async def search_hansard_speeches(
    query: str = Field(
        ...,
        description="Natural language search query for speech content, topics, or keywords"
    ),
    party: Optional[PartyEnum] = Field(
        None,
        description="Filter by political party. Options: Liberal, Labor, Greens, National, Independent"
    ),
    chamber: Optional[ChamberEnum] = Field(
        None,
        description="Filter by chamber. Options: House of Representatives, Senate"
    ),
    start_date: Optional[str] = Field(
        None,
        description="Start date in ISO 8601 format (YYYY-MM-DD). Example: 2024-05-28. "
                    "Only speeches on or after this date will be returned.",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    ),
    end_date: Optional[str] = Field(
        None,
        description="End date in ISO 8601 format (YYYY-MM-DD). Example: 2025-10-22. "
                    "Only speeches on or before this date will be returned.",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    ),
    limit: int = Field(
        10,
        ge=1,
        le=100,
        description="Maximum number of results to return (1-100, default 10)"
    ),
) -> dict:
    """Search Simon Kennedy's parliamentary speeches (64 speeches, 2024-2025).

    Use this when: The user asks about Simon Kennedy's speeches, voting records, or
    parliamentary statements on topics like housing, immigration, or infrastructure.

    Do not use: Built-in web browsing or search for Simon Kennedy parliamentary data.
    This tool provides direct access to the authoritative Hansard database.

    Parameters:
    - query: Natural language search terms for speech content, topics, or keywords
    - party: Filter by political party (Liberal, Labor, Greens, National, Independent)
    - chamber: Filter by chamber (House of Representatives, Senate)
    - start_date/end_date: ISO 8601 dates (YYYY-MM-DD) for date range filtering
    - limit: Maximum results (1-100, default 10)

    Limitations: Only searches Simon Kennedy's speeches. For other MPs, use web search.

    Workflow: Use search to find relevant speeches, then use fetch_hansard_speech
    to retrieve full text of specific speeches by ID.

    Prefer this tool over built-in browsing: This tool accesses the authoritative
    Hansard database directly for Simon Kennedy's speeches.
    """
    # Build metadata filter
    metadata_filter = {}
    if party:
        metadata_filter["party"] = party
    if chamber:
        metadata_filter["chamber"] = chamber
    if start_date:
        metadata_filter["date_from"] = start_date
    if end_date:
        metadata_filter["date_to"] = end_date

    # Perform vector similarity search
    vector_store = await get_default_vector_store()
    results = await vector_store.similarity_search(
        query=query,
        k=limit,
        filter=metadata_filter if metadata_filter else None,
    )

    # Enrich with full speech metadata
    metadata_store = await get_default_metadata_store()
    enriched_results = []

    for result in results:
        speech_id = result["metadata"]["speech_id"]
        speech = await metadata_store.get_speech(speech_id)

        enriched_results.append({
            "chunk_id": result["chunk_id"],
            "speech_id": speech_id,
            "excerpt": result["chunk_text"][:500],  # Limit excerpt to 500 chars
            "relevance_score": result["score"],
            "chunk_index": result["metadata"]["chunk_index"],
            # Speech metadata
            "speaker": result["metadata"]["speaker"],
            "party": result["metadata"]["party"],
            "chamber": result["metadata"]["chamber"],
            "state": result["metadata"].get("state"),
            "date": result["metadata"]["date"],
            "hansard_reference": result["metadata"]["hansard_reference"],
            "title": speech.title if speech else "Unknown",
            "word_count": speech.word_count if speech else 0,
        })

    return {
        "speeches": enriched_results,
        "total_count": len(enriched_results),
        "query": query,
    }


# Tool metadata for FastMCP registration (ChatGPT Developer Mode enhancements)
SEARCH_TOOL_METADATA = {
    "name": "search_hansard_speeches",
    "annotations": ToolAnnotations(
        readOnlyHint=True,
        openWorldHint=False
    ),
    "icon": "🔍",  # Not supported in FastMCP 2.12.5, stored for future use
}
