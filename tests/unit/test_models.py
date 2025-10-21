"""Unit tests for Pydantic models."""

import pytest
from datetime import date
from pydantic import ValidationError

from src.models.speech import SpeechMetadata, SpeechDetail, SpeechChunkMetadata
from src.models.results import IngestionResult, SearchResult, DatasetStats


class TestSpeechMetadata:
    """Tests for SpeechMetadata model."""

    def test_valid_house_speech(self):
        """Test valid House of Representatives speech."""
        speech = SpeechMetadata(
            title="Test Speech",
            full_text="This is a test speech about climate change policy.",
            speaker="Anthony Albanese",
            party="Labor",
            chamber="House of Representatives",
            electorate="Grayndler",
            state="NSW",
            date=date(2024, 3, 23),
            hansard_reference="House Hansard, 23 March 2024, p.145",
            topic_tags=["climate change", "environment"],
        )

        assert speech.title == "Test Speech"
        assert speech.chamber == "House of Representatives"
        assert speech.electorate == "Grayndler"
        assert speech.word_count == 9
        assert len(speech.content_hash) == 64  # SHA-256 hex digest length
        assert speech.topic_tags == ["climate change", "environment"]

    def test_valid_senate_speech(self):
        """Test valid Senate speech."""
        speech = SpeechMetadata(
            title="Senate Committee Report",
            full_text="As a Senator, I present this committee report on energy policy.",
            speaker="Penny Wong",
            party="Labor",
            chamber="Senate",
            electorate=None,  # Senators don't have electorates
            state="SA",
            date=date(2024, 4, 15),
            hansard_reference="Senate Hansard, 15 April 2024, p.82",
        )

        assert speech.chamber == "Senate"
        assert speech.electorate is None
        assert speech.state == "SA"

    def test_invalid_chamber(self):
        """Test validation fails for invalid chamber."""
        with pytest.raises(ValidationError) as exc_info:
            SpeechMetadata(
                title="Test",
                full_text="Test speech content here.",
                speaker="Test Speaker",
                party="Test Party",
                chamber="Invalid Chamber",
                state="NSW",
                date=date(2024, 1, 1),
                hansard_reference="Test ref",
            )

        errors = exc_info.value.errors()
        assert any("chamber" in str(err) for err in errors)

    def test_invalid_state(self):
        """Test validation fails for invalid state."""
        with pytest.raises(ValidationError) as exc_info:
            SpeechMetadata(
                title="Test",
                full_text="Test speech content here.",
                speaker="Test Speaker",
                party="Test Party",
                chamber="Senate",
                state="INVALID",
                date=date(2024, 1, 1),
                hansard_reference="Test ref",
            )

        errors = exc_info.value.errors()
        assert any("state" in str(err) for err in errors)

    def test_all_valid_states(self):
        """Test all valid Australian states/territories."""
        valid_states = ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"]

        for state_code in valid_states:
            speech = SpeechMetadata(
                title="Test",
                full_text="Test speech content.",
                speaker="Test Speaker",
                party="Test Party",
                chamber="Senate",
                state=state_code,
                date=date(2024, 1, 1),
                hansard_reference="Test ref",
            )
            assert speech.state == state_code

    def test_senator_with_electorate_fails(self):
        """Test validation fails when Senator has electorate."""
        with pytest.raises(ValueError, match="Senators cannot have electorate"):
            SpeechMetadata(
                title="Test",
                full_text="Test speech content.",
                speaker="Penny Wong",
                party="Labor",
                chamber="Senate",
                electorate="Adelaide",  # Invalid for Senator
                state="SA",
                date=date(2024, 1, 1),
                hansard_reference="Test ref",
            )

    def test_house_member_without_electorate_fails(self):
        """Test validation fails when House member lacks electorate."""
        with pytest.raises(ValueError, match="House members must have electorate"):
            SpeechMetadata(
                title="Test",
                full_text="Test speech content.",
                speaker="Anthony Albanese",
                party="Labor",
                chamber="House of Representatives",
                electorate=None,  # Invalid for House member
                state="NSW",
                date=date(2024, 1, 1),
                hansard_reference="Test ref",
            )

    def test_topic_tags_normalization(self):
        """Test topic tags are normalized (lowercase, stripped)."""
        speech = SpeechMetadata(
            title="Test",
            full_text="Test speech content.",
            speaker="Test Speaker",
            party="Test Party",
            chamber="Senate",
            state="NSW",
            date=date(2024, 1, 1),
            hansard_reference="Test ref",
            topic_tags=["  Climate Change  ", "ENVIRONMENT", "Energy Policy"],
        )

        assert speech.topic_tags == ["climate change", "environment", "energy policy"]

    def test_content_hash_consistency(self):
        """Test content hash is deterministic."""
        speech1 = SpeechMetadata(
            title="Test1",
            full_text="Identical content",
            speaker="Speaker1",
            party="Party1",
            chamber="Senate",
            state="NSW",
            date=date(2024, 1, 1),
            hansard_reference="Ref1",
        )

        speech2 = SpeechMetadata(
            title="Test2",  # Different title
            full_text="Identical content",  # Same content
            speaker="Speaker2",
            party="Party2",
            chamber="House of Representatives",
            electorate="Test",
            state="VIC",
            date=date(2024, 2, 1),
            hansard_reference="Ref2",
        )

        # Content hash should be same (depends only on full_text)
        assert speech1.content_hash == speech2.content_hash

    def test_word_count_calculation(self):
        """Test word count is calculated correctly."""
        speech = SpeechMetadata(
            title="Test",
            full_text="One two three four five six seven eight nine ten.",
            speaker="Test Speaker",
            party="Test Party",
            chamber="Senate",
            state="NSW",
            date=date(2024, 1, 1),
            hansard_reference="Test ref",
        )

        assert speech.word_count == 10


class TestSpeechChunkMetadata:
    """Tests for SpeechChunkMetadata model."""

    def test_valid_chunk_metadata(self):
        """Test valid chunk metadata."""
        chunk = SpeechChunkMetadata(
            speech_id="550e8400-e29b-41d4-a716-446655440000",
            chunk_index=0,
            chunk_size=782,
            speaker="Anthony Albanese",
            party="Labor",
            chamber="House of Representatives",
            date=date(2024, 3, 23),
            topic_tags=["climate change"],
            hansard_reference="House Hansard, 23 March 2024, p.145",
            title="Test Speech",
        )

        assert chunk.chunk_index == 0
        assert chunk.chunk_size == 782

    def test_negative_chunk_index_fails(self):
        """Test validation fails for negative chunk index."""
        with pytest.raises(ValidationError):
            SpeechChunkMetadata(
                speech_id="550e8400-e29b-41d4-a716-446655440000",
                chunk_index=-1,  # Invalid
                chunk_size=100,
                speaker="Test",
                party="Test",
                chamber="Senate",
                date=date(2024, 1, 1),
                hansard_reference="Test",
                title="Test",
            )

    def test_zero_chunk_size_fails(self):
        """Test validation fails for zero/negative chunk size."""
        with pytest.raises(ValidationError):
            SpeechChunkMetadata(
                speech_id="550e8400-e29b-41d4-a716-446655440000",
                chunk_index=0,
                chunk_size=0,  # Invalid
                speaker="Test",
                party="Test",
                chamber="Senate",
                date=date(2024, 1, 1),
                hansard_reference="Test",
                title="Test",
            )


class TestIngestionResult:
    """Tests for IngestionResult model."""

    def test_valid_ingestion_result(self):
        """Test valid ingestion result."""
        result = IngestionResult(
            speeches_processed=65,
            chunks_created=203,
            vectors_stored=203,
            duplicates_skipped=0,
            errors=[],
            processing_time_seconds=45.3,
        )

        assert result.speeches_processed == 65
        assert result.chunks_created == 203
        assert len(result.errors) == 0

    def test_ingestion_with_errors(self):
        """Test ingestion result with errors."""
        result = IngestionResult(
            speeches_processed=60,
            chunks_created=180,
            vectors_stored=180,
            duplicates_skipped=2,
            errors=["Failed to parse file1.md", "Invalid metadata in file2.md"],
            processing_time_seconds=42.1,
        )

        assert len(result.errors) == 2
        assert result.duplicates_skipped == 2


class TestSearchResult:
    """Tests for SearchResult model."""

    def test_valid_search_result(self):
        """Test valid search result."""
        result = SearchResult(
            speech_id="550e8400-e29b-41d4-a716-446655440000",
            chunk_id="660e8400-e29b-41d4-a716-446655440001",
            excerpt="Climate change is the defining challenge...",
            speaker="Anthony Albanese",
            party="Labor",
            chamber="House of Representatives",
            date=date(2024, 3, 23),
            title="Climate Change Bill 2024",
            hansard_reference="House Hansard, 23 March 2024, p.145",
            topic_tags=["climate change"],
            relevance_score=0.87,
            chunk_index=0,
        )

        assert result.relevance_score == 0.87
        assert 0.0 <= result.relevance_score <= 1.0

    def test_relevance_score_out_of_range(self):
        """Test validation fails for relevance score out of range."""
        with pytest.raises(ValidationError):
            SearchResult(
                speech_id="550e8400-e29b-41d4-a716-446655440000",
                chunk_id="660e8400-e29b-41d4-a716-446655440001",
                excerpt="Test excerpt",
                speaker="Test",
                party="Test",
                chamber="Senate",
                date=date(2024, 1, 1),
                title="Test",
                hansard_reference="Test",
                relevance_score=1.5,  # Invalid (>1.0)
                chunk_index=0,
            )
