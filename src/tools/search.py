"""Search tool for parliamentary speeches with ChatGPT Developer Mode optimizations."""

from pydantic import Field
from fastmcp.tools.tool import ToolAnnotations

from models.enums import ChamberEnum, PartyEnum


async def search_hansard_speeches(
    query: str,
    party: PartyEnum | None = Field(
        None,
        description="Filter by political party. Options: Liberal, Labor, Greens, National, Independent"
    ),
    chamber: ChamberEnum | None = Field(
        None,
        description="Filter by chamber. Options: House of Representatives, Senate"
    ),
    start_date: str | None = Field(
        None,
        description="Start date in ISO 8601 format (YYYY-MM-DD). Example: 2024-05-28. "
                    "Only speeches on or after this date will be returned.",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    ),
    end_date: str | None = Field(
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
    # Placeholder implementation - actual vector search would go here
    # This would integrate with LangChain vector store and Cloud SQL pgvector

    return {
        "speeches": [],
        "total_count": 0,
        "message": "Tool implemented with ChatGPT Developer Mode enhancements. "
                   "Vector search integration pending."
    }


# Tool metadata for FastMCP registration
SEARCH_TOOL_METADATA = {
    "name": "search_hansard_speeches",
    "annotations": ToolAnnotations(
        readOnlyHint=True,
        openWorldHint=False
    ),
    "icon": "🔍",
}
