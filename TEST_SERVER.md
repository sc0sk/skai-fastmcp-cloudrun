# Server Testing Notes

## Import Path Issue

The FastMCP CLI expects different import paths than standard Python execution. Here are the solutions:

### Option 1: Use PYTHONPATH (Recommended for Testing)

```bash
# Set PYTHONPATH to include the src directory
export PYTHONPATH=/home/user/skai-fastmcp-cloudrun/src:$PYTHONPATH
export DANGEROUSLY_OMIT_AUTH=true

# Start server
fastmcp dev src/server.py
```

### Option 2: Install Package in Development Mode

```bash
# Install as editable package
uv pip install -e .

# Then start server
DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py
```

### Option 3: Flatten Structure (Alternative)

Move tools and models to src root:
```
src/
├── server.py
├── search.py
├── fetch.py
├── ingest.py
└── enums.py
```

## Current Status

✅ **Server code is correct** - imports work with standard Python
✅ **Tests pass** - enum tests run successfully
📋 **FastMCP CLI** - needs PYTHONPATH or package install

## Verification

Once import issue is resolved, the server will start and you can test with:

```bash
# In terminal 1
DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py

# In terminal 2
npx @modelcontextprotocol/inspector
```

## What Works Now

```bash
# Direct Python import (works)
python3 -c "import sys; sys.path.insert(0, 'src'); from server import mcp"

# Pytest (works)
pytest tests/unit/test_tool_metadata.py::TestEnumDefinitions -v
```
