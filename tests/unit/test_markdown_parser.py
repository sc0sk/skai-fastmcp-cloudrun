"""Unit tests for markdown parser."""
import pytest
from pathlib import Path
from tools.ingest.markdown_parser import parse_markdown_file
from models.speech import SpeechFrontmatter


def test_parse_valid_markdown():
    """Test parsing valid markdown with frontmatter."""
    fixture_path = "tests/fixtures/markdown/valid_speech.md"
    metadata, content = parse_markdown_file(fixture_path)
    
    assert isinstance(metadata, SpeechFrontmatter)
    assert metadata.speech_id == "test-001"
    assert metadata.speaker == "Anthony Albanese"
    assert metadata.party == "Labor"
    assert metadata.chamber == "REPS"
    assert metadata.title == "Climate Change Bill 2024 - Second Reading"
    assert content.startswith("Mr Speaker")


def test_parse_no_frontmatter():
    """Test parsing markdown without frontmatter."""
    fixture_path = "tests/fixtures/markdown/no_frontmatter.md"
    
    with pytest.raises(ValueError, match="missing YAML frontmatter"):
        parse_markdown_file(fixture_path)


def test_parse_malformed_yaml():
    """Test parsing markdown with malformed YAML."""
    fixture_path = "tests/fixtures/markdown/malformed_yaml.md"
    
    with pytest.raises(ValueError, match="Invalid frontmatter"):
        parse_markdown_file(fixture_path)


def test_parse_missing_fields():
    """Test parsing markdown with missing required fields."""
    fixture_path = "tests/fixtures/markdown/missing_fields.md"
    
    with pytest.raises(ValueError, match="Invalid frontmatter"):
        parse_markdown_file(fixture_path)


def test_parse_nonexistent_file():
    """Test parsing non-existent file."""
    with pytest.raises(FileNotFoundError):
        parse_markdown_file("nonexistent.md")
