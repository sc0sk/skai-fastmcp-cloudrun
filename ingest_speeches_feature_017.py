#!/usr/bin/env python3
"""Feature 017: Fresh PostgreSQL Population - Simplified Async Approach.

Key insight: The ingest_markdown_directory MCP tool already handles everything:
1. Creates collection in database (via storage layer)
2. Processes markdown files
3. Generates embeddings
4. Stores in PostgreSQL with metadata
5. Reports progress and errors

We just need to call it in an async context!
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tools.ingest_markdown_directory import ingest_markdown_directory  # noqa


async def main():
    """Execute bulk ingestion of speeches."""
    
    print("=" * 80)
    print("Feature 017: Fresh PostgreSQL Database Population")
    print("=" * 80)
    print()
    print("Using Feature 013: ingest_markdown_directory MCP tool")
    print()
    print("This tool handles:")
    print("  ✅ Directory discovery (data/hansard_converted/)")
    print("  ✅ Markdown parsing with frontmatter extraction")
    print("  ✅ Text splitting (LangChain RecursiveCharacterTextSplitter)")
    print("  ✅ Vector embeddings (Vertex AI, 768-dimensional)")
    print("  ✅ PostgreSQL storage (langchain-postgres schema)")
    print("  ✅ Progress reporting")
    print("  ✅ Error isolation")
    print()
    print("=" * 80)
    print("Starting Bulk Ingestion")
    print("=" * 80)
    print()

    try:
        result = await ingest_markdown_directory(
            directory_path="data/hansard_converted/",
            pattern="*.md",
            max_files=100,  # Safety limit
            duplicate_policy="skip",
            validate_path=False,  # Allow relative paths in this context
            ctx=None  # No auth context needed for local script
        )

        print()
        print("=" * 80)
        print("Ingestion Results")
        print("=" * 80)
        print()

        summary = result.get("summary", {})
        print("Summary:")
        print(f"  Total files discovered:  {summary.get('total_files', 0):>6}")
        print(
            f"  Successfully ingested:   {summary.get('succeeded', 0):>6}"
        )
        print(
            f"  Skipped (duplicates):    {summary.get('skipped', 0):>6}"
        )
        print(f"  Failed:                  {summary.get('failed', 0):>6}")
        total_chunks = summary.get('total_chunks_created', 0)
        print(
            f"  Total chunks created:    {total_chunks:>6}"
        )
        print()

        if result.get("failed_files"):
            failed = result["failed_files"]
            print(f"Failed Files ({len(failed)}):")
            for item in failed[:10]:
                error_msg = item.get('error', 'Unknown error')
                file_name = item.get('file_name')
                print(f"  - {file_name}: {error_msg}")
            if len(failed) > 10:
                print(f"  ... and {len(failed) - 10} more")
            print()

        if result.get("successful_files"):
            success = result["successful_files"]
            print(f"Sample Successful Files (first 5 of {len(success)}):")
            for item in success[:5]:
                print(f"  - {item.get('file_name')}: {item.get('chunks_created', 0)} chunks")
            print()

        message = result.get("message", "")
        print(f"Message: {message}")
        print()

        # Status
        if result.get("status") == "complete":
            if summary.get("failed", 0) == 0:
                print("✅ INGESTION SUCCESSFUL - All files processed!")
            else:
                print(f"⚠️  INGESTION PARTIAL - {summary.get('failed')} files failed")
        else:
            print(f"❌ INGESTION ERROR - Status: {result.get('status')}")

        print()
        print("=" * 80)
        print("Next Steps")
        print("=" * 80)
        print()
        print("1. Update Cloud Run service:")
        print("   gcloud run services update hansard-mcp \\")
        print("     --set-env-vars VECTOR_BACKEND=postgres")
        print()
        print("2. Deploy updated service")
        print()
        print("3. Test in production:")
        print('   curl -X POST https://hansard-mcp-XXX.run.app/search \\')
        print('     -d \'{"query": "climate policy"}\'')
        print()

        return 0 if result.get("status") == "complete" and summary.get("failed", 0) == 0 else 1

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
