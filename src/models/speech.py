"""Pydantic models for Australian Hansard speeches."""

import hashlib
from datetime import date as date_type
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, computed_field, field_validator, ConfigDict


class SpeechMetadata(BaseModel):
    """Pydantic model for speech metadata validation during ingestion."""

    # Core identification
    speech_id: Optional[str] = Field(
        None, description="UUID v4 (auto-generated if not provided)"
    )
    title: str = Field(..., min_length=1, max_length=500, description="Speech title/subject")

    # Content
    full_text: str = Field(..., min_length=10, description="Complete speech transcript")

    # Speaker information
    speaker: str = Field(..., min_length=1, max_length=200, description="MP/Senator name")
    party: str = Field(..., min_length=1, max_length=100, description="Political party")
    chamber: str = Field(..., description="House of Representatives or Senate")
    electorate: Optional[str] = Field(
        None, max_length=100, description="Electorate (House members only)"
    )
    state: Optional[str] = Field(None, description="Australian state/territory")

    # Parliamentary context
    date: date_type = Field(..., description="Speech date (ISO 8601)")
    hansard_reference: str = Field(
        ..., min_length=1, max_length=500, description="Official Hansard citation"
    )
    topic_tags: List[str] = Field(default_factory=list, description="Topic tags")

    # Source
    source_url: Optional[str] = Field(None, max_length=1000, description="Source URL")

    # Computed fields
    @computed_field
    @property
    def word_count(self) -> int:
        """Calculate word count from full_text."""
        return len(self.full_text.split())

    @computed_field
    @property
    def content_hash(self) -> str:
        """Generate SHA-256 hash for deduplication."""
        return hashlib.sha256(self.full_text.encode("utf-8")).hexdigest()

    # Validators
    @field_validator("chamber")
    @classmethod
    def validate_chamber(cls, v: str) -> str:
        """Validate chamber is valid Australian chamber."""
        valid_chambers = {"House of Representatives", "Senate"}
        if v not in valid_chambers:
            raise ValueError(f"chamber must be one of: {valid_chambers}")
        return v

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: Optional[str]) -> Optional[str]:
        """Validate state is valid Australian state/territory."""
        if v is None:
            return v
        valid_states = {"NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"}
        if v not in valid_states:
            raise ValueError(f"state must be one of: {valid_states}")
        return v

    @field_validator("topic_tags")
    @classmethod
    def validate_topic_tags(cls, v: List[str]) -> List[str]:
        """Normalize topic tags (lowercase, strip whitespace)."""
        return [tag.strip().lower() for tag in v if tag.strip()]

    def model_post_init(self, __context) -> None:
        """Validate electorate based on chamber."""
        if self.chamber == "Senate" and self.electorate is not None:
            raise ValueError("Senators cannot have electorate (must be NULL)")
        if self.chamber == "House of Representatives" and self.electorate is None:
            raise ValueError("House members must have electorate")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "Second Reading: Climate Change Bill 2024",
                    "full_text": "Mr Speaker, I rise to speak on the Climate Change Bill...",
                    "speaker": "Anthony Albanese",
                    "party": "Labor",
                    "chamber": "House of Representatives",
                    "electorate": "Grayndler",
                    "state": "NSW",
                    "date": "2024-03-23",
                    "hansard_reference": "House Hansard, 23 March 2024, p.145",
                    "topic_tags": ["climate change", "environment", "energy policy"],
                    "source_url": "https://www.aph.gov.au/Parliamentary_Business/Hansard",
                }
            ]
        }
    }


class SpeechDetail(SpeechMetadata):
    """Extended speech model with full details (returned by get_speech tool)."""

    ingestion_timestamp: Optional[str] = Field(
        None, description="When speech was ingested (ISO 8601)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "speech_id": "550e8400-e29b-41d4-a716-446655440000",
                    "title": "Second Reading: Climate Change Bill 2024",
                    "full_text": "Mr Speaker, I rise to speak on the Climate Change Bill...",
                    "speaker": "Anthony Albanese",
                    "party": "Labor",
                    "chamber": "House of Representatives",
                    "electorate": "Grayndler",
                    "state": "NSW",
                    "date": "2024-03-23",
                    "hansard_reference": "House Hansard, 23 March 2024, p.145",
                    "topic_tags": ["climate change", "environment", "energy policy"],
                    "source_url": "https://www.aph.gov.au/Parliamentary_Business/Hansard",
                    "ingestion_timestamp": "2024-03-24T10:30:00Z",
                }
            ]
        }
    }


class SpeechChunkMetadata(BaseModel):
    """Metadata for individual speech chunks (used internally by LangChain)."""

    # Chunk identification
    chunk_id: Optional[str] = Field(None, description="UUID v4 (auto-generated)")
    speech_id: str = Field(..., description="Parent speech UUID")
    chunk_index: int = Field(..., ge=0, description="Position in speech (0-based)")
    chunk_size: int = Field(..., gt=0, description="Character count")

    # Denormalized metadata for filtering
    speaker: str = Field(..., description="Speaker name")
    party: str = Field(..., description="Political party")
    chamber: str = Field(..., description="Chamber")
    date: date_type = Field(..., description="Speech date")
    topic_tags: List[str] = Field(default_factory=list, description="Topic tags")

    # Additional metadata
    hansard_reference: str = Field(..., description="Official citation")
    title: str = Field(..., description="Speech title")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "speech_id": "550e8400-e29b-41d4-a716-446655440000",
                    "chunk_index": 0,
                    "chunk_size": 782,
                    "speaker": "Anthony Albanese",
                    "party": "Labor",
                    "chamber": "House of Representatives",
                    "date": "2024-03-23",
                    "topic_tags": ["climate change", "environment"],
                    "hansard_reference": "House Hansard, 23 March 2024, p.145",
                    "title": "Second Reading: Climate Change Bill 2024",
                }
            ]
        }
    }
