#!/usr/bin/env python3
"""Run the ingestion pipeline to populate the database with Hansard speeches."""

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
    """Main ingestion function."""
    print("Starting Hansard speech ingestion pipeline...")
    
    # Set environment variables for postgres backend
    os.environ.setdefault("GCP_PROJECT_ID", "skai-fastmcp-cloudrun")
    os.environ.setdefault("GCP_REGION", "us-central1")
    os.environ.setdefault("CLOUDSQL_INSTANCE", "hansard-db-v2")
    os.environ.setdefault("CLOUDSQL_DATABASE", "hansard")
    os.environ.setdefault("VECTOR_BACKEND", "postgres")
    
    project_id = os.getenv("GCP_PROJECT_ID")
    region = os.getenv("GCP_REGION")
    instance = os.getenv("CLOUDSQL_INSTANCE")
    database = os.getenv("CLOUDSQL_DATABASE")
    
    print(f"Database Configuration:")
    print(f"   Project: {project_id}")
    print(f"   Region: {region}")
    print(f"   Instance: {instance}")
    print(f"   Database: {database}")
    
    # Get list of markdown files
    data_dir = Path(__file__).parent / "data" / "hansard_converted"
    markdown_files = sorted(data_dir.glob("*.md"))
    
    print(f"\nFound {len(markdown_files)} markdown files to ingest")
    
    # Ingest each file
    success_count = 0
    error_count = 0
    skip_count = 0
    
    for i, file_path in enumerate(markdown_files, 1):
        print(f"\n[{i}/{len(markdown_files)}] Processing: {file_path.name}")
        
        try:
            result = await ingest_markdown_file(
                file_path=str(file_path),
                duplicate_policy="skip",
                validate_path=False,
                ctx=None
            )
            
            if result['status'] == 'skipped':
                print(f"   Skipped (already exists)")
                skip_count += 1
            elif result['status'] == 'success':
                print(f"   Success - Chunks: {result.get('chunks_ingested', 0)}")
                success_count += 1
            else:
                print(f"   Error: {result.get('message', 'Unknown error')}")
                error_count += 1
            
        except Exception as e:
            print(f"   Exception: {e}")
            error_count += 1
            continue
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Ingestion Pipeline Complete!")
    print(f"{'='*60}")
    print(f"Successfully ingested: {success_count} files")
    print(f"Skipped (already exist): {skip_count} files")
    print(f"Failed: {error_count} files")
    print(f"Total processed: {len(markdown_files)} files")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
