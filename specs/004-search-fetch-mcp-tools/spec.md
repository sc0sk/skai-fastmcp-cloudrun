# Feature 004: Search and Fetch MCP Tools for Hansard Speeches

**Status**: Specification
**Priority**: P0 (MVP - Core Functionality)
**Created**: 2025-10-23
**Updated**: 2025-10-23

---

## Problem Statement

Researchers, journalists, political analysts, and fact-checkers need to search and retrieve Australian Hansard parliamentary speeches to find relevant quotes, analyze policy positions, and verify statements. Currently, there is no programmatic way to perform semantic searches across parliamentary speeches or retrieve complete speech transcripts with their associated metadata (speaker, party, themes, entities, communications utility metrics).

### Current Pain Points:
- Users cannot search Hansard speeches by semantic meaning (e.g., "housing affordability crisis")
- No way to filter speeches by party, chamber, date range, or speaker
- Cannot retrieve full speech context when verifying quotes
- No access to rich metadata (entities mentioned, themes discussed, policy areas)
- Manual search through parliamentary archives is time-consuming

### User Impact:
- **Journalists**: Spend hours searching for relevant soundbites and quotes
- **Political Analysts**: Cannot efficiently track policy positions across parties
- **Fact-Checkers**: Difficult to verify quotes in their full context
- **Researchers**: No systematic way to analyze parliamentary discourse

---

## Solution Overview

Implement two Model Context Protocol (MCP) tools that provide programmatic access to Hansard speeches stored in a vector database:

1. **search_hansard**: Semantic search tool with metadata filtering
   - Search by natural language query (semantic similarity)
   - Filter by party, chamber, date range, speaker
   - Returns relevant speech chunks with metadata
   - Enables discovery of related speeches across time and speakers

2. **fetch_speech**: Speech retrieval tool
   - Retrieve complete speech by unique identifier
   - Returns full speech text reconstructed from chunks
   - Includes all metadata (29 fields: entities, themes, policy areas, communications utility)
   - Provides attribution and verification context

---

## User Scenarios & Testing *(mandatory)*

### Scenario 1: Journalist Finding Soundbites

**Actor**: Political journalist working on housing crisis story

**Context**: Needs quotes from Liberal Party MPs about housing affordability for tomorrow's article deadline

**User Flow**:
1. User opens Claude Desktop with MCP connection
2. User asks: "Find me quotes about housing affordability from Liberal Party members"
3. System calls `search_hansard(query="housing affordability", party="LP", limit=10)`
4. System returns 10 relevant speech chunks with speaker names, dates, and text
5. User reviews results and identifies interesting quote from Simon Kennedy
6. User asks: "Show me the full context of Simon Kennedy's speech"
7. System extracts speech_id from metadata and calls `fetch_speech(speech_id="267506-2024-05-28-129006")`
8. System returns complete speech with full paragraph context
9. User copies quote with proper attribution and verification link

**Success Criteria**:
- User finds relevant quotes in under 2 minutes
- Search returns semantically relevant results (not just keyword matches)
- Full speech context available for verification
- Attribution information (speaker, date, chamber) included

---

### Scenario 2: Policy Analyst Comparing Positions

**Actor**: Policy analyst tracking climate change policy evolution

**Context**: Writing report on how parties' climate positions have shifted over the past year

**User Flow**:
1. User asks: "What did MPs say about climate change between Jan and Dec 2024?"
2. System calls `search_hansard(query="climate change", date_from="2024-01-01", date_to="2024-12-31", limit=20)`
3. System returns speeches from multiple parties across the year
4. User notices pattern: Liberal Party speeches focus on "economic transition"
5. User asks: "Show me all Liberal Party speeches on climate in this period"
6. System calls `search_hansard(query="climate", party="LP", date_from="2024-01-01", date_to="2024-12-31")`
7. User analyzes results and identifies shift in rhetoric around August
8. User retrieves specific speeches using `fetch_speech()` for detailed analysis

**Success Criteria**:
- User can filter by date range to track temporal changes
- Search returns speeches from all relevant parties
- Metadata includes policy themes and stance indicators
- Results ordered by relevance (most semantically similar first)

---

### Scenario 3: Fact-Checker Verifying Quote

**Actor**: Fact-checking organization verifying viral social media quote

**Context**: Tweet claims "Simon Kennedy said housing affordability is not a crisis" - need to verify exact wording and context

**User Flow**:
1. User searches for the alleged quote
2. System calls `search_hansard(query="housing affordability crisis", speaker="Simon Kennedy", limit=5)`
3. System returns matching speech chunks showing Kennedy actually said "housing affordability *is* a crisis"
4. User requests full speech context
5. System calls `fetch_speech(speech_id="...")` and returns complete maiden speech
6. User reviews surrounding paragraphs to understand full context
7. User confirms the viral quote is misquoted (word "not" was incorrectly added)

**Success Criteria**:
- User verifies quote accuracy within 5 minutes
- Search handles speaker name matching (with or without honorifics)
- Full speech context reveals intended meaning
- System returns all metadata needed for authoritative fact-check report

---

## Functional Requirements *(mandatory)*

### FR-001: Semantic Search Capability
**Priority**: P0
**Description**: System MUST perform semantic similarity search across Hansard speeches using natural language queries

**Acceptance Criteria**:
- Search query parameter accepts natural language text (e.g., "housing crisis", "tax reform proposal")
- Results ranked by semantic similarity (vector distance) not keyword matching
- Returns top N most relevant speech chunks (default 10, max 50)
- Each result includes matched text chunk and relevance score

---

### FR-002: Metadata Filtering
**Priority**: P0
**Description**: System MUST support filtering search results by political party, chamber, date range, and speaker

**Acceptance Criteria**:
- `party` parameter filters by political party code (e.g., "LP", "ALP", "GRN")
- `chamber` parameter filters by "House of Representatives" or "Senate"
- `date_from` and `date_to` parameters filter by speech date (ISO 8601 format)
- `speaker` parameter filters by speaker name (case-insensitive, partial match)
- Filters can be combined (AND logic)
- Empty/null filters are ignored (no filtering applied)

---

### FR-003: Search Result Structure
**Priority**: P0
**Description**: Search results MUST include chunk text, metadata, and attribution information

**Acceptance Criteria**:
- Each result contains: chunk text, speaker name, party, chamber, date
- Results include speech_id for retrieving full speech
- Metadata includes: themes, entities mentioned, policy areas
- Communications utility metrics included: soundbite_potential, controversy_level
- Results returned as structured JSON/dict format

---

### FR-004: Speech Retrieval by ID
**Priority**: P0
**Description**: System MUST retrieve complete speech by unique identifier

**Acceptance Criteria**:
- `speech_id` parameter accepts unique speech identifier (format: "{speaker_id}-{date}-{utterance_id}")
- Returns complete speech text (all chunks concatenated in order)
- Includes all 29 metadata fields stored during ingestion
- Handles invalid/non-existent speech_id gracefully (error message)

---

### FR-005: Full Speech Reconstruction
**Priority**: P0
**Description**: System MUST reconstruct full speech text from chunks in correct order

**Acceptance Criteria**:
- Chunks ordered by chunk_index metadata field
- Text concatenated with proper spacing (paragraph breaks preserved)
- Full speech length matches original markdown file content
- No duplicate or missing chunks in reconstruction

---

### FR-006: Rich Metadata Access
**Priority**: P0
**Description**: Fetched speech MUST include all metadata from YAML frontmatter

**Acceptance Criteria**:
- Returns all 29 metadata fields: speaker, party, chamber, date, electorate, speech_type
- Includes nested structures: entities (people, organizations, places, legislation)
- Includes themes, subthemes, tags arrays
- Includes political_stance with government_position, criticism_targets, support_targets
- Includes communications_utility with soundbite_potential, controversy_level, quotable_phrases

---

### FR-007: Error Handling
**Priority**: P1
**Description**: System MUST handle invalid inputs and missing data gracefully

**Acceptance Criteria**:
- Invalid speech_id returns clear error message (not found)
- Empty search query returns error (minimum 2 characters required)
- Invalid date format returns validation error with correct format example
- Database connection errors return user-friendly message
- Tool errors logged for debugging but don't crash the MCP server

---

### FR-008: MCP Protocol Compliance
**Priority**: P0
**Description**: Tools MUST comply with Model Context Protocol specification

**Acceptance Criteria**:
- Tools registered with FastMCP using @mcp.tool() decorator
- Tool names follow naming convention: snake_case
- Tool descriptions provided for MCP discovery
- Parameter types specified (string, int, optional)
- Returns JSON-serializable data structures
- Tools callable via MCP Inspector and Claude Desktop

---

## Success Criteria *(mandatory)*

### Measurable Outcomes:

1. **Search Performance**
   - Users find relevant speeches in under 2 minutes (from query to result review)
   - Search returns semantically relevant results (user satisfaction >80% in feedback)
   - 95% of searches return at least 3 relevant results

2. **Retrieval Accuracy**
   - 100% of speech retrievals return complete text (no missing chunks)
   - All 29 metadata fields present in fetch responses
   - Speech reconstruction matches original markdown content exactly

3. **Usability**
   - New users successfully perform search and fetch within 5 minutes (no documentation)
   - Tools work seamlessly in Claude Desktop conversations
   - Error messages clear enough that users can self-correct (no support tickets)

4. **Availability**
   - Tools accessible 24/7 via MCP connection
   - Response time under 3 seconds for searches (10 results)
   - Response time under 2 seconds for speech retrieval

5. **Feature Adoption**
   - Both tools successfully tested in MCP Inspector
   - Tools used in at least 3 different research scenarios
   - Positive feedback from target users (journalists, analysts, researchers)

---

## Key Entities

### Speech Chunk
**Description**: Segment of a parliamentary speech stored in vector database

**Attributes**:
- chunk_text: The actual text content (800 characters avg)
- speech_id: Link to parent speech (format: "{speaker_id}-{date}-{utterance_id}")
- chunk_index: Position in original speech (0-indexed)
- embedding: 768-dimensional vector (Vertex AI text-embedding-005)
- langchain_metadata: JSONB field containing all metadata

### Speech Metadata
**Description**: Structured information about a parliamentary speech

**Core Fields**:
- speaker: Speaker's full name (normalized from "LastName, FirstName MP")
- party: Political party code (LP, ALP, GRN, NAT, etc.)
- chamber: House of Representatives or Senate
- date: Speech date (ISO 8601 format)
- electorate: Electoral division (for House of Representatives only)
- speech_type: maiden-speech, debate, question, etc.

**Analytical Fields**:
- entities: Nested dict with people, organizations, places, legislation arrays
- themes: Array of primary themes (e.g., ["housing-affordability", "economic-productivity"])
- subthemes: Array of secondary themes
- tags: Array of content tags
- policy_areas: Dict with primary, secondary, tertiary policy areas
- political_stance: Dict with government_position, criticism_targets, support_targets

**Communications Fields**:
- communications_utility: Dict with:
  - quotable_phrases: Array of notable quotes
  - soundbite_potential: "high", "medium", or "low"
  - controversy_level: "high", "medium", or "low"
  - local_news_value: Relevance to local media
  - social_media_shareable: Boolean indicator

**Parliamentary Context**:
- debate: Topic/bill being discussed
- parliamentary_interaction: Dict with points_of_order, interjections, etc.
- legislative_metadata: Dict with bill_reference, vote_position, amendment_moved

---

## Non-Functional Requirements

### Performance:
- Search queries return results within 3 seconds (95th percentile)
- Speech retrieval completes within 2 seconds (95th percentile)
- System handles 10 concurrent queries without degradation

### Scalability:
- Architecture supports adding more speeches (currently 64, designed for 10,000+)
- No hardcoded limits on result set sizes (configurable via parameters)

### Maintainability:
- Tool code follows project conventions (async/await, type hints)
- Clear error messages aid debugging
- Logging captures tool invocations and errors

---

## Assumptions

1. **Database Ready**: Assumes hansard_speeches table populated with 628 chunks (64 speeches) using LangChain schema
2. **Vector Store**: Assumes PostgreSQL with pgvector extension and LangChain's PostgresVectorStore
3. **Embeddings**: Assumes Vertex AI text-embedding-005 model for generating query embeddings
4. **Authentication**: Assumes Cloud SQL IAM authentication configured for MCP server service account
5. **MCP Server**: Assumes FastMCP server framework configured and running
6. **Date Format**: Assumes ISO 8601 date strings (YYYY-MM-DD) in user inputs and metadata
7. **Party Codes**: Assumes standard Australian party abbreviations (LP, ALP, GRN, NAT, etc.)
8. **Speaker Names**: Assumes normalized format "FirstName LastName" (without honorifics)

---

## Out of Scope *(optional)*

### Future Enhancements (Not in MVP):
- **Quote extraction tool**: Dedicated tool for finding high soundbite-potential sentences
- **Entity mention tracking**: Tool to find all mentions of specific people/organizations
- **Policy position analysis**: Compare policy stances across parties/speakers
- **Temporal tracking**: Analyze how discussions evolve over time
- **Aggregate statistics**: Generate summaries (speech counts, theme distribution)
- **Hierarchical chunking**: Search at sentence/paragraph/speech levels independently
- **Read-only service account**: Separate service account for query tools (security enhancement)

### Explicitly Excluded:
- ❌ Write operations (no tools for updating/deleting speeches)
- ❌ Data ingestion tools (separate ingestion pipeline already implemented)
- ❌ Real-time speech transcription (works with pre-ingested historical data)
- ❌ Natural language query parsing (users provide structured filter parameters)
- ❌ Export functionality (PDF, CSV, etc.)
- ❌ Visualization or dashboard UI
- ❌ Integration with external systems (Tableau, PowerBI, etc.)

---

## Dependencies

### Existing Infrastructure:
- PostgreSQL database (hansard-db-v2) with pgvector extension
- Cloud SQL instance with IAM authentication
- hansard_speeches table populated with vector embeddings
- Vertex AI API access for embedding generation
- FastMCP server framework running

### External Services:
- Google Cloud SQL (PostgreSQL)
- Google Cloud IAM (authentication)
- Vertex AI Embeddings API (text-embedding-005)

### Code Dependencies:
- langchain-google-cloud-sql-pg (PostgresEngine, PostgresVectorStore)
- langchain-google-vertexai (VertexAIEmbeddings)
- fastmcp (MCP server framework)

---

## Risks & Mitigations

### Risk 1: Semantic Search Returns Irrelevant Results
**Impact**: High - Users lose trust in tool if results don't match query intent
**Likelihood**: Medium
**Mitigation**:
- Use proven Vertex AI embeddings (text-embedding-005)
- Test with diverse queries before deployment
- Allow users to specify limit parameter to see more results
- Future: Add relevance feedback mechanism

### Risk 2: Database Connection Failures
**Impact**: High - Tools become unusable if database unreachable
**Likelihood**: Low
**Mitigation**:
- Use Cloud SQL's built-in high availability
- Implement connection pooling (LangChain handles this)
- Return clear error messages (don't expose internal details)
- Log failures for monitoring and alerting

### Risk 3: Slow Query Performance
**Impact**: Medium - Poor user experience if searches take >5 seconds
**Likelihood**: Low (current dataset small)
**Mitigation**:
- PostgreSQL indexes on date, party, chamber metadata fields (future enhancement)
- HNSW vector index already configured for similarity search
- Monitor query performance and optimize as dataset grows
- Consider caching for frequent queries (future)

---

## Open Questions

_None - Specification complete and ready for implementation planning._

---

## References

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [LangChain PostgresVectorStore Documentation](https://python.langchain.com/docs/integrations/vectorstores/google_cloud_sql_pg/)
- [FastMCP Framework](https://github.com/jlowin/fastmcp)
- [Hansard Ingestion Implementation](../002-real-hansard-ingestion/)
- [Future MCP Tools Design](../../docs/mcp-tools-future-design.md)
