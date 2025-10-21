"""Pydantic models for MCP tool results."""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class IngestionResult(BaseModel):
    """Result returned by ingest_markdown_speeches tool."""

    speeches_processed: int = Field(..., ge=0, description="Total speeches processed")
    chunks_created: int = Field(..., ge=0, description="Total chunks created")
    vectors_stored: int = Field(..., ge=0, description="Total vectors embedded and stored")
    duplicates_skipped: int = Field(..., ge=0, description="Speeches skipped (already exist)")
    errors: List[str] = Field(default_factory=list, description="Error messages (if any)")
    processing_time_seconds: float = Field(..., ge=0.0, description="Total processing time")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "speeches_processed": 65,
                    "chunks_created": 203,
                    "vectors_stored": 203,
                    "duplicates_skipped": 0,
                    "errors": [],
                    "processing_time_seconds": 45.3,
                }
            ]
        }
    }


class SearchResult(BaseModel):
    """Single search result returned by search_speeches tool."""

    # Identification
    speech_id: str = Field(..., description="Parent speech UUID")
    chunk_id: str = Field(..., description="Chunk UUID")

    # Content
    excerpt: str = Field(
        ..., max_length=1000, description="Chunk text excerpt (up to 1000 chars)"
    )

    # Metadata
    speaker: str = Field(..., description="Speaker name")
    party: str = Field(..., description="Political party")
    chamber: str = Field(..., description="Chamber")
    date: date = Field(..., description="Speech date")
    title: str = Field(..., description="Speech title")
    hansard_reference: str = Field(..., description="Official Hansard citation")
    topic_tags: List[str] = Field(default_factory=list, description="Topic tags")

    # Search metrics
    relevance_score: float = Field(
        ..., ge=0.0, le=1.0, description="Similarity score (0-1)"
    )
    chunk_index: int = Field(..., ge=0, description="Position in speech")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "speech_id": "550e8400-e29b-41d4-a716-446655440000",
                    "chunk_id": "660e8400-e29b-41d4-a716-446655440001",
                    "excerpt": "Mr Speaker, climate change is the defining challenge of our time...",
                    "speaker": "Anthony Albanese",
                    "party": "Labor",
                    "chamber": "House of Representatives",
                    "date": "2024-03-23",
                    "title": "Second Reading: Climate Change Bill 2024",
                    "hansard_reference": "House Hansard, 23 March 2024, p.145",
                    "topic_tags": ["climate change", "environment"],
                    "relevance_score": 0.87,
                    "chunk_index": 0,
                }
            ]
        }
    }


class DatasetStats(BaseModel):
    """Dataset statistics returned by hansard://dataset/stats resource."""

    speech_count: int = Field(..., ge=0, description="Total speeches in database")
    chunk_count: int = Field(..., ge=0, description="Total chunks in database")
    unique_speakers: int = Field(..., ge=0, description="Number of unique speakers")
    date_range: dict = Field(..., description="Date range {earliest, latest}")
    chambers: dict = Field(..., description="Speech counts by chamber")
    parties: dict = Field(..., description="Speech counts by party")
    topic_distribution: dict = Field(..., description="Top 10 topics with counts")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "speech_count": 65,
                    "chunk_count": 203,
                    "unique_speakers": 1,
                    "date_range": {"earliest": "2024-05-28", "latest": "2025-10-09"},
                    "chambers": {"House of Representatives": 65, "Senate": 0},
                    "parties": {"Liberal": 65},
                    "topic_distribution": {
                        "economy": 25,
                        "energy": 18,
                        "housing": 12,
                        "taxation": 10,
                    },
                }
            ]
        }
    }
