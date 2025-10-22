"""MCP tool for fetching full Hansard speech by ID."""

from typing import Dict, Any, Optional

from fastmcp import Context

from src.storage.vector_store import get_default_vector_store


async def fetch_speech(speech_id: str, ctx: Optional[Context] = None) -> Dict[str, Any]:
    """
    Fetch complete Hansard speech by ID.

    Args:
        speech_id: Speech ID from search results

    Returns:
        Complete speech with full text and metadata

    Raises:
        ValueError: If speech_id not found

    Example:
        >>> speech = await fetch_speech("AUH_2024-07-01-p2.s1.per0.reps.u9")
        >>> speech["speaker"]
        'Kennedy, Simon MP'
        >>> speech["content"]
        'Mr Speaker, I rise to speak on...'
    """
    if ctx:
        await ctx.info(f"Fetching speech {speech_id}")

    vector_store = await get_default_vector_store()

    # Search for the speech by ID in metadata
    # Since we don't have a direct get-by-id, we do a metadata filter search
    results = await vector_store.similarity_search(
        query="",  # Empty query - we're filtering by ID only
        k=1,
        filter={"speech_id": speech_id}
    )

    if not results or len(results) == 0:
        if ctx:
            await ctx.warning(f"Speech not found: {speech_id}")
        raise ValueError(f"Speech not found: {speech_id}")

    # Extract the first (and should be only) result
    result = results[0]
    content = result.get("content", result.get("page_content", ""))
    metadata = result.get("metadata", {})

    if ctx:
        word_count = len(content.split())
        await ctx.info(f"Retrieved speech: {metadata.get('speaker', 'Unknown')} ({word_count} words)")

    # Return speech data
    return {
        "id": speech_id,
        "content": content,
        "speaker": metadata.get("speaker", ""),
        "party": metadata.get("party", ""),
        "chamber": metadata.get("chamber", ""),
        "electorate": metadata.get("electorate", ""),
        "date": str(metadata.get("date", "")),
        "debate": metadata.get("debate", ""),
        "themes": metadata.get("themes", ""),
        "tags": metadata.get("tags", ""),
        "summary": metadata.get("summary", ""),
        "speaker_id": metadata.get("speaker_id", ""),
        "word_count": len(content.split()),
    }


async def get_dataset_stats() -> Dict[str, Any]:
    """
    Get Hansard dataset statistics.

    Returns:
        Dataset statistics including speech count, speakers, date range, party breakdown

    Example:
        >>> stats = await get_dataset_stats()
        >>> stats["speech_count"]
        64
        >>> stats["unique_speakers"]
        1
    """
    vector_store = await get_default_vector_store()

    # Get all speeches to calculate stats
    # We do a broad search to get all documents
    all_results = await vector_store.similarity_search(
        query="parliament speech government",  # Generic query to match all speeches
        k=100  # Get up to 100 speeches
    )

    if not all_results:
        return {
            "speech_count": 0,
            "unique_speakers": 0,
            "earliest_date": None,
            "latest_date": None,
            "party_breakdown": {},
            "chamber_breakdown": {},
        }

    # Extract metadata
    speakers = set()
    parties = {}
    chambers = {}
    dates = []

    for result in all_results:
        metadata = result.get("metadata", {})

        speaker = metadata.get("speaker")
        if speaker:
            speakers.add(speaker)

        party = metadata.get("party")
        if party:
            parties[party] = parties.get(party, 0) + 1

        chamber = metadata.get("chamber")
        if chamber:
            chambers[chamber] = chambers.get(chamber, 0) + 1

        date = metadata.get("date")
        if date:
            dates.append(str(date))

    # Calculate stats
    stats = {
        "speech_count": len(all_results),
        "unique_speakers": len(speakers),
        "speakers": list(speakers),
        "earliest_date": min(dates) if dates else None,
        "latest_date": max(dates) if dates else None,
        "party_breakdown": parties,
        "chamber_breakdown": chambers,
    }

    return stats
