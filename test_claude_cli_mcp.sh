#!/bin/bash
# Test Hansard MCP server tools via Claude Code CLI

echo "================================================================================"
echo "CLAUDE CODE CLI MCP TESTING"
echo "================================================================================"
echo ""
echo "Testing all 3 MCP tools with live Cloud SQL data:"
echo "1. search_hansard_speeches - Semantic search with filters"
echo "2. fetch_hansard_speech - Fetch by ID"
echo "3. ingest_hansard_speech - Add new speech"
echo ""
echo "================================================================================"

# Test 1: Search with chamber filter
echo ""
echo "TEST 1: SEARCH WITH CHAMBER FILTER"
echo "================================================================================"
echo "Query: 'climate policy'"
echo "Filter: chamber=REPS"
echo "Limit: 2"
echo ""

claude --mcp hansard-mcp "Use the search_hansard_speeches tool to search for 'climate policy' with chamber='REPS' and limit=2. Display ALL metadata fields for each result including speech_id, speaker, party, chamber, date, and similarity_score."

echo ""
echo "================================================================================"

# Test 2: Search with party filter
echo ""
echo "TEST 2: SEARCH WITH PARTY FILTER"
echo "================================================================================"
echo "Query: 'housing'"
echo "Filter: party=Liberal"
echo "Limit: 2"
echo ""

claude --mcp hansard-mcp "Use the search_hansard_speeches tool to search for 'housing' with party='Liberal' and limit=2. Display ALL metadata fields for each result."

echo ""
echo "================================================================================"

# Test 3: Search with combined filters
echo ""
echo "TEST 3: SEARCH WITH COMBINED FILTERS"
echo "================================================================================"
echo "Query: 'infrastructure'"
echo "Filters: chamber=REPS AND party=Liberal"
echo "Limit: 2"
echo ""

claude --mcp hansard-mcp "Use the search_hansard_speeches tool to search for 'infrastructure' with chamber='REPS' AND party='Liberal' and limit=2. Display ALL metadata fields and verify both filters are applied correctly."

echo ""
echo "================================================================================"

# Test 4: Fetch speech by ID
echo ""
echo "TEST 4: FETCH SPEECH BY ID"
echo "================================================================================"
echo "First search to get a speech_id, then fetch the full speech"
echo ""

claude --mcp hansard-mcp "First, use search_hansard_speeches to find 1 speech about 'budget'. Then use fetch_hansard_speech with the speech_id from that result to get the full speech text. Show me the speaker, date, title, and the first 300 characters of the full text."

echo ""
echo "================================================================================"

# Test 5: Date range filter
echo ""
echo "TEST 5: DATE RANGE FILTER"
echo "================================================================================"
echo "Query: 'economy'"
echo "Date range: 2024-06-01 to 2024-06-30"
echo "Limit: 2"
echo ""

claude --mcp hansard-mcp "Use the search_hansard_speeches tool to search for 'economy' with start_date='2024-06-01' and end_date='2024-06-30' and limit=2. Display the date field for each result to verify the filter works."

echo ""
echo "================================================================================"
echo "✅ ALL TESTS COMPLETED"
echo "================================================================================"
