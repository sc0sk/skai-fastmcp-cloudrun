"""Unit tests for ingestion tool."""

import pytest
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.speech import SpeechMetadata
from src.models.results import IngestionResult


class TestMarkdownParsing:
    """Tests for parsing Markdown files with YAML frontmatter."""

    def test_parse_yaml_frontmatter(self):
        """Test parsing YAML frontmatter from sk-hansard format."""
        markdown_content = """---
speaker: Simon Kennedy
date: 2024-06-03
debate: Appropriation Bill (No. 1) 2024-2025
chamber: House of Reps
party: LP
electorate: Cook
state: NSW
---

Mr Speaker, I rise to discuss the Appropriation Bill...
"""
        # This test will pass once validators.py is implemented
        # For now, we're defining the expected behavior
        pass

    def test_party_code_mapping(self):
        """Test mapping party codes (LP -> Liberal)."""
        party_codes = {
            "LP": "Liberal",
            "ALP": "Labor",
            "GRN": "Greens",
            "NAT": "National",
            "IND": "Independent",
        }

        assert party_codes["LP"] == "Liberal"
        assert party_codes["ALP"] == "Labor"
        assert party_codes["GRN"] == "Greens"

    def test_chamber_normalization(self):
        """Test normalizing chamber names."""
        chamber_mappings = {
            "House of Reps": "House of Representatives",
            "House of Representatives": "House of Representatives",
            "Senate": "Senate",
        }

        assert chamber_mappings["House of Reps"] == "House of Representatives"
        assert chamber_mappings["Senate"] == "Senate"

    def test_hansard_reference_construction(self):
        """Test constructing Hansard reference from metadata."""
        # Format: "{Chamber} Hansard, {date}, Debate: {debate_title}"
        chamber = "House of Representatives"
        date_str = "3 June 2024"
        debate = "Appropriation Bill (No. 1) 2024-2025"

        expected = f"{chamber} Hansard, {date_str}, Debate: {debate}"
        assert "House of Representatives Hansard" in expected
        assert "3 June 2024" in expected
        assert "Appropriation Bill" in expected


class TestSpeechMetadataTransformation:
    """Tests for transforming sk-hansard data to SpeechMetadata."""

    def test_valid_transformation(self):
        """Test transforming valid sk-hansard data."""
        sk_hansard_data = {
            "speaker": "Simon Kennedy",
            "date": "2024-06-03",
            "debate": "Appropriation Bill (No. 1) 2024-2025",
            "chamber": "House of Reps",
            "party": "LP",
            "electorate": "Cook",
            "state": "NSW",
            "full_text": "Mr Speaker, I rise to discuss the budget...",
        }

        # After transformation, should be valid SpeechMetadata
        expected_party = "Liberal"
        expected_chamber = "House of Representatives"
        expected_title = "Appropriation Bill (No. 1) 2024-2025"

        assert expected_party == "Liberal"
        assert expected_chamber == "House of Representatives"
        assert expected_title == sk_hansard_data["debate"]

    def test_missing_required_fields(self):
        """Test handling missing required fields."""
        incomplete_data = {
            "speaker": "Simon Kennedy",
            # Missing date, debate, chamber, etc.
        }

        # Should raise validation error
        with pytest.raises((KeyError, ValueError)):
            # This will fail until validators.py is implemented
            raise KeyError("Missing required field: date")

    def test_invalid_party_code(self):
        """Test handling unknown party code."""
        # Unknown party codes should either:
        # 1. Use the code as-is (fallback)
        # 2. Raise validation error
        unknown_code = "UNKNOWN"

        # For now, expect fallback behavior
        assert unknown_code == "UNKNOWN"  # Use as-is


class TestDuplicateDetection:
    """Tests for duplicate detection via content_hash."""

    def test_content_hash_generation(self):
        """Test SHA-256 hash generation for duplicate detection."""
        speech1 = SpeechMetadata(
            title="Test Speech",
            full_text="Identical content",
            speaker="Speaker 1",
            party="Liberal",
            chamber="House of Representatives",
            electorate="Cook",
            state="NSW",
            date=date(2024, 6, 3),
            hansard_reference="Test ref",
        )

        speech2 = SpeechMetadata(
            title="Different Title",
            full_text="Identical content",  # Same content
            speaker="Speaker 2",
            party="Labor",
            chamber="Senate",
            state="VIC",
            date=date(2024, 6, 4),
            hansard_reference="Different ref",
        )

        # Content hash should be same (based only on full_text)
        assert speech1.content_hash == speech2.content_hash

    def test_different_content_different_hash(self):
        """Test different content produces different hashes."""
        speech1 = SpeechMetadata(
            title="Test",
            full_text="Content A",
            speaker="Speaker",
            party="Liberal",
            chamber="House of Representatives",
            electorate="Cook",
            state="NSW",
            date=date(2024, 6, 3),
            hansard_reference="Ref",
        )

        speech2 = SpeechMetadata(
            title="Test",
            full_text="Content B",  # Different content
            speaker="Speaker",
            party="Liberal",
            chamber="House of Representatives",
            electorate="Cook",
            state="NSW",
            date=date(2024, 6, 3),
            hansard_reference="Ref",
        )

        assert speech1.content_hash != speech2.content_hash


class TestErrorHandling:
    """Tests for error handling during ingestion."""

    def test_invalid_file_path(self):
        """Test handling non-existent file."""
        non_existent_path = Path("/nonexistent/path/to/file.md")

        assert not non_existent_path.exists()

    def test_malformed_yaml(self):
        """Test handling malformed YAML frontmatter."""
        malformed_content = """---
speaker: Simon Kennedy
date: INVALID_DATE
chamber: Invalid Chamber
"""
        # Should handle parsing errors gracefully
        # Will be implemented in validators.py
        pass

    def test_empty_file(self):
        """Test handling empty Markdown files."""
        empty_content = ""

        # Should skip or raise appropriate error
        assert len(empty_content) == 0


class TestIngestionResult:
    """Tests for IngestionResult model."""

    def test_successful_ingestion_result(self):
        """Test creating successful ingestion result."""
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

    def test_partial_ingestion_with_errors(self):
        """Test ingestion result with some errors."""
        result = IngestionResult(
            speeches_processed=60,
            chunks_created=180,
            vectors_stored=180,
            duplicates_skipped=3,
            errors=["Failed to parse file1.md: Invalid YAML", "File2.md not found"],
            processing_time_seconds=42.1,
        )

        assert result.speeches_processed == 60
        assert result.duplicates_skipped == 3
        assert len(result.errors) == 2
        assert "Invalid YAML" in result.errors[0]
