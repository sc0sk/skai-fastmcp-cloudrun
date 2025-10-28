"""
A simple script to test the ingestion of a single markdown file.
"""
import asyncio
import os
import sys

# This ensures that the 'src' directory is on the Python path
# so that absolute imports like 'from config import ...' work correctly.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from tools.ingest_markdown_file import ingest_markdown_file

# Define the path to a single test file.
# Using a known file from the dataset.
TEST_FILE_PATH = "data/hansard_converted/00a0b9b0-0a0a-4a0a-8a0a-0a0a0a0a0a0a.md"


async def main():
    """
    Runs the ingestion for a single file and prints the result.
    """
    print(f"Attempting to ingest single file: {TEST_FILE_PATH}")
    result = await ingest_markdown_file(file_path=TEST_FILE_PATH)
    print("--- Ingestion Result ---")
    import json
    print(json.dumps(result, indent=2))
    print("------------------------")


if __name__ == "__main__":
    # Check if the file exists before running
    if not os.path.exists(TEST_FILE_PATH):
        print(f"Error: Test file not found at '{TEST_FILE_PATH}'")
        print("Please ensure the data is available.")
        sys.exit(1)
    
    asyncio.run(main())
