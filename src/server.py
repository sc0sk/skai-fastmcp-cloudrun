"""FastMCP server for Australian Hansard RAG system."""

from fastmcp import FastMCP
from contextlib import asynccontextmanager
from typing import Dict, Any

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tools.search import search_speeches
from src.tools.fetch import fetch_speech, get_dataset_stats


# Lifespan context manager for global resources
@asynccontextmanager
async def lifespan(app: FastMCP):
    """
    Manage global resources (database connections, embedding models).

    Note:
        Connection pools are lazily initialized on first use.
        This context manager ensures proper cleanup on shutdown.
    """
    # Startup: Resources are lazily initialized
    print("🚀 FastMCP Hansard RAG Server starting...")

    yield

    # Shutdown: Clean up resources
    print("🛑 FastMCP Hansard RAG Server shutting down...")
    from src.storage.metadata_store import _default_metadata_store
    from src.storage.vector_store import _default_vector_store

    if _default_metadata_store:
        await _default_metadata_store.close()

    if _default_vector_store:
        await _default_vector_store.close()


# Initialize FastMCP server
mcp = FastMCP("Australian Hansard RAG")


# Tool: Search speeches
@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": True,  # Queries external database
    }
)
async def search(
    query: str,
    limit: int = 10,
    speaker: str | None = None,
    party: str | None = None,
    chamber: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> Dict[str, Any]:
    """
    Search Australian Hansard speeches using semantic search with metadata filters.

    Performs vector similarity search over parliamentary speech transcripts,
    returning relevant excerpts with speaker metadata and relevance scores.

    Args:
        query: Search query text (e.g., "climate change policy", "housing affordability")
        limit: Maximum results to return (1-50, default: 10)
        speaker: Filter by speaker name (case-insensitive partial match)
        party: Filter by political party (Liberal, Labor, Greens, National, Independent)
        chamber: Filter by chamber ("House of Representatives" or "Senate")
        date_from: Filter speeches from date onwards (ISO format: YYYY-MM-DD)
        date_to: Filter speeches up to date (ISO format: YYYY-MM-DD)

    Returns:
        List of search results with excerpts, metadata, and relevance scores (0-1)

    Examples:
        Search for climate policy speeches:
        >>> search(query="climate change policy", limit=5)

        Find Labor speeches about housing:
        >>> search(query="housing affordability", party="Labor", limit=10)

        Search House of Representatives speeches in 2024:
        >>> search(
        ...     query="budget",
        ...     chamber="House of Representatives",
        ...     date_from="2024-01-01",
        ...     date_to="2024-12-31"
        ... )
    """
    results = await search_speeches(
        query=query,
        limit=limit,
        speaker=speaker,
        party=party,
        chamber=chamber,
        date_from=date_from,
        date_to=date_to,
    )

    return {
        "results": results,
        "count": len(results),
        "query": query,
        "filters": {
            "speaker": speaker,
            "party": party,
            "chamber": chamber,
            "date_from": date_from,
            "date_to": date_to,
        },
    }


# Tool: Fetch speech
@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": True,  # Queries external database
    }
)
async def fetch(speech_id: str) -> Dict[str, Any]:
    """
    Fetch complete Hansard speech by ID.

    Retrieves the full text and metadata for a specific parliamentary speech.
    Use this after finding speech_id from search results to get the complete transcript.

    Args:
        speech_id: UUID of the speech (obtained from search results)

    Returns:
        Complete speech with full text, speaker metadata, and parliamentary context

    Example:
        >>> fetch(speech_id="550e8400-e29b-41d4-a716-446655440000")
        {
            "speech_id": "550e8400-e29b-41d4-a716-446655440000",
            "title": "Second Reading: Climate Change Bill 2024",
            "full_text": "Mr Speaker, I rise to speak...",
            "speaker": "Simon Kennedy",
            "party": "Liberal",
            "chamber": "House of Representatives",
            "date": "2024-06-03",
            "word_count": 1523,
            ...
        }
    """
    return await fetch_speech(speech_id)


# Resource: Dataset statistics
@mcp.resource("hansard://dataset/stats")
async def dataset_stats() -> str:
    """
    Get Hansard dataset statistics.

    Returns overview statistics about the speech corpus including
    speech count, unique speakers, date range, and party distribution.

    Example:
        >>> dataset_stats()
        {
            "speech_count": 65,
            "unique_speakers": 1,
            "earliest_date": "2024-05-28",
            "latest_date": "2025-10-09",
            "party_breakdown": {"Liberal": 65}
        }
    """
    stats = await get_dataset_stats()
    # Return as JSON string for MCP resource
    import json
    return json.dumps(stats, indent=2)


if __name__ == "__main__":
    # Run server with FastMCP CLI
    # Usage: fastmcp dev src/server.py
    mcp.run()
