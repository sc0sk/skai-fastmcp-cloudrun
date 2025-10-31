#!/usr/bin/env python3
"""Test script to verify mcp-prod OAuth flow and tool execution.

This script:
1. Connects to the production MCP server via HTTP with OAuth
2. Lists available tools
3. Executes a search_hansard_speeches query
4. Fetches a specific speech
"""

import asyncio
import logging
from fastmcp import Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_mcp_prod():
    """Test the production MCP server with OAuth authentication."""
    
    server_url = "https://mcp.simonkennedymp.com.au/mcp"
    
    logger.info(f"Connecting to MCP server: {server_url}")
    
    try:
        # Create client - OAuth flow will happen automatically if needed
        async with Client(server_url) as client:
            logger.info("✅ Connected to MCP server")
            
            # List available tools
            tools = await client.list_tools()
            logger.info(f"Available tools: {[t.name for t in tools]}")
            
            # Test 1: Search for speeches about climate change
            logger.info("\n=== Test 1: Search for 'climate change' speeches ===")
            search_result = await client.call_tool(
                "search_hansard_speeches",
                query="climate change",
                limit=3
            )
            logger.info(f"Search result: {search_result}")
            
            # Extract first speech_id if available
            if search_result and 'speeches' in search_result:
                speeches = search_result['speeches']
                if speeches:
                    first_speech = speeches[0]
                    speech_id = first_speech.get('speech_id')
                    
                    if speech_id:
                        # Test 2: Fetch the full speech
                        logger.info(f"\n=== Test 2: Fetch speech {speech_id} ===")
                        fetch_result = await client.call_tool(
                            "fetch_hansard_speech",
                            speech_id=speech_id
                        )
                        logger.info(f"Fetched speech: {fetch_result.get('speaker_name')} - {fetch_result.get('title')[:100]}...")
            
            logger.info("\n✅ All tests passed!")
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(test_mcp_prod())
