#!/usr/bin/env python3
"""Ingest real Hansard speeches from markdown files with YAML frontmatter."""

import asyncio
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import hashlib

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parsers.hansard_parser import HansardMarkdownParser
from models.speech import SpeechMetadata
from storage.metadata_store import get_default_metadata_store
from storage.vector_store import get_default_vector_store
from langchain_text_splitters import RecursiveCharacterTextSplitter


def compute_content_hash(text: str) -> str:
    """Compute SHA-256 hash of text content for duplicate detection."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


async def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 150) -> List[str]:
    """Split text into chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    return splitter.split_text(text)


async def ingest_single_speech(
    file_path: Path,
    metadata_store,
    vector_store,
    speech_num: int,
    total_speeches: int,
) -> bool:
    """
    Ingest a single Hansard speech from markdown file.

    Returns:
        bool: True if successfully ingested, False if skipped/failed
    """
    try:
        print(f"  Processing {speech_num}/{total_speeches}: {file_path.name}")

        # Parse markdown file
        parser = HansardMarkdownParser(str(file_path))
        parsed_data = parser.parse()

        # Validate required fields
        required_fields = ['speaker', 'date', 'chamber', 'full_text']
        for field in required_fields:
            if field not in parsed_data or not parsed_data[field]:
                print(f"    ❌ Error: Missing required field '{field}'")
                return False

        # Compute content hash
        content_hash = compute_content_hash(parsed_data["full_text"])

        # Create SpeechMetadata object
        speech = SpeechMetadata(
            title=parsed_data.get('debate', 'Parliamentary Speech'),
            full_text=parsed_data["full_text"],
            speaker=parsed_data["speaker"],
            party=parsed_data.get("party"),
            chamber=parsed_data["chamber"],
            electorate=parsed_data.get("electorate"),
            state=None,  # Can be derived from electorate if needed
            date=parsed_data["date"],
            hansard_reference=parsed_data.get("hansard_reference"),
            topic_tags=[],  # Could extract from frontmatter if available
            content_hash=content_hash,
        )

        # Add speech to metadata store
        try:
            speech_id = await metadata_store.add_speech(speech)
            print(f"    ✅ Speech added to metadata store (ID: {speech_id[:8]}...)")
        except ValueError as e:
            if "Duplicate speech detected" in str(e):
                print(f"    ⚠️  Skipped: Speech already exists (duplicate content)")
                return False
            raise

        # Chunk the speech text
        chunks = await chunk_text(parsed_data["full_text"])
        print(f"    📝 Split into {len(chunks)} chunks")

        # Prepare metadata for each chunk - CONVERT DATE TO STRING
        chunk_metadatas = []
        for idx, chunk in enumerate(chunks):
            metadata = {
                "speech_id": speech_id,
                "chunk_index": idx,
                "chunk_size": len(chunk),
                "speaker": parsed_data["speaker"],
                "party": parsed_data.get("party"),
                "chamber": parsed_data["chamber"],
                "electorate": parsed_data.get("electorate"),
                "date": parsed_data["date"].isoformat() if hasattr(parsed_data["date"], 'isoformat') else str(parsed_data["date"]),
                "hansard_reference": parsed_data.get("hansard_reference"),
            }
            chunk_metadatas.append(metadata)

        # Add chunks with embeddings to vector store
        chunk_ids = await vector_store.add_chunks(
            texts=chunks,
            metadatas=chunk_metadatas,
            speech_id=speech_id,
        )
        print(f"    ✅ {len(chunk_ids)} chunks added to vector store with embeddings")

        return True

    except Exception as e:
        print(f"    ❌ Error processing speech: {e}")
        import traceback
        traceback.print_exc()
        return False


async def bulk_ingest(data_dir: str = "data/hansard_reps") -> Dict[str, int]:
    """
    Ingest all Hansard markdown files from directory.

    Returns:
        Dict with counts: {'total': N, 'success': M, 'skipped': K, 'failed': L}
    """
    print("=" * 80)
    print("Hansard Markdown Ingestion Script")
    print("=" * 80)
    print()

    # Initialize stores
    print("🔄 Initializing storage services...")
    metadata_store = await get_default_metadata_store()
    vector_store = await get_default_vector_store()
    print("✅ Storage services initialized")
    print()

    # Discover markdown files
    data_path = Path(data_dir)
    if not data_path.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    md_files = sorted(data_path.glob("*.md"))
    total = len(md_files)

    print(f"📂 Found {total} markdown files in {data_dir}")
    print()

    # Process each file
    stats = {'total': total, 'success': 0, 'skipped': 0, 'failed': 0}

    for idx, file_path in enumerate(md_files, 1):
        result = await ingest_single_speech(
            file_path, metadata_store, vector_store, idx, total
        )

        if result:
            stats['success'] += 1
        else:
            stats['skipped'] += 1

        # Progress indicator
        if idx % 10 == 0:
            print(f"\n  Progress: {idx}/{total} files processed\n")

    # Final report
    print()
    print("=" * 80)
    print("Ingestion Complete")
    print("=" * 80)
    print(f"Total files: {stats['total']}")
    print(f"✅ Successfully ingested: {stats['success']} speeches")
    print(f"⚠️  Skipped (duplicates): {stats['skipped']} speeches")
    print(f"❌ Failed: {stats['failed']} speeches")
    print("=" * 80)

    return stats


async def main():
    """Main execution function."""
    # Verify environment variables
    required_env_vars = ["GCP_PROJECT_ID", "CLOUDSQL_INSTANCE"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        print(f"❌ ERROR: Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)

    # Run ingestion
    stats = await bulk_ingest()

    # Exit with success if any speeches were ingested
    sys.exit(0 if stats['success'] > 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
