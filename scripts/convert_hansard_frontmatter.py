#!/usr/bin/env python3
"""
Convert existing Hansard markdown files to new frontmatter format.

Transforms rich metadata files from sk-hansard-converter format to
the simplified frontmatter schema required by ingest_markdown_file tool.

Required fields for new format:
- speech_id: Unique identifier
- speaker: Speaker name
- party: Political party (Liberal, Labor, Greens, National, Independent)
- chamber: Chamber (REPS or SENATE)
- date: ISO 8601 date
- title: Speech title/topic
- state: Electoral state (optional)
- hansard_reference: Hansard page reference (optional)
"""

import frontmatter
import sys
from pathlib import Path
from typing import Dict, Any

# Party mapping from old format to new PartyEnum
PARTY_MAP = {
    "LP": "Liberal",
    "ALP": "Labor",
    "GRN": "Greens",
    "NATS": "National",
    "NAT": "National",
    "IND": "Independent",
    "KAP": "Independent",  # Katter's Australian Party → Independent
    "PHON": "Independent",  # Pauline Hanson's One Nation → Independent
    "CA": "Independent",  # Centre Alliance → Independent
}

# Chamber mapping
CHAMBER_MAP = {
    "House of Reps": "REPS",
    "Senate": "SENATE",
}


def extract_title(old_metadata: Dict[str, Any], content: str) -> str:
    """
    Extract a meaningful title from metadata or content.

    Priority:
    1. summary field (first 500 chars)
    2. speech_type + date
    3. First line of content
    """
    # Try summary first
    if "summary" in old_metadata:
        summary = old_metadata["summary"]
        if len(summary) > 500:
            summary = summary[:497] + "..."
        return summary

    # Try speech_type + debate
    if "speech_type" in old_metadata:
        title = old_metadata["speech_type"].replace("-", " ").title()
        if "debate" in old_metadata:
            title += f": {old_metadata['debate']}"
        return title[:500]

    # Fallback to first line of content
    first_line = content.split("\n")[0].strip()
    if len(first_line) > 500:
        first_line = first_line[:497] + "..."
    return first_line if first_line else "Parliamentary Speech"


def convert_frontmatter(input_file: Path, output_file: Path) -> None:
    """Convert a single markdown file to new frontmatter format."""

    # Read existing file
    with open(input_file, 'r', encoding='utf-8') as f:
        post = frontmatter.load(f)

    old_metadata = post.metadata
    content = post.content.strip()

    # Extract required fields
    speaker = old_metadata.get("speaker", "Unknown Speaker")

    # Map party
    old_party = old_metadata.get("party", "IND")
    party = PARTY_MAP.get(old_party, "Independent")

    # Map chamber
    old_chamber = old_metadata.get("chamber", "House of Reps")
    chamber = CHAMBER_MAP.get(old_chamber, "REPS")

    # Date is already in ISO format
    date = old_metadata.get("date", "2024-01-01")

    # Extract title
    title = extract_title(old_metadata, content)

    # Optional: state from electorate
    state = old_metadata.get("electorate", None)

    # Optional: hansard reference from source_file + utterance_id
    hansard_ref = None
    if "source_file" in old_metadata and "utterance_id" in old_metadata:
        source = old_metadata["source_file"].replace(".xml", "")
        utterance = old_metadata["utterance_id"].split(".")[-1]
        hansard_ref = f"{source} {utterance}"
        if len(hansard_ref) > 100:
            hansard_ref = hansard_ref[:100]

    # Create speech_id from speaker_id + date + utterance_id
    speech_id = old_metadata.get("utterance_id", f"{old_metadata.get('speaker_id', 'unknown')}-{date}")

    # Build new frontmatter
    new_metadata = {
        "speech_id": speech_id,
        "speaker": speaker,
        "party": party,
        "chamber": chamber,
        "date": date,
        "title": title,
    }

    # Add optional fields if present
    if state:
        new_metadata["state"] = state
    if hansard_ref:
        new_metadata["hansard_reference"] = hansard_ref

    # Create new file with converted frontmatter
    new_post = frontmatter.Post(content, **new_metadata)

    # Write to output file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(frontmatter.dumps(new_post))

    print(f"✓ Converted: {input_file.name} → {output_file.name}")
    print(f"  Speech ID: {speech_id}")
    print(f"  Speaker: {speaker} ({party})")
    print(f"  Title: {title[:80]}...")
    print()


def main():
    """Convert all Hansard markdown files."""

    input_dir = Path("/home/user/sk-hansard-converter/output_md_enhanced/reps")
    output_dir = Path("/home/user/skai-fastmcp-cloudrun/data/hansard_converted")

    if not input_dir.exists():
        print(f"❌ Input directory not found: {input_dir}")
        sys.exit(1)

    # Get all markdown files
    md_files = sorted(input_dir.glob("*.md"))

    print(f"Found {len(md_files)} markdown files to convert")
    print(f"Input: {input_dir}")
    print(f"Output: {output_dir}")
    print()

    # Convert each file
    success_count = 0
    error_count = 0

    for input_file in md_files:
        try:
            output_file = output_dir / input_file.name
            convert_frontmatter(input_file, output_file)
            success_count += 1
        except Exception as e:
            print(f"❌ Error converting {input_file.name}: {e}")
            error_count += 1

    print("=" * 60)
    print(f"✅ Conversion complete!")
    print(f"   Success: {success_count}/{len(md_files)}")
    print(f"   Errors: {error_count}")
    print(f"   Output: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
