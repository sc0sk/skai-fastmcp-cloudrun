"""Parser for Australian Hansard markdown files with YAML frontmatter."""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import date


class HansardMarkdownParser:
    """Parse Hansard markdown files with YAML frontmatter."""

    def __init__(self, file_path: str):
        """Initialize parser with file path."""
        self.file_path = Path(file_path)
        self.frontmatter: Dict[str, Any] = {}
        self.speech_text: str = ""

    def parse(self) -> Dict[str, Any]:
        """Parse the markdown file and return structured data."""
        content = self.file_path.read_text(encoding='utf-8')

        # Split frontmatter and content
        parts = content.split('---', 2)
        if len(parts) < 3:
            raise ValueError(f"Invalid markdown format in {self.file_path}")

        # Parse YAML frontmatter
        self.frontmatter = yaml.safe_load(parts[1])

        # Extract speech text (after second ---)
        self.speech_text = parts[2].strip()

        # Build structured data
        return {
            'speaker': self.parse_speaker_name(),
            'speaker_id': self.frontmatter.get('speaker_id'),
            'date': self.parse_date(),
            'chamber': self.normalize_chamber(),
            'electorate': self.frontmatter.get('electorate'),
            'party': self.frontmatter.get('party'),
            'debate': self.frontmatter.get('debate'),
            'utterance_id': self.frontmatter.get('utterance_id'),
            'hansard_reference': self.frontmatter.get('source_file'),
            'full_text': self.speech_text,
        }

    def parse_speaker_name(self) -> str:
        """Convert 'LastName, FirstName MP' to 'FirstName LastName'."""
        speaker_raw = self.frontmatter.get('speaker', '')
        # Remove ' MP' suffix if present
        speaker = speaker_raw.replace(' MP', '').strip()

        # Convert "LastName, FirstName" to "FirstName LastName"
        if ',' in speaker:
            parts = [p.strip() for p in speaker.split(',', 1)]
            return f"{parts[1]} {parts[0]}" if len(parts) == 2 else speaker
        return speaker

    def parse_date(self) -> date:
        """Parse date from YYYY-MM-DD format."""
        date_str = self.frontmatter.get('date', '')
        if isinstance(date_str, date):
            return date_str

        # Parse from string
        from datetime import datetime
        return datetime.strptime(date_str, '%Y-%m-%d').date()

    def normalize_chamber(self) -> str:
        """Normalize chamber name to match SpeechMetadata validation."""
        chamber_raw = self.frontmatter.get('chamber', '')

        # Map common variations to canonical names
        chamber_map = {
            'House of Reps': 'House of Representatives',
            'House of Representatives': 'House of Representatives',
            'Senate': 'Senate',
        }

        return chamber_map.get(chamber_raw, chamber_raw)

    def extract_speech_text(self) -> str:
        """Get speech text content."""
        return self.speech_text

    def parse_frontmatter(self) -> Dict[str, Any]:
        """Get parsed frontmatter."""
        return self.frontmatter
