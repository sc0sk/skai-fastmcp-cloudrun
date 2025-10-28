import asyncio
import sys
from pathlib import Path
import json

# Add src to path to allow for imports
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from tools.ingest_markdown_directory import ingest_markdown_directory

async def main():
    """Runs the bulk ingestion tool for the hansard data."""
    directory_path = "data/hansard_converted"
    print(f"Starting ingestion for directory: {directory_path}")

    # Mock a request object for authorization context.
    # In a real server, this would come from the HTTP request.
    # The authorization logic in tool_utils expects a 'user' object.
    mock_request = {
        "user": {
            "roles": ["admin"] 
        }
    }

    try:
        result = await ingest_markdown_directory(
            directory_path=directory_path,
            max_files=200, # Set a higher limit to ingest all files
        )
        print("--- Ingestion Summary ---")
        # Using json.dumps for pretty printing the nested dictionary
        print(json.dumps(result, indent=2))
        print("-------------------------")

    except Exception as e:
        print(f"An unexpected error occurred during the ingestion process: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # This allows running the async main function
    if sys.version_info >= (3, 7):
        asyncio.run(main())
    else:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
