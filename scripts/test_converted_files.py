#!/usr/bin/env python3
"""
Test that all converted markdown files are valid and ready for ingestion.

This script validates frontmatter without actually ingesting to the database.
"""

import frontmatter
import sys
from pathlib import Path
from pydantic import ValidationError

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models.speech import SpeechFrontmatter


def validate_file(file_path: Path) -> dict:
    """Validate a single markdown file."""

    try:
        # Parse markdown
        with open(file_path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)

        # Validate frontmatter against Pydantic model
        metadata = SpeechFrontmatter(**post.metadata)

        # Get content
        content = post.content.strip()

        return {
            "status": "valid",
            "speech_id": metadata.speech_id,
            "speaker": metadata.speaker,
            "party": metadata.party,
            "date": str(metadata.date),
            "title": metadata.title[:60] + "..." if len(metadata.title) > 60 else metadata.title,
            "content_length": len(content),
            "word_count": len(content.split()),
        }

    except ValidationError as e:
        return {
            "status": "error",
            "file": file_path.name,
            "error": str(e)
        }
    except Exception as e:
        return {
            "status": "error",
            "file": file_path.name,
            "error": f"Unexpected error: {e}"
        }


def main():
    """Validate all converted files."""

    input_dir = Path("/home/user/skai-fastmcp-cloudrun/data/hansard_converted")

    if not input_dir.exists():
        print(f"❌ Directory not found: {input_dir}")
        sys.exit(1)

    md_files = sorted(input_dir.glob("*.md"))

    print("=" * 80)
    print(f"Hansard Markdown Validation Report")
    print("=" * 80)
    print(f"Directory: {input_dir}")
    print(f"Files: {len(md_files)}")
    print()

    valid_count = 0
    error_count = 0
    total_words = 0

    for i, file_path in enumerate(md_files, 1):
        result = validate_file(file_path)

        if result["status"] == "valid":
            valid_count += 1
            total_words += result["word_count"]

            # Print first 5 and last 5 files
            if i <= 5 or i > len(md_files) - 5:
                print(f"✅ {i:2d}. {file_path.name}")
                print(f"     ID: {result['speech_id']}")
                print(f"     Speaker: {result['speaker']} ({result['party']}) - {result['date']}")
                print(f"     Title: {result['title']}")
                print(f"     Words: {result['word_count']:,}")
                print()
            elif i == 6:
                print(f"   ... (showing first 5 and last 5 files)")
                print()
        else:
            error_count += 1
            print(f"❌ {i:2d}. {file_path.name}")
            print(f"     Error: {result['error']}")
            print()

    print("=" * 80)
    print(f"Validation Summary")
    print("=" * 80)
    print(f"✅ Valid files: {valid_count}/{len(md_files)}")
    print(f"❌ Errors: {error_count}")
    print(f"📝 Total words: {total_words:,}")
    print(f"📊 Average words per speech: {total_words // valid_count if valid_count > 0 else 0:,}")
    print()

    if valid_count == len(md_files):
        print("🎉 All files are valid and ready for ingestion!")
        print()
        print("Next steps:")
        print("1. Use Claude Code CLI to ingest files interactively")
        print("2. Build Phase 5 (ingest_markdown_bulk tool) for automated bulk ingestion")
        print("3. Deploy to Cloud Run and use production MCP server")
    else:
        print(f"⚠️  {error_count} files have validation errors - please review")

    print("=" * 80)


if __name__ == "__main__":
    main()
