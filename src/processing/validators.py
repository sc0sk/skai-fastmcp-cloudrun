"""Validators for parsing Markdown files with YAML frontmatter (sk-hansard format)."""

from typing import Dict, Any
from datetime import date
from pathlib import Path
import re

import frontmatter  # python-frontmatter package


# Party code mappings (from sk-hansard format to full names)
PARTY_CODES = {
    "LP": "Liberal",
    "ALP": "Labor",
    "GRN": "Greens",
    "NAT": "National",
    "IND": "Independent",
    "PHON": "One Nation",
    "CA": "Centre Alliance",
    "KAP": "Katter's Australian Party",
    "UAP": "United Australia Party",
}

# Chamber normalization
CHAMBER_MAPPINGS = {
    "House of Reps": "House of Representatives",
    "House of Representatives": "House of Representatives",
    "Senate": "Senate",
}

# Valid Australian states/territories
VALID_STATES = {"NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"}


class ValidationError(Exception):
    """Raised when Markdown file validation fails."""
    pass


def parse_markdown_file(file_path: Path) -> Dict[str, Any]:
    """
    Parse Markdown file with YAML frontmatter (sk-hansard format).

    Args:
        file_path: Path to Markdown file

    Returns:
        Dict with keys: speaker, date, debate, chamber, party, electorate,
                       state, full_text

    Raises:
        ValidationError: If file is invalid or missing required fields

    Example:
        >>> from pathlib import Path
        >>> data = parse_markdown_file(Path("data/sk-hansard/speech1.md"))
        >>> data["speaker"]
        'Simon Kennedy'
        >>> data["party"]
        'Liberal'
    """
    if not file_path.exists():
        raise ValidationError(f"File not found: {file_path}")

    if not file_path.suffix == ".md":
        raise ValidationError(f"Not a Markdown file: {file_path}")

    # Parse YAML frontmatter + content
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)
    except Exception as e:
        raise ValidationError(f"Failed to parse {file_path}: {e}")

    # Extract metadata
    metadata = post.metadata
    content = post.content.strip()

    if not content:
        raise ValidationError(f"Empty content in {file_path}")

    # Validate required fields
    required_fields = ["speaker", "date", "debate", "chamber", "party"]
    missing = [f for f in required_fields if f not in metadata]
    if missing:
        raise ValidationError(f"Missing required fields in {file_path}: {missing}")

    # Parse date (format: YYYY-MM-DD or date object)
    date_value = metadata["date"]
    if isinstance(date_value, str):
        try:
            parsed_date = date.fromisoformat(date_value)
        except ValueError:
            raise ValidationError(f"Invalid date format in {file_path}: {date_value}")
    elif isinstance(date_value, date):
        parsed_date = date_value
    else:
        raise ValidationError(f"Invalid date type in {file_path}: {type(date_value)}")

    # Normalize party code
    party_code = metadata["party"]
    party_full = PARTY_CODES.get(party_code, party_code)  # Fallback to code if unknown

    # Normalize chamber
    chamber_raw = metadata["chamber"]
    chamber_normalized = CHAMBER_MAPPINGS.get(chamber_raw, chamber_raw)

    # Validate chamber
    if chamber_normalized not in ["House of Representatives", "Senate"]:
        raise ValidationError(
            f"Invalid chamber in {file_path}: {chamber_raw}. "
            "Must be 'House of Representatives' or 'Senate'"
        )

    # Validate state (optional field)
    state = metadata.get("state")
    if state and state not in VALID_STATES:
        raise ValidationError(
            f"Invalid state in {file_path}: {state}. "
            f"Must be one of {VALID_STATES}"
        )

    # Construct Hansard reference
    hansard_ref = construct_hansard_reference(
        chamber=chamber_normalized,
        date=parsed_date,
        debate=metadata["debate"],
    )

    return {
        "speaker": metadata["speaker"],
        "date": parsed_date,
        "debate": metadata["debate"],
        "chamber": chamber_normalized,
        "party": party_full,
        "electorate": metadata.get("electorate"),
        "state": state,
        "full_text": content,
        "hansard_reference": hansard_ref,
    }


def construct_hansard_reference(
    chamber: str,
    date: date,
    debate: str,
) -> str:
    """
    Construct Hansard reference string.

    Args:
        chamber: Chamber name (normalized)
        date: Speech date
        debate: Debate title

    Returns:
        Hansard reference string

    Example:
        >>> ref = construct_hansard_reference(
        ...     chamber="House of Representatives",
        ...     date=date(2024, 6, 3),
        ...     debate="Appropriation Bill (No. 1) 2024-2025"
        ... )
        >>> ref
        'House of Representatives Hansard, 3 June 2024, Debate: Appropriation Bill (No. 1) 2024-2025'
    """
    # Format date as "3 June 2024"
    date_str = date.strftime("%-d %B %Y")  # Unix format (no leading zero)

    return f"{chamber} Hansard, {date_str}, Debate: {debate}"


def validate_file_batch(directory: Path) -> Dict[str, Any]:
    """
    Validate all Markdown files in a directory.

    Args:
        directory: Path to directory containing Markdown files

    Returns:
        Dict with keys: valid_files, invalid_files, error_messages

    Example:
        >>> from pathlib import Path
        >>> results = validate_file_batch(Path("data/sk-hansard"))
        >>> results["valid_files"]
        65
        >>> results["invalid_files"]
        0
    """
    if not directory.exists():
        raise ValidationError(f"Directory not found: {directory}")

    if not directory.is_dir():
        raise ValidationError(f"Not a directory: {directory}")

    valid_files = []
    invalid_files = []
    error_messages = []

    # Find all .md files
    md_files = list(directory.glob("*.md"))

    for file_path in md_files:
        try:
            parse_markdown_file(file_path)
            valid_files.append(str(file_path))
        except ValidationError as e:
            invalid_files.append(str(file_path))
            error_messages.append(f"{file_path.name}: {e}")

    return {
        "valid_files": len(valid_files),
        "invalid_files": len(invalid_files),
        "total_files": len(md_files),
        "error_messages": error_messages,
    }


def normalize_topic_tags(tags: list) -> list:
    """
    Normalize topic tags (lowercase, strip whitespace).

    Args:
        tags: List of topic tag strings

    Returns:
        List of normalized tags

    Example:
        >>> normalize_topic_tags(["Climate Change", " Budget ", "HEALTH"])
        ['climate change', 'budget', 'health']
    """
    if not tags:
        return []

    return [tag.strip().lower() for tag in tags if tag and tag.strip()]
