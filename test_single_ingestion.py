#!/usr/bin/env python3
"""Test ingesting a single file to verify the pipeline works."""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))
os.chdir(project_root)

from src.tools.ingest_markdown_file import ingest_markdown_file


async def main():
    """Ingest a single file for testing."""
    print("🚀 Testing single file ingestion with IAM auth...")
    
    # Set environment variables for postgres backend
    os.environ.setdefault("GCP_PROJECT_ID", "skai-fastmcp-cloudrun")
    os.environ.setdefault("GCP_REGION", "us-central1")
    os.environ.setdefault("CLOUDSQL_INSTANCE", "hansard-db-v2")
    os.environ.setdefault("CLOUDSQL_DATABASE", "hansard")
    os.environ.setdefault("VECTOR_BACKEND", "postgres")
    os.environ.setdefault("USE_IAM_AUTH", "1")  # Force IAM auth
    
    # Get markdown files
    data_dir = Path(__file__).parent / "data" / "hansard_converted"
    markdown_files = sorted(data_dir.glob("*.md"))
    
    if not markdown_files:
        print("❌ No markdown files found!")
        return
    
    # Try a few files to find one that hasn't been ingested
    result = None
    test_file = None
    
    for i, candidate in enumerate(markdown_files[:10]):
        print(f"\n🔍 Trying file {i+1}: {candidate.name}")
        
        try:
            result = await ingest_markdown_file(
                file_path=str(candidate),
                duplicate_policy="skip",
                validate_path=False,
                ctx=None
            )
            
            if result['status'] == 'success':
                test_file = candidate
                print(f"   ✅ Successfully ingested new file!")
                break
            else:
                print(f"   ⏭️  Skipped (already exists: {result.get('speech_id')})")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue
    
    if not result:
        print("\n❌ No files could be processed!")
        sys.exit(1)
    
    # Print final result
    print(f"\n{'='*60}")
    print(f"📊 Ingestion Result:")
    print(f"{'='*60}")
    print(f"   Status: {result['status']}")
    print(f"   File: {result.get('file_path', 'N/A')}")
    if result.get('speech_id'):
        print(f"   Speech ID: {result['speech_id']}")
    if result.get('chunks_ingested'):
        print(f"   Chunks ingested: {result['chunks_ingested']}")
    if result.get('collection'):
        print(f"   Collection: {result['collection']}")
    
    if result['status'] == 'success':
        print(f"\n{'='*60}")
        print(f"✅ Single file ingestion test PASSED!")
        print(f"{'='*60}")
    else:
        print(f"\n⚠️  File was skipped (already exists)")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
