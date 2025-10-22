#!/usr/bin/env python3
"""Populate Cloud SQL database with sample Hansard speeches.

This script ingests sample Simon Kennedy speeches into the Cloud SQL database,
generating vector embeddings and storing them for semantic search.

Usage:
    python scripts/populate_hansard_db.py

Environment Variables:
    GCP_PROJECT_ID: GCP project ID (required)
    GCP_REGION: Cloud SQL region (default: us-central1)
    CLOUDSQL_INSTANCE: Cloud SQL instance name (required)
    CLOUDSQL_DATABASE: Database name (default: hansard)
    CLOUDSQL_USER: Database user (optional, None for IAM auth)
    DATABASE_PASSWORD: Database password (optional, None for IAM auth)
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import date
from typing import List, Dict, Any
import hashlib

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain.text_splitter import RecursiveCharacterTextSplitter

# Import sample speeches
sys.path.insert(0, str(Path(__file__).parent))
from data.sample_speeches import get_sample_speeches, get_speech_count

# Import storage services
from storage.vector_store import get_default_vector_store
from storage.metadata_store import get_default_metadata_store
from models.speech import SpeechMetadata


def compute_content_hash(text: str) -> str:
    """Compute SHA-256 hash of speech content for duplicate detection.

    Args:
        text: Full speech text

    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


async def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 150) -> List[str]:
    """Split text into chunks using RecursiveCharacterTextSplitter.

    Args:
        text: Full speech text to chunk
        chunk_size: Target chunk size in characters (default: 800)
        chunk_overlap: Overlap between chunks in characters (default: 150)

    Returns:
        List of text chunks
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = splitter.split_text(text)
    return chunks


async def ingest_speech(
    speech_data: Dict[str, Any],
    vector_store,
    metadata_store,
    speech_num: int,
    total_speeches: int,
) -> bool:
    """Ingest a single speech into the database.

    Args:
        speech_data: Dictionary containing speech metadata and full_text
        vector_store: VectorStoreService instance
        metadata_store: MetadataStore instance
        speech_num: Current speech number (for progress reporting)
        total_speeches: Total number of speeches to process

    Returns:
        True if successful, False if skipped/failed
    """
    try:
        print(f"  Processing speech {speech_num}/{total_speeches}: {speech_data['title'][:60]}...")

        # Validate required fields
        required_fields = ["title", "speaker", "date", "full_text"]
        for field in required_fields:
            if field not in speech_data or not speech_data[field]:
                print(f"    ❌ Error: Missing required field '{field}'")
                return False

        # Compute content hash
        content_hash = compute_content_hash(speech_data["full_text"])

        # Create SpeechMetadata object
        speech = SpeechMetadata(
            title=speech_data["title"],
            full_text=speech_data["full_text"],
            speaker=speech_data["speaker"],
            party=speech_data.get("party"),
            chamber=speech_data.get("chamber"),
            electorate=speech_data.get("electorate"),
            state=speech_data.get("state"),
            date=speech_data["date"],
            hansard_reference=speech_data.get("hansard_reference"),
            topic_tags=speech_data.get("topic_tags", []),
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
        chunks = await chunk_text(speech_data["full_text"])
        print(f"    📝 Split into {len(chunks)} chunks")

        # Prepare metadata for each chunk
        chunk_metadatas = []
        for idx, chunk in enumerate(chunks):
            metadata = {
                "speech_id": speech_id,
                "chunk_index": idx,
                "chunk_size": len(chunk),
                "speaker": speech_data["speaker"],
                "party": speech_data.get("party"),
                "chamber": speech_data.get("chamber"),
                "state": speech_data.get("state"),
                "date": speech_data["date"],
                "hansard_reference": speech_data.get("hansard_reference"),
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


async def main():
    """Main execution function."""
    print("=" * 80)
    print("Hansard Database Population Script")
    print("=" * 80)
    print()

    # Verify environment variables
    required_env_vars = ["GCP_PROJECT_ID", "CLOUDSQL_INSTANCE"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ Error: Missing required environment variables: {', '.join(missing_vars)}")
        print()
        print("Required environment variables:")
        print("  GCP_PROJECT_ID - GCP project ID")
        print("  CLOUDSQL_INSTANCE - Cloud SQL instance name")
        print()
        print("Optional environment variables:")
        print("  GCP_REGION - Cloud SQL region (default: us-central1)")
        print("  CLOUDSQL_DATABASE - Database name (default: hansard)")
        print("  CLOUDSQL_USER - Database user (default: None for IAM auth)")
        print("  DATABASE_PASSWORD - Database password (default: None for IAM auth)")
        sys.exit(1)

    print("Configuration:")
    print(f"  Project ID: {os.getenv('GCP_PROJECT_ID')}")
    print(f"  Region: {os.getenv('GCP_REGION', 'us-central1')}")
    print(f"  Instance: {os.getenv('CLOUDSQL_INSTANCE')}")
    print(f"  Database: {os.getenv('CLOUDSQL_DATABASE', 'hansard')}")
    print(f"  Auth: {'IAM' if not os.getenv('CLOUDSQL_USER') else 'User/Password'}")
    print()

    # Load sample speeches
    sample_speeches = get_sample_speeches()
    total_count = get_speech_count()

    print(f"📚 Loaded {total_count} sample speeches")
    print()

    # Initialize storage services
    print("🔄 Initializing storage services...")
    try:
        vector_store = await get_default_vector_store()
        metadata_store = await get_default_metadata_store()
        print("✅ Storage services initialized")
    except Exception as e:
        print(f"❌ Error initializing storage services: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print()
    print("=" * 80)
    print("Starting Ingestion")
    print("=" * 80)
    print()

    # Ingest speeches one by one
    successful = 0
    skipped = 0
    failed = 0

    for idx, speech_data in enumerate(sample_speeches, 1):
        result = await ingest_speech(
            speech_data=speech_data,
            vector_store=vector_store,
            metadata_store=metadata_store,
            speech_num=idx,
            total_speeches=total_count,
        )

        if result:
            successful += 1
        elif result is False:
            skipped += 1
        else:
            failed += 1

        print()  # Blank line between speeches

    # Summary
    print("=" * 80)
    print("Ingestion Complete")
    print("=" * 80)
    print()
    print(f"✅ Successfully ingested: {successful} speeches")
    if skipped > 0:
        print(f"⚠️  Skipped (duplicates): {skipped} speeches")
    if failed > 0:
        print(f"❌ Failed: {failed} speeches")
    print()
    print(f"📊 Total speeches in database: {successful}")
    print()

    if successful > 0:
        print("🎉 Database population complete!")
        print()
        print("Next steps:")
        print("  1. Test search: Run search_hansard_speeches via MCP Inspector")
        print("  2. Test fetch: Run fetch_hansard_speech with a speech_id from search results")
        print("  3. Verify: Check that search returns non-empty results")
    else:
        print("⚠️  No speeches were successfully ingested.")
        print("   Check the error messages above for details.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
