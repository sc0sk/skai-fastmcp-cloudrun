#!/usr/bin/env python3
"""
Bulk ingest converted Hansard markdown files to Cloud Run MCP server.

This script uploads converted markdown files to the production Cloud Run
instance where they will be ingested into the database with proper authentication.
"""

import asyncio
import httpx
from pathlib import Path
import json
from typing import List

CLOUD_RUN_URL = "https://hansard-mcp-server-666924716777.us-central1.run.app"
MCP_ENDPOINT = f"{CLOUD_RUN_URL}/mcp"


async def ingest_file_via_mcp(file_path: Path, session: httpx.AsyncClient) -> dict:
    """
    Ingest a single markdown file via Cloud Run MCP server.

    Note: This is a simplified example. The actual MCP protocol requires
    proper SSE (Server-Sent Events) handling and JSON-RPC format.
    """

    # Read file content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # For now, just print what we would do
    print(f"Would ingest: {file_path.name}")

    return {
        "status": "simulated",
        "file": file_path.name,
        "message": "Simulation mode - use Claude Code CLI for actual ingestion"
    }


async def main():
    """Bulk ingest all converted files."""

    input_dir = Path("/home/user/skai-fastmcp-cloudrun/data/hansard_converted")
    md_files = sorted(input_dir.glob("*.md"))

    print("=" * 60)
    print(f"Hansard Bulk Ingestion to Cloud Run")
    print("=" * 60)
    print(f"Files to ingest: {len(md_files)}")
    print(f"MCP Server: {CLOUD_RUN_URL}")
    print()

    print("⚠️  NOTE: This script demonstrates the approach.")
    print("   For actual ingestion, use the MCP tool via:")
    print("   1. Claude Code CLI")
    print("   2. MCP Inspector")
    print("   3. Direct MCP client")
    print()

    async with httpx.AsyncClient(timeout=300.0) as session:
        for i, file_path in enumerate(md_files, 1):
            result = await ingest_file_via_mcp(file_path, session)
            print(f"  [{i}/{len(md_files)}] {result['message']}")

            # Rate limit to avoid overwhelming the server
            if i % 10 == 0:
                print(f"  ... processed {i}/{len(md_files)} files")
                await asyncio.sleep(1)

    print()
    print("=" * 60)
    print("✅ Bulk ingestion simulation complete!")
    print()
    print("To actually ingest files, you can:")
    print("1. Use Claude Code CLI with the hansard-mcp server")
    print("2. Build Phase 5: ingest_markdown_bulk tool")
    print("3. Use the Cloud Run deployment for production")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
