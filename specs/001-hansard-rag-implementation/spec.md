# Specification: Australian Hansard RAG MVP

**Status**: Draft
**Created**: 2025-10-21
**Owner**: Speech RAG Team
**Version**: 1.0.0

## Overview

Build a Retrieval-Augmented Generation (RAG) server using FastMCP on Google Cloud Run for searching and analyzing Australian Hansard transcripts and political communications with semantic search and metadata filtering.

## Objective

Enable AI assistants (Claude Desktop, Claude Code, Cursor) to search, retrieve, and analyze Australian parliamentary speeches (Hansard) and political communications from MPs and Senators using hybrid search (semantic + metadata filtering) via the Model Context Protocol (MCP).

## Success Criteria

1. **Functional Requirements Met**:
   - ✅ Ingest 10 sample Australian Hansard speeches from CSV/JSON
   - ✅ Semantic search working with sample queries
   - ✅ Metadata filtering by speaker, date, topic
   - ✅ Results include citations and context
   - ✅ Accessible via MCP clients (Claude Desktop minimum)

2. **Technical Requirements Met**:
   - ✅ FastMCP server running locally with `fastmcp dev`
   - ✅ Vector embeddings stored in ChromaDB (local development)
   - ✅ Metadata stored in SQLite (local development)
   - ✅ Search latency <500ms for local queries
   - ✅ Infrastructure deployable to Cloud Run (ready, not deployed yet)

3. **Quality Requirements Met**:
   - ✅ Test coverage >80% for core search functionality
   - ✅ MCP Inspector shows all tools working
   - ✅ End-to-end demo works: ingest → search → retrieve
   - ✅ Documentation complete for local development setup

## Scope

### In Scope (MVP)

**Core Functionality**:
1. **Speech Ingestion Tool** (`ingest_speech`):
   - Load speeches from CSV/JSON files
   - Extract metadata: speaker, date, event, topic_tags, chamber (House/Senate)
   - Chunk text using RecursiveCharacterTextSplitter (800 chars, 150 overlap)
   - Generate embeddings using sentence-transformers/all-MiniLM-L6-v2
   - Store in ChromaDB + SQLite

2. **Hybrid Search Tool** (`search_speeches`):
   - Semantic vector search via ChromaDB
   - Metadata filtering (speaker, date range, chamber, topics)
   - Return top-K results with relevance scores
   - Include excerpt + citation

3. **Speech Retrieval Tool** (`get_speech`):
   - Retrieve full speech by ID
   - Include all metadata
   - Optional: surrounding context (previous/next chunks)

**Data Schema** (Australian Context):
```python
SpeechMetadata:
  - speech_id: str (UUID)
  - title: str
  - speaker: str (MP/Senator name)
  - party: str (Labor, Liberal, Greens, etc.)
  - chamber: str ("House of Representatives" | "Senate")
  - date: str (ISO 8601)
  - hansard_reference: str (Official Hansard citation)
  - topic_tags: List[str]
  - electorate: Optional[str] (for House members)
  - state: str (NSW, VIC, QLD, etc.)
  - source_url: Optional[str]
```

**Technology Stack (Local Development)**:
- FastMCP 2.14.0+
- ChromaDB (local vector database)
- SQLite (local metadata storage)
- sentence-transformers/all-MiniLM-L6-v2
- LangChain (text splitting)
- Pydantic v2 (data validation)

**Sample Dataset**:
- 10 Australian Hansard speeches (CSV/JSON format)
- Mix of House and Senate
- Multiple parties represented
- Date range: Recent (2023-2024)

### Out of Scope (MVP)

**Deferred to Future Phases**:
- ❌ GitHub OAuth authentication (defer to v2)
- ❌ Cloud deployment (Cloud Run, Redis, Qdrant, PostgreSQL)
- ❌ Large-scale corpus (1,000-5,000 speeches)
- ❌ Advanced features (cross-encoder reranking, summarization)
- ❌ Real-time Hansard ingestion (API scraping)
- ❌ ChatGPT integration
- ❌ Response caching (Redis)
- ❌ Multi-user support
- ❌ Batch ingestion from web scraping

**Explicitly Not Included**:
- Web interface (MCP clients only)
- User management
- Payment/billing
- Analytics/logging beyond basic
- Hansard PDF parsing (assume clean text input)

## Requirements

### Functional Requirements

**FR1: Speech Ingestion**
- **FR1.1**: Accept CSV/JSON input with required fields: text, speaker, date, chamber
- **FR1.2**: Validate metadata using Pydantic models
- **FR1.3**: Chunk text into 800-character segments with 150-character overlap
- **FR1.4**: Generate 384-dimensional embeddings for each chunk
- **FR1.5**: Store embeddings in ChromaDB with metadata
- **FR1.6**: Store full speech + metadata in SQLite
- **FR1.7**: Return ingestion summary (chunks created, vectors stored)
- **FR1.8**: Handle duplicate detection (skip if speech_id exists)

**FR2: Hybrid Search**
- **FR2.1**: Accept text query + optional metadata filters
- **FR2.2**: Generate query embedding
- **FR2.3**: Perform vector similarity search in ChromaDB
- **FR2.4**: Apply metadata filters (speaker, date range, chamber, party, topics)
- **FR2.5**: Return top-K results (default: 10, max: 50)
- **FR2.6**: Include for each result: excerpt, speaker, date, chamber, relevance score, speech_id
- **FR2.7**: Sort by relevance score (descending)

**FR3: Speech Retrieval**
- **FR3.1**: Accept speech_id parameter
- **FR3.2**: Retrieve full speech text from SQLite
- **FR3.3**: Retrieve all metadata
- **FR3.4**: Return structured response with complete speech
- **FR3.5**: Include Hansard reference/citation
- **FR3.6**: Optional: Include surrounding chunks for context

### Non-Functional Requirements

**NFR1: Performance**
- **NFR1.1**: Search latency <500ms (p95) for local queries
- **NFR1.2**: Embedding generation <100ms per chunk
- **NFR1.3**: Ingestion throughput: 1 speech per second minimum
- **NFR1.4**: Handle 10-50 concurrent MCP client requests (future Cloud Run)

**NFR2: Quality**
- **NFR2.1**: Test coverage >80% for core tools
- **NFR2.2**: Search recall >90% on golden dataset (10 test queries)
- **NFR2.3**: No hallucinated metadata (exact match from source)
- **NFR2.4**: Chunking preserves sentence boundaries

**NFR3: Usability**
- **NFR3.1**: Tools discoverable via `list_tools()` with clear descriptions
- **NFR3.2**: Error messages are actionable and user-friendly
- **NFR3.3**: MCP Inspector can test all tools interactively
- **NFR3.4**: README provides complete local development setup

**NFR4: Maintainability**
- **NFR4.1**: Code follows FastMCP constitution standards
- **NFR4.2**: All tools use Pydantic models for input validation
- **NFR4.3**: Modular architecture (separate ingestion, search, storage modules)
- **NFR4.4**: Configuration via environment variables (.env file)

**NFR5: Future-Proofing**
- **NFR5.1**: Database abstraction layer (easy swap ChromaDB → Qdrant)
- **NFR5.2**: Metadata schema supports future expansion
- **NFR5.3**: Cloud Run deployment configuration prepared (not deployed)
- **NFR5.4**: GitHub OAuth integration points identified (not implemented)

## Constraints

### Technical Constraints

1. **Local Development Only (MVP)**:
   - No cloud deployment in MVP
   - ChromaDB (not Qdrant Cloud)
   - SQLite (not PostgreSQL)
   - No Redis caching

2. **MCP Protocol**:
   - Must use STDIO transport for local MCP clients
   - All tools must return valid MCP content types
   - Compatible with Claude Desktop, Claude Code, Cursor

3. **Embedding Model**:
   - Must use sentence-transformers/all-MiniLM-L6-v2 (384 dims)
   - Model loaded in-memory (no API calls)
   - No GPU required (CPU-only fine)

4. **Data Format**:
   - Input: CSV or JSON only (no PDF/HTML parsing)
   - Text must be pre-cleaned (assume clean Hansard transcripts)
   - Metadata must include minimum required fields

### Business Constraints

1. **Budget**:
   - MVP: $0 (local development only)
   - Future deployment: $70-80/month (within Google Cloud credits)

2. **Timeline**:
   - MVP delivery: 1-2 weeks
   - First 10 speeches ingested and searchable: Day 3-4
   - Full testing complete: End of Week 2

3. **Team**:
   - Single developer (you)
   - AI assistant support (Claude Code)
   - GitHub SpecKit for spec-driven development

### Compliance Constraints

1. **Australian Parliamentary Data**:
   - Hansard transcripts are public domain (no copyright issues)
   - Attribution required (include Hansard reference in citations)
   - No modification of official transcript text (preserve verbatim)

2. **Privacy**:
   - All data is public political speech (no PII concerns)
   - No user tracking in MVP (deferred to production)

## Data Schema

### SpeechMetadata (Pydantic Model)

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

class SpeechMetadata(BaseModel):
    """Metadata for Australian parliamentary speeches."""

    # Core identification
    speech_id: str = Field(description="Unique identifier (UUID v4)")
    title: str = Field(description="Speech title or topic")
    speaker: str = Field(description="Full name of speaker (MP/Senator)")

    # Political context
    party: str = Field(description="Political party (Labor, Liberal, Greens, National, Independent, etc.)")
    chamber: str = Field(description="House of Representatives or Senate")
    electorate: Optional[str] = Field(default=None, description="Electorate (for House members only)")
    state: str = Field(description="Australian state/territory (NSW, VIC, QLD, SA, WA, TAS, NT, ACT)")

    # Temporal & reference
    date: str = Field(description="Speech date (ISO 8601: YYYY-MM-DD)")
    hansard_reference: str = Field(description="Official Hansard citation (e.g., 'House Hansard, 21 Oct 2024, p. 42')")

    # Content classification
    topic_tags: List[str] = Field(default_factory=list, description="Topics (economy, healthcare, climate, etc.)")
    debate_type: Optional[str] = Field(default=None, description="Question Time, General Business, Bills, etc.")

    # Source
    source_url: Optional[str] = Field(default=None, description="URL to official Hansard record")
    transcript_quality: str = Field(default="verbatim", description="verbatim, edited, or summary")

    # Speech structure (for chunks)
    chunk_index: Optional[int] = Field(default=None, description="Position of chunk in speech (0-indexed)")
    total_chunks: Optional[int] = Field(default=None, description="Total chunks for this speech")
```

### CSV/JSON Input Format

**CSV Example**:
```csv
speech_id,title,speaker,party,chamber,electorate,state,date,hansard_reference,topic_tags,source_url,text
uuid-1,"Climate Action Urgency","Adam Bandt","Greens","House of Representatives","Melbourne","VIC","2024-10-15","House Hansard, 15 Oct 2024, p. 12","climate,environment,renewable_energy","https://hansard.example.gov.au/...","Mr BANDT (Melbourne) (14:32): Mr Speaker, the climate crisis..."
```

**JSON Example**:
```json
{
  "speeches": [
    {
      "speech_id": "uuid-1",
      "title": "Climate Action Urgency",
      "speaker": "Adam Bandt",
      "party": "Greens",
      "chamber": "House of Representatives",
      "electorate": "Melbourne",
      "state": "VIC",
      "date": "2024-10-15",
      "hansard_reference": "House Hansard, 15 Oct 2024, p. 12",
      "topic_tags": ["climate", "environment", "renewable_energy"],
      "source_url": "https://hansard.example.gov.au/...",
      "text": "Mr BANDT (Melbourne) (14:32): Mr Speaker, the climate crisis requires immediate action..."
    }
  ]
}
```

## MCP Tools Specification

### Tool 1: ingest_speech

```python
@mcp.tool(tags=["ingestion", "admin", "stable"])
async def ingest_speech(
    file_path: str,
    format: str = "json",
    ctx: Context = None
) -> IngestionResult:
    """
    Ingest Australian Hansard speeches from CSV/JSON file.

    Args:
        file_path: Path to CSV or JSON file containing speeches
        format: File format ("csv" or "json")
        ctx: MCP context for logging

    Returns:
        IngestionResult with summary of ingestion
    """
```

**Returns**:
```python
class IngestionResult(BaseModel):
    speeches_processed: int
    chunks_created: int
    vectors_stored: int
    duplicates_skipped: int
    errors: List[str]
    processing_time_seconds: float
```

### Tool 2: search_speeches

```python
@mcp.tool(tags=["search", "rag", "stable"], readOnlyHint=True)
async def search_speeches(
    query: str,
    speaker: Optional[str] = None,
    party: Optional[str] = None,
    chamber: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    topics: Optional[List[str]] = None,
    state: Optional[str] = None,
    top_k: int = 10,
    ctx: Context = None
) -> List[SpeechSearchResult]:
    """
    Hybrid search for Australian parliamentary speeches.

    Combines semantic vector search with metadata filtering.

    Args:
        query: Text query for semantic search
        speaker: Filter by MP/Senator name
        party: Filter by political party
        chamber: Filter by "House of Representatives" or "Senate"
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        topics: Filter by topic tags
        state: Filter by Australian state/territory
        top_k: Number of results to return (default: 10, max: 50)
        ctx: MCP context for logging

    Returns:
        List of search results with excerpts and metadata
    """
```

**Returns**:
```python
class SpeechSearchResult(BaseModel):
    speech_id: str
    speaker: str
    party: str
    chamber: str
    date: str
    title: str
    excerpt: str  # 500-character excerpt centered on match
    relevance_score: float  # 0.0 to 1.0
    hansard_reference: str
    topic_tags: List[str]
    source_url: Optional[str]
```

### Tool 3: get_speech

```python
@mcp.tool(tags=["retrieve", "rag", "stable"], readOnlyHint=True)
async def get_speech(
    speech_id: str,
    include_context: bool = False,
    ctx: Context = None
) -> SpeechDetail:
    """
    Retrieve complete speech by ID.

    Args:
        speech_id: Unique speech identifier
        include_context: Include surrounding chunks for context
        ctx: MCP context for logging

    Returns:
        Complete speech with all metadata
    """
```

**Returns**:
```python
class SpeechDetail(BaseModel):
    speech_id: str
    title: str
    speaker: str
    party: str
    chamber: str
    electorate: Optional[str]
    state: str
    date: str
    hansard_reference: str
    topic_tags: List[str]
    full_text: str
    word_count: int
    source_url: Optional[str]
    context_before: Optional[str]  # If include_context=True
    context_after: Optional[str]   # If include_context=True
```

## Testing Strategy

### Unit Tests

**Test Coverage Target**: >80%

1. **Data Models** (Pydantic):
   - Valid metadata validation
   - Invalid data rejection
   - Optional field handling
   - Date format validation

2. **Text Processing**:
   - Chunking with correct overlap
   - Embedding generation
   - Metadata extraction

3. **Search Logic**:
   - Query embedding generation
   - Metadata filter construction
   - Result sorting and ranking

### Integration Tests

1. **End-to-End Ingestion**:
   - Load sample CSV
   - Verify ChromaDB storage
   - Verify SQLite storage
   - Check duplicate handling

2. **End-to-End Search**:
   - Search with no filters
   - Search with speaker filter
   - Search with date range
   - Search with multiple filters
   - Verify result accuracy

3. **MCP Client Compatibility**:
   - Test with MCP Inspector
   - Test with Claude Desktop
   - Verify tool discovery
   - Verify error handling

### Quality Tests

1. **Search Quality** (Golden Dataset):
   - 10 test queries with expected results
   - Measure recall (found / expected)
   - Target: >90% recall

2. **Performance Tests**:
   - Search latency measurement (p50, p95, p99)
   - Embedding generation speed
   - Ingestion throughput

3. **Edge Cases**:
   - Empty query
   - Malformed filters
   - Non-existent speech_id
   - Invalid CSV format
   - Duplicate ingestion

## Dependencies

### External Services

**None for MVP** (local development only)

Future (Cloud deployment):
- Google Cloud Run
- Qdrant Cloud
- Cloud Memorystore for Redis
- Cloud SQL for PostgreSQL

### Python Packages

```toml
[project]
dependencies = [
    "fastmcp>=2.14.0",
    "sentence-transformers>=2.2.2",
    "chromadb>=0.4.0",
    "langchain>=0.1.0",
    "pydantic>=2.5.0",
    "pandas>=2.0.0",  # CSV processing
    "python-dateutil>=2.8.2",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.7.0",
]
```

### Development Tools

- Python 3.11+
- uv (package manager)
- MCP Inspector (testing)
- Claude Desktop / Claude Code (MCP client)
- Git (version control)
- GitHub SpecKit (spec-driven development)

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Chunking loses context** | High | Medium | Use 150-char overlap, test with golden dataset |
| **Search quality poor** | High | Low | Use proven embedding model, tune chunk size |
| **ChromaDB performance issues** | Medium | Low | Profile queries, optimize if needed |
| **Sample data not representative** | Medium | Medium | Choose diverse speeches (parties, chambers, topics) |
| **MCP client incompatibility** | High | Low | Test with MCP Inspector + Claude Desktop early |
| **Cloud migration difficulty** | Medium | Low | Use database abstraction layer from start |

## Acceptance Criteria

The MVP is **accepted** when ALL of the following are true:

- [ ] **AC1**: 10 Australian Hansard speeches successfully ingested from CSV/JSON
- [ ] **AC2**: `search_speeches` returns relevant results for 10 test queries
- [ ] **AC3**: Metadata filtering works correctly (speaker, chamber, date, party)
- [ ] **AC4**: `get_speech` retrieves complete speech with all metadata
- [ ] **AC5**: MCP Inspector shows all 3 tools working
- [ ] **AC6**: Claude Desktop can connect and use all tools
- [ ] **AC7**: Test coverage >80% (pytest-cov report)
- [ ] **AC8**: Search latency <500ms (p95) for local queries
- [ ] **AC9**: README documents complete local development setup
- [ ] **AC10**: No critical bugs in core search functionality
- [ ] **AC11**: Hansard references included in all results
- [ ] **AC12**: Code follows FastMCP constitution standards

## Timeline

**Estimated Duration**: 10-12 days

**Milestones**:
- **Day 1-2**: Project setup, data models, database setup
- **Day 3-4**: Ingestion tool + test with 10 speeches
- **Day 5-7**: Search tool implementation + testing
- **Day 8-9**: Retrieval tool + MCP client testing
- **Day 10-12**: Documentation, refinement, acceptance testing

## Appendix

### Sample Test Queries (Golden Dataset)

1. "climate change action"
2. "healthcare funding"
3. "economic policy"
4. "renewable energy transition"
5. "housing affordability"
6. "education reform"
7. "immigration policy"
8. "foreign affairs"
9. "indigenous reconciliation"
10. "budget surplus"

### Australian Political Parties (Reference)

- Labor (ALP)
- Liberal
- National
- Greens
- One Nation
- United Australia Party (UAP)
- Independent
- Katter's Australian Party
- Centre Alliance

### Australian States/Territories

- NSW (New South Wales)
- VIC (Victoria)
- QLD (Queensland)
- SA (South Australia)
- WA (Western Australia)
- TAS (Tasmania)
- NT (Northern Territory)
- ACT (Australian Capital Territory)

---

**Document Status**: Ready for Review
**Next Steps**: Create implementation plan using `/speckit.plan`
