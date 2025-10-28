import asyncio
import sys
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).resolve().parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from tools.ingest_markdown_directory import ingest_markdown_directory


async def main():
    """Runs the bulk ingestion process."""
    directory_to_ingest = "/home/user/skai-fastmcp-cloudrun/data/hansard_converted/"
    print(f"Starting ingestion for directory: {directory_to_ingest}")

    # This mock request will be passed down to the single file ingestion tool
    # to satisfy the authorization check. In a real server environment,
    # this would be the actual incoming FastAPI request object.
    mock_request = {
        "scope": {
            "headers": [
                (b"authorization", b"Bearer mock-token-for-cli-ingestion")
            ]
        }
    }

    # Create a mock context object that has a 'request' attribute
    class MockContext:
        def __init__(self):
            self.request = mock_request

        async def report_progress(self, current, total):
            print(f"Progress: {current}/{total} files processed.")

        async def info(self, message):
            print(f"INFO: {message}")

    result = await ingest_markdown_directory(
        directory_path=directory_to_ingest,
        ctx=MockContext()
    )

    print("\n--- Ingestion Complete ---")
    print(result)
    print("--------------------------\n")


if __name__ == "__main__":
    asyncio.run(main())
