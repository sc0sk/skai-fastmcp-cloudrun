"""
This script makes the ingest_markdown_directory tool runnable as a module.
"""
import asyncio
import json

from tools.ingest_markdown_directory import ingest_markdown_directory


async def main():
    """Runs the bulk ingestion tool for the hansard data."""
    # Assumes the script is run from the root of the project
    directory_path = "data/hansard_converted"
    print(f"Starting ingestion for directory: {directory_path}")

    try:
        result = await ingest_markdown_directory(
            directory_path=directory_path,
            max_files=200,  # Set a higher limit to ingest all files
        )
        print("--- Ingestion Summary ---")
        print(json.dumps(result, indent=2))
        print("-------------------------")

    except Exception as e:
        print(f"An unexpected error occurred during the ingestion process: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
