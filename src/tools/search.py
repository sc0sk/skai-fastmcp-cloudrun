"""MCP tool for searching Hansard speeches using hybrid vector + metadata search."""

from typing import List, Optional, Dict, Any
from datetime import date as date_type

from src.storage.vector_store import get_default_vector_store
from src.storage.metadata_store import get_default_metadata_store


async def search_speeches(
    query: str,
    limit: int = 10,
    speaker: Optional[str] = None,
    party: Optional[str] = None,
    chamber: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Search Hansard speeches using semantic vector search with metadata filters.

    Args:
        query: Search query text (semantic search)
        limit: Maximum number of results (default: 10, max: 50)
        speaker: Filter by speaker name (partial match, case-insensitive)
        party: Filter by political party (exact match)
        chamber: Filter by chamber ("House of Representatives" or "Senate")
        date_from: Filter speeches from this date onwards (ISO format: YYYY-MM-DD)
        date_to: Filter speeches up to this date (ISO format: YYYY-MM-DD)

    Returns:
        List of search results with speech excerpts, metadata, and relevance scores

    Example:
        >>> results = await search_speeches(
        ...     query="climate change policy",
        ...     party="Liberal",
        ...     chamber="House of Representatives",
        ...     limit=5
        ... )
        >>> results[0]["speaker"]
        'Simon Kennedy'
        >>> results[0]["relevance_score"]
        0.87
    """
    # Validate limit
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if limit > 50:
        limit = 50

    # Build metadata filter
    metadata_filter = {}
    if speaker:
        metadata_filter["speaker"] = speaker
    if party:
        metadata_filter["party"] = party
    if chamber:
        metadata_filter["chamber"] = chamber
    if date_from:
        # Parse ISO date
        try:
            date_from_parsed = date_type.fromisoformat(date_from)
            metadata_filter["date_from"] = date_from_parsed.isoformat()
        except ValueError:
            raise ValueError(f"Invalid date_from format: {date_from}. Use YYYY-MM-DD")
    if date_to:
        try:
            date_to_parsed = date_type.fromisoformat(date_to)
            metadata_filter["date_to"] = date_to_parsed.isoformat()
        except ValueError:
            raise ValueError(f"Invalid date_to format: {date_to}. Use YYYY-MM-DD")

    # Perform vector similarity search
    vector_store = await get_default_vector_store()
    results = await vector_store.similarity_search(
        query=query,
        k=limit,
        filter=metadata_filter if metadata_filter else None,
    )

    # Enrich with full speech metadata from metadata store
    metadata_store = await get_default_metadata_store()
    enriched_results = []

    for result in results:
        speech_id = result["metadata"]["speech_id"]

        # Get full speech metadata
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

    return enriched_results
