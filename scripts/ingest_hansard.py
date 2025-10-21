#!/usr/bin/env python3
"""CLI script for ingesting Markdown speeches into Hansard RAG database.

This script is used for admin operations (ingestion) and is separate from the
MCP server which handles read-only operations (search/retrieve).

Usage:
    # Dry run (validate only)
    python scripts/ingest_hansard.py --directory data/sk-hansard --dry-run

    # Full ingestion
    python scripts/ingest_hansard.py --directory data/sk-hansard

    # Custom chunk settings
    python scripts/ingest_hansard.py --directory data/sk-hansard --chunk-size 1000 --chunk-overlap 200

    # Single file
    python scripts/ingest_hansard.py --file data/sk-hansard/speech1.md
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tools.ingest import ingest_markdown_speeches, ingest_single_speech


async def main():
    parser = argparse.ArgumentParser(
        description="Ingest Markdown speeches into Hansard RAG database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--directory",
        "-d",
        type=str,
        help="Directory containing Markdown files (sk-hansard format)",
    )
    input_group.add_argument(
        "--file",
        "-f",
        type=str,
        help="Single Markdown file to ingest",
    )

    # Chunking options
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=800,
        help="Chunk size in characters (default: 800)",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=150,
        help="Overlap between chunks in characters (default: 150)",
    )

    # Dry run option
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate files without inserting to database",
    )

    # Verbose output
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output",
    )

    args = parser.parse_args()

    # Print configuration
    print("🚀 Hansard RAG Ingestion Script")
    print("=" * 50)
    if args.directory:
        print(f"📁 Directory: {args.directory}")
    else:
        print(f"📄 File: {args.file}")
    print(f"📏 Chunk size: {args.chunk_size} chars")
    print(f"🔗 Chunk overlap: {args.chunk_overlap} chars")
    print(f"🧪 Dry run: {args.dry_run}")
    print("=" * 50)
    print()

    try:
        if args.directory:
            # Ingest directory
            print(f"📂 Processing directory: {args.directory}")
            result = await ingest_markdown_speeches(
                directory_path=args.directory,
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap,
                dry_run=args.dry_run,
            )

            # Print results
            print("\n✅ Ingestion Complete!")
            print("=" * 50)
            print(f"📊 Speeches processed: {result.speeches_processed}")
            print(f"📦 Chunks created: {result.chunks_created}")
            print(f"🎯 Vectors stored: {result.vectors_stored}")
            print(f"⏭️  Duplicates skipped: {result.duplicates_skipped}")
            print(f"⏱️  Processing time: {result.processing_time_seconds:.2f}s")

            if result.errors:
                print(f"\n⚠️  Errors encountered: {len(result.errors)}")
                if args.verbose:
                    for error in result.errors:
                        print(f"  - {error}")

        else:
            # Ingest single file
            print(f"📄 Processing file: {args.file}")
            result = await ingest_single_speech(
                file_path=args.file,
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap,
            )

            # Print results
            print("\n✅ Ingestion Complete!")
            print("=" * 50)
            print(f"🆔 Speech ID: {result['speech_id']}")
            print(f"📦 Chunks created: {result['chunks_created']}")
            print(f"⏱️  Processing time: {result['processing_time_seconds']:.2f}s")

            if args.verbose:
                print(f"\n📋 Chunk IDs:")
                for chunk_id in result['chunk_ids']:
                    print(f"  - {chunk_id}")

        print("\n🎉 Success!")
        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
