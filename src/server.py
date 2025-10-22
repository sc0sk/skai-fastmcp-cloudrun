"""FastMCP server for Australian Hansard parliamentary speech search.

This server provides MCP tools optimized for ChatGPT Developer Mode with:
- Enhanced tool descriptions with "Use this when..." guidance
- Tool annotations (readOnlyHint) for better UX
- Parameter enums for Australian political parties and chambers
- ISO 8601 date format specifications
- Tool selection guidance to prefer MCP tools over built-in capabilities
"""

import os
from fastmcp import FastMCP

# Import tool functions (relative imports for FastMCP)
from tools.search import search_hansard_speeches, SEARCH_TOOL_METADATA
from tools.fetch import fetch_hansard_speech, FETCH_TOOL_METADATA
from tools.ingest import ingest_hansard_speech, INGEST_TOOL_METADATA

# Create FastMCP server instance
mcp = FastMCP("Hansard MCP Server")

# Register search tool with ChatGPT Developer Mode enhancements
# Note: icon parameter not supported in FastMCP 2.12.5, icons stored in metadata for future use
mcp.tool(
    name=SEARCH_TOOL_METADATA["name"],
    annotations=SEARCH_TOOL_METADATA["annotations"]
)(search_hansard_speeches)

# Register fetch tool with ChatGPT Developer Mode enhancements
mcp.tool(
    name=FETCH_TOOL_METADATA["name"],
    annotations=FETCH_TOOL_METADATA["annotations"]
)(fetch_hansard_speech)

# Register ingest tool (write operation - no readOnlyHint)
mcp.tool(
    name=INGEST_TOOL_METADATA["name"]
)(ingest_hansard_speech)

# Print startup message
print("✅ Hansard MCP Server initialized with ChatGPT Developer Mode enhancements")
print("   🔍 search_hansard_speeches [read-only]")
print("   📄 fetch_hansard_speech [read-only]")
print("   📝 ingest_hansard_speech [write]")

# The server is ready to be run with:
# DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py (local dev)
# PORT=8080 fastmcp run src/server.py (production with OAuth)
