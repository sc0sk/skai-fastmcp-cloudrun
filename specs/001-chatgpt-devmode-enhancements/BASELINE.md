# Baseline Tool State

**Date**: 2025-10-22
**Feature**: ChatGPT Developer Mode Enhancements
**Branch**: `001-chatgpt-devmode-enhancements`

## Purpose

This document records the baseline state of MCP tools before applying ChatGPT Developer Mode enhancements. Since the tools don't exist yet in the repository, this feature implements them WITH enhancements already included.

## Baseline State

### Project Status

- **FastMCP Version**: 2.12.5 (supports `readOnlyHint` and tool annotations)
- **Tools Directory**: Does not exist (`src/tools/` is empty)
- **Existing Tools**: None
- **Test Infrastructure**: Created during this feature implementation

### Implementation Approach

Rather than implementing basic tools and then enhancing them, we're creating the tools WITH ChatGPT Developer Mode enhancements from the start. This approach is more efficient and aligns with the feature specification.

## Tool Specifications (To Be Implemented)

### 1. search_hansard_speeches

**Purpose**: Search Simon Kennedy's parliamentary speeches using semantic search

**Baseline (if it existed)**:
- Simple description: "Search parliamentary speeches"
- No tool annotations
- No parameter enums
- No "Use this when..." guidance

**Enhanced (what we'll implement)**:
- Comprehensive description with "Use this when..." guidance
- `readOnlyHint: true` annotation
- Parameter enums for `party` and `chamber`
- ISO 8601 date format specifications
- Tool selection guidance ("Do not use built-in browsing")
- Icon: 🔍

### 2. fetch_hansard_speech

**Purpose**: Fetch complete text of a specific speech by ID

**Baseline (if it existed)**:
- Simple description: "Fetch speech by ID"
- No tool annotations
- No workflow guidance

**Enhanced (what we'll implement)**:
- Comprehensive description with workflow guidance
- `readOnlyHint: true` annotation
- `idempotentHint: true` annotation
- Workflow documentation (typically used after search)
- Icon: 📄

### 3. ingest_hansard_speech

**Purpose**: Ingest new speeches into the database

**Baseline (if it existed)**:
- Simple description: "Ingest speech data"
- No tool annotations
- No admin-focused guidance

**Enhanced (what we'll implement)**:
- Admin-focused description
- NO `readOnlyHint` (this is a write operation)
- Workflow documentation (data ingestion pipeline)
- Icon: 📝

## Verification

To verify the baseline state (absence of tools):
```bash
ls -la /home/user/skai-fastmcp-cloudrun/src/tools/
# Result: Empty directory (only __pycache__)

grep -r "search_hansard" /home/user/skai-fastmcp-cloudrun/src/
# Result: No matches
```

## Enhancement Summary

All three tools will be implemented with:
1. ✅ Enhanced descriptions with "Use this when..." guidance
2. ✅ Appropriate tool annotations (`readOnlyHint` for read-only tools)
3. ✅ Parameter enums for party and chamber (search tool)
4. ✅ ISO 8601 date format specifications
5. ✅ Tool selection guidance
6. ✅ Workflow documentation
7. ✅ Icons for visual identification

This baseline document serves as a reference for what would have been the "before" state if the tools had existed.
