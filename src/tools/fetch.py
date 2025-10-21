"""MCP tool for fetching full Hansard speech by ID."""

from typing import Dict, Any, Optional

from src.storage.metadata_store import get_default_metadata_store
from src.models.speech import SpeechMetadata


async def fetch_speech(speech_id: str) -> Dict[str, Any]:
    """
    Fetch complete Hansard speech by ID.

    Args:
        speech_id: UUID of the speech to retrieve

    Returns:
        Complete speech with full text and metadata

    Raises:
        ValueError: If speech_id not found

    Example:
        >>> speech = await fetch_speech("550e8400-e29b-41d4-a716-446655440000")
        >>> speech["speaker"]
        'Simon Kennedy'
        >>> speech["full_text"]
        'Mr Speaker, I rise to speak on...'
    """
    metadata_store = await get_default_metadata_store()

    # Retrieve speech from database
    speech: Optional[SpeechMetadata] = await metadata_store.get_speech(speech_id)

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


async def get_dataset_stats() -> Dict[str, Any]:
    """
    Get Hansard dataset statistics.

    Returns:
        Dataset statistics including speech count, speakers, date range, party breakdown

    Example:
        >>> stats = await get_dataset_stats()
        >>> stats["speech_count"]
        65
        >>> stats["unique_speakers"]
        1
    """
    metadata_store = await get_default_metadata_store()

    # Get statistics from metadata store
    stats = await metadata_store.get_stats()

    return stats
