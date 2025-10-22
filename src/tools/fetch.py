"""Fetch tool for retrieving complete parliamentary speech text."""

from fastmcp.tools.tool import ToolAnnotations


async def fetch_hansard_speech(
    speech_id: str,
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
    # Placeholder implementation - actual database fetch would go here
    # This would retrieve from Cloud SQL PostgreSQL

    return {
        "id": speech_id,
        "message": "Tool implemented with ChatGPT Developer Mode enhancements. "
                   "Database integration pending."
    }


# Tool metadata for FastMCP registration
FETCH_TOOL_METADATA = {
    "name": "fetch_hansard_speech",
    "annotations": ToolAnnotations(
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=False
    ),
    "icon": "📄",
}
