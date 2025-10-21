# Data Model: Australian Hansard RAG

**Branch**: `001-hansard-rag-implementation`
**Date**: 2025-10-21
**Spec**: [spec.md](./spec.md)
**Research**: [research.md](./research.md)

---

## Overview

This document defines the data model for the Australian Hansard RAG system, using Cloud SQL PostgreSQL with pgvector extension (768-dimensional vectors) per the constitution (v2.6.0) Google ADK-aligned architecture.

**Database**: Cloud SQL PostgreSQL 15 with pgvector v0.8.0
**Vector Dimensions**: 768 (Vertex AI text-embedding-004)
**Index Type**: HNSW (m=24, ef_construction=100)

---

## Database Schema

### Table 1: `speeches`

Stores complete speech text and metadata for full-text retrieval and relational queries.

```sql
CREATE TABLE speeches (
    -- Primary key
    speech_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Speech content
    title TEXT NOT NULL,
    full_text TEXT NOT NULL,
    word_count INTEGER NOT NULL,
    content_hash TEXT NOT NULL UNIQUE,  -- SHA-256 for deduplication

    -- Speaker information
    speaker TEXT NOT NULL,
    party TEXT NOT NULL,
    chamber TEXT NOT NULL CHECK (chamber IN ('House of Representatives', 'Senate')),
    electorate TEXT,  -- NULL for Senators
    state TEXT NOT NULL CHECK (state IN ('NSW', 'VIC', 'QLD', 'WA', 'SA', 'TAS', 'ACT', 'NT')),

    -- Parliamentary context
    date DATE NOT NULL,
    hansard_reference TEXT NOT NULL,  -- e.g., "House Hansard, 23 March 2024, p.145"
    topic_tags TEXT[] NOT NULL DEFAULT '{}',  -- Array of topic tags

    -- Source tracking
    source_url TEXT,
    ingestion_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Indexes
    CONSTRAINT valid_electorate CHECK (
        (chamber = 'Senate' AND electorate IS NULL) OR
        (chamber = 'House of Representatives' AND electorate IS NOT NULL)
    )
);

-- Indexes for common queries
CREATE INDEX idx_speeches_speaker ON speeches(speaker);
CREATE INDEX idx_speeches_party ON speeches(party);
CREATE INDEX idx_speeches_chamber ON speeches(chamber);
CREATE INDEX idx_speeches_date ON speeches(date DESC);
CREATE INDEX idx_speeches_topic_tags ON speeches USING GIN(topic_tags);
CREATE INDEX idx_speeches_content_hash ON speeches(content_hash);

-- Full-text search index (PostgreSQL built-in)
CREATE INDEX idx_speeches_full_text_search ON speeches USING GIN(to_tsvector('english', full_text));
```

**Entity: Speech**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| speech_id | UUID | PRIMARY KEY, auto-generated | Unique identifier |
| title | TEXT | NOT NULL | Speech title/subject |
| full_text | TEXT | NOT NULL | Complete speech transcript |
| word_count | INTEGER | NOT NULL | Word count for analytics |
| content_hash | TEXT | NOT NULL, UNIQUE | SHA-256 hash for deduplication |
| speaker | TEXT | NOT NULL | MP/Senator name (e.g., "Anthony Albanese") |
| party | TEXT | NOT NULL | Political party (e.g., "Labor", "Liberal", "Greens") |
| chamber | TEXT | NOT NULL, CHECK | "House of Representatives" or "Senate" |
| electorate | TEXT | NULL for Senate | Electorate name (e.g., "Grayndler") |
| state | TEXT | NOT NULL, CHECK | Australian state/territory |
| date | DATE | NOT NULL | Speech date (ISO 8601) |
| hansard_reference | TEXT | NOT NULL | Official Hansard citation |
| topic_tags | TEXT[] | NOT NULL, DEFAULT '{}' | Array of topics (e.g., ["economy", "healthcare"]) |
| source_url | TEXT | NULL | Source URL if available |
| ingestion_timestamp | TIMESTAMPTZ | NOT NULL, DEFAULT NOW | When speech was ingested |

**Validation Rules**:
- `chamber`: Must be either "House of Representatives" or "Senate"
- `state`: Must be valid Australian state/territory (NSW, VIC, QLD, WA, SA, TAS, ACT, NT)
- `electorate`: Required for House members, NULL for Senators
- `content_hash`: SHA-256 hash of `full_text` for duplicate detection
- `word_count`: Calculated during ingestion

**Relationships**:
- One speech → Many speech_chunks (1:N)

---

### Table 2: `speech_chunks`

Stores text chunks with vector embeddings for semantic search, managed by LangChain's PostgresVectorStore.

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE speech_chunks (
    -- Primary key
    chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign key to speeches table
    speech_id UUID NOT NULL REFERENCES speeches(speech_id) ON DELETE CASCADE,

    -- Chunk content and position
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,  -- Position in speech (0-based)
    chunk_size INTEGER NOT NULL,   -- Character count

    -- Vector embedding (768 dimensions from Vertex AI text-embedding-004)
    embedding vector(768) NOT NULL,

    -- Metadata for filtering (denormalized for query performance)
    speaker TEXT NOT NULL,
    party TEXT NOT NULL,
    chamber TEXT NOT NULL,
    date DATE NOT NULL,
    topic_tags TEXT[] NOT NULL DEFAULT '{}',

    -- LangChain metadata (JSON for additional fields)
    langchain_metadata JSONB,

    -- Constraints
    UNIQUE(speech_id, chunk_index),
    CHECK (chunk_index >= 0),
    CHECK (chunk_size > 0)
);

-- HNSW index for fast vector similarity search
CREATE INDEX speech_chunks_embedding_hnsw ON speech_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (
    m = 24,                  -- Higher for 768-dim (default: 16)
    ef_construction = 100    -- Better recall (default: 64)
);

-- Indexes for metadata filtering
CREATE INDEX idx_chunks_speech_id ON speech_chunks(speech_id);
CREATE INDEX idx_chunks_speaker ON speech_chunks(speaker);
CREATE INDEX idx_chunks_party ON speech_chunks(party);
CREATE INDEX idx_chunks_chamber ON speech_chunks(chamber);
CREATE INDEX idx_chunks_date ON speech_chunks(date);
CREATE INDEX idx_chunks_topic_tags ON speech_chunks USING GIN(topic_tags);

-- PostgreSQL query optimization settings
ALTER DATABASE hansard SET maintenance_work_mem = '2GB';
ALTER DATABASE hansard SET max_parallel_workers_per_gather = 2;
ALTER DATABASE hansard SET shared_buffers = '1920MB';  -- 25% of 7.5 GB
ALTER DATABASE hansard SET effective_cache_size = '5GB';  -- 66% of RAM
```

**Entity: SpeechChunk**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| chunk_id | UUID | PRIMARY KEY, auto-generated | Unique identifier |
| speech_id | UUID | FOREIGN KEY, NOT NULL | Reference to parent speech |
| chunk_text | TEXT | NOT NULL | Text content of chunk (~800 chars) |
| chunk_index | INTEGER | NOT NULL, >= 0, UNIQUE with speech_id | Position in speech (0-based) |
| chunk_size | INTEGER | NOT NULL, > 0 | Character count |
| embedding | vector(768) | NOT NULL | 768-dimensional vector from Vertex AI |
| speaker | TEXT | NOT NULL | Denormalized from speeches table |
| party | TEXT | NOT NULL | Denormalized from speeches table |
| chamber | TEXT | NOT NULL | Denormalized from speeches table |
| date | DATE | NOT NULL | Denormalized from speeches table |
| topic_tags | TEXT[] | NOT NULL, DEFAULT '{}' | Denormalized from speeches table |
| langchain_metadata | JSONB | NULL | Additional LangChain metadata |

**Validation Rules**:
- `chunk_index`: Must be >= 0, unique per speech
- `chunk_size`: Must be > 0
- `embedding`: Must be exactly 768 dimensions
- Denormalized metadata must match parent speech

**Relationships**:
- Many chunks → One speech (N:1)

**Denormalization Rationale**:
- Metadata fields (`speaker`, `party`, `chamber`, `date`, `topic_tags`) are denormalized from `speeches` table
- Enables fast filtering during vector search without JOIN operations
- Trade-off: Slight storage overhead for significant query performance gain
- Consistency: Maintained via application logic during ingestion

---

## Pydantic Models

### SpeechMetadata (Input Validation)

```python
from pydantic import BaseModel, Field, field_validator, computed_field
from typing import Optional, List
from datetime import date
import hashlib

class SpeechMetadata(BaseModel):
    """Pydantic model for speech metadata validation during ingestion."""

    # Core identification
    speech_id: Optional[str] = Field(None, description="UUID v4 (auto-generated if not provided)")
    title: str = Field(..., min_length=1, max_length=500, description="Speech title/subject")

    # Content
    full_text: str = Field(..., min_length=10, description="Complete speech transcript")

    # Speaker information
    speaker: str = Field(..., min_length=1, max_length=200, description="MP/Senator name")
    party: str = Field(..., min_length=1, max_length=100, description="Political party")
    chamber: str = Field(..., description="House of Representatives or Senate")
    electorate: Optional[str] = Field(None, max_length=100, description="Electorate (House members only)")
    state: str = Field(..., description="Australian state/territory")

    # Parliamentary context
    date: date = Field(..., description="Speech date (ISO 8601)")
    hansard_reference: str = Field(..., min_length=1, max_length=500, description="Official Hansard citation")
    topic_tags: List[str] = Field(default_factory=list, description="Topic tags")

    # Source
    source_url: Optional[str] = Field(None, max_length=1000, description="Source URL")

    # Computed fields
    @computed_field
    @property
    def word_count(self) -> int:
        """Calculate word count from full_text."""
        return len(self.full_text.split())

    @computed_field
    @property
    def content_hash(self) -> str:
        """Generate SHA-256 hash for deduplication."""
        return hashlib.sha256(self.full_text.encode('utf-8')).hexdigest()

    # Validators
    @field_validator('chamber')
    @classmethod
    def validate_chamber(cls, v: str) -> str:
        """Validate chamber is valid Australian chamber."""
        valid_chambers = {'House of Representatives', 'Senate'}
        if v not in valid_chambers:
            raise ValueError(f"chamber must be one of: {valid_chambers}")
        return v

    @field_validator('state')
    @classmethod
    def validate_state(cls, v: str) -> str:
        """Validate state is valid Australian state/territory."""
        valid_states = {'NSW', 'VIC', 'QLD', 'WA', 'SA', 'TAS', 'ACT', 'NT'}
        if v not in valid_states:
            raise ValueError(f"state must be one of: {valid_states}")
        return v

    @field_validator('topic_tags')
    @classmethod
    def validate_topic_tags(cls, v: List[str]) -> List[str]:
        """Normalize topic tags (lowercase, strip whitespace)."""
        return [tag.strip().lower() for tag in v if tag.strip()]

    def model_post_init(self, __context) -> None:
        """Validate electorate based on chamber."""
        if self.chamber == 'Senate' and self.electorate is not None:
            raise ValueError("Senators cannot have electorate (must be NULL)")
        if self.chamber == 'House of Representatives' and self.electorate is None:
            raise ValueError("House members must have electorate")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Second Reading: Climate Change Bill 2024",
                "full_text": "Mr Speaker, I rise to speak on the Climate Change Bill...",
                "speaker": "Anthony Albanese",
                "party": "Labor",
                "chamber": "House of Representatives",
                "electorate": "Grayndler",
                "state": "NSW",
                "date": "2024-03-23",
                "hansard_reference": "House Hansard, 23 March 2024, p.145",
                "topic_tags": ["climate change", "environment", "energy policy"],
                "source_url": "https://www.aph.gov.au/Parliamentary_Business/Hansard"
            }
        }
```

### SpeechChunkMetadata (Internal Use)

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date

class SpeechChunkMetadata(BaseModel):
    """Metadata for individual speech chunks (used internally by LangChain)."""

    # Chunk identification
    chunk_id: Optional[str] = Field(None, description="UUID v4 (auto-generated)")
    speech_id: str = Field(..., description="Parent speech UUID")
    chunk_index: int = Field(..., ge=0, description="Position in speech (0-based)")
    chunk_size: int = Field(..., gt=0, description="Character count")

    # Denormalized metadata for filtering
    speaker: str = Field(..., description="Speaker name")
    party: str = Field(..., description="Political party")
    chamber: str = Field(..., description="Chamber")
    date: date = Field(..., description="Speech date")
    topic_tags: List[str] = Field(default_factory=list, description="Topic tags")

    # Additional metadata
    hansard_reference: str = Field(..., description="Official citation")

    class Config:
        json_schema_extra = {
            "example": {
                "speech_id": "550e8400-e29b-41d4-a716-446655440000",
                "chunk_index": 0,
                "chunk_size": 782,
                "speaker": "Anthony Albanese",
                "party": "Labor",
                "chamber": "House of Representatives",
                "date": "2024-03-23",
                "topic_tags": ["climate change", "environment"],
                "hansard_reference": "House Hansard, 23 March 2024, p.145"
            }
        }
```

### SearchResult (Output)

```python
from pydantic import BaseModel, Field
from typing import List
from datetime import date

class SearchResult(BaseModel):
    """Single search result returned by search_speeches tool."""

    # Identification
    speech_id: str = Field(..., description="Parent speech UUID")
    chunk_id: str = Field(..., description="Chunk UUID")

    # Content
    excerpt: str = Field(..., max_length=1000, description="Chunk text excerpt (up to 1000 chars)")
    full_text: Optional[str] = Field(None, description="Complete speech text (if requested)")

    # Metadata
    speaker: str = Field(..., description="Speaker name")
    party: str = Field(..., description="Political party")
    chamber: str = Field(..., description="Chamber")
    date: date = Field(..., description="Speech date")
    title: str = Field(..., description="Speech title")
    hansard_reference: str = Field(..., description="Official Hansard citation")
    topic_tags: List[str] = Field(default_factory=list, description="Topic tags")

    # Search metrics
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score (0-1)")
    chunk_index: int = Field(..., ge=0, description="Position in speech")

    class Config:
        json_schema_extra = {
            "example": {
                "speech_id": "550e8400-e29b-41d4-a716-446655440000",
                "chunk_id": "660e8400-e29b-41d4-a716-446655440001",
                "excerpt": "Mr Speaker, climate change is the defining challenge of our time...",
                "speaker": "Anthony Albanese",
                "party": "Labor",
                "chamber": "House of Representatives",
                "date": "2024-03-23",
                "title": "Second Reading: Climate Change Bill 2024",
                "hansard_reference": "House Hansard, 23 March 2024, p.145",
                "topic_tags": ["climate change", "environment"],
                "relevance_score": 0.87,
                "chunk_index": 0
            }
        }
```

---

## Text Chunking Strategy

**Implementation**: LangChain `RecursiveCharacterTextSplitter`

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,        # ~2-3 paragraphs per chunk
    chunk_overlap=150,     # Preserve context across boundaries
    length_function=len,   # Character count
    separators=["\n\n", "\n", ". ", " ", ""],  # Semantic boundaries
    is_separator_regex=False
)
```

**Rationale** (from research.md):
- **800 chars**: Preserves speech context (complete thoughts)
- **150 char overlap**: Prevents losing meaning at chunk boundaries
- **Semantic separators**: Maintains speech structure (paragraphs → sentences → words)
- **Character count**: Consistent with constitution specification

**Expected Output**:
- 10,000 speeches × ~12,000 chars = 120M chars
- 120M chars / (800 - 150) effective chunk size ≈ **15,000-20,000 chunks**

---

## Data Flow: Ingestion Pipeline

```
CSV/JSON Input
   │
   ├─> Pydantic Validation (SpeechMetadata)
   │   └─> Raise error if validation fails
   │
   ├─> Duplicate Check (content_hash)
   │   └─> Skip if exists in speeches table
   │
   ├─> Insert into speeches table
   │   └─> Get speech_id (UUID)
   │
   ├─> Text Chunking (RecursiveCharacterTextSplitter)
   │   └─> Generate chunks with overlap
   │
   ├─> Generate Embeddings (Vertex AI text-embedding-004)
   │   ├─> Task type: RETRIEVAL_DOCUMENT
   │   ├─> Output dimensions: 768
   │   └─> Batch size: 10 chunks per API call
   │
   └─> Insert into speech_chunks table
       ├─> chunk_text, chunk_index, embedding
       ├─> Denormalized metadata (speaker, party, chamber, date, topic_tags)
       └─> HNSW index automatically updated
```

---

## Data Flow: Search Query

```
User Query + Metadata Filters
   │
   ├─> Generate Query Embedding (Vertex AI text-embedding-004)
   │   ├─> Task type: RETRIEVAL_QUERY
   │   └─> Output dimensions: 768
   │
   ├─> Vector Similarity Search (PostgresVectorStore)
   │   ├─> HNSW index scan (vector_cosine_ops)
   │   ├─> Apply metadata filters (speaker, party, chamber, date, topic_tags)
   │   ├─> Set hnsw.ef_search = 40-80 for recall tuning
   │   └─> Return top-K chunks with scores
   │
   ├─> Enrich with Full Text (JOIN to speeches table)
   │   └─> SELECT full_text, title FROM speeches WHERE speech_id = ...
   │
   └─> Return SearchResult objects
       └─> Pydantic validation + serialization
```

---

## Migration from MVP (Future)

The MVP spec references ChromaDB + SQLite. Migration path to production schema:

1. **Export from MVP**:
   ```python
   # Export from ChromaDB + SQLite
   speeches_csv = export_speeches_to_csv()  # From SQLite
   embeddings_pkl = export_embeddings()      # From ChromaDB
   ```

2. **Import to Production**:
   ```python
   # Import to Cloud SQL PostgreSQL + pgvector
   for speech in speeches_csv:
       validate_and_insert_speech(speech)     # Insert into speeches table
       chunks = chunk_text(speech.full_text)
       embeddings = generate_embeddings(chunks)  # Vertex AI
       insert_chunks(chunks, embeddings)      # Insert into speech_chunks
   ```

3. **Validation**:
   - Compare search results (MVP vs Production) with golden dataset
   - Validate HNSW index performance (<200ms p95 latency)
   - Verify data integrity (row counts, content hashes)

---

## Summary

| Component | Technology | Specification |
|-----------|-----------|---------------|
| **Database** | Cloud SQL PostgreSQL 15 | db-custom-2-7680 (2 vCPU, 7.5 GB RAM) |
| **Vector Extension** | pgvector v0.8.0 | HNSW index (m=24, ef_construction=100) |
| **Vector Dimensions** | 768 | Vertex AI text-embedding-004 |
| **Tables** | 2 tables | `speeches` (full text + metadata), `speech_chunks` (vectors + chunks) |
| **Relationships** | 1:N | One speech → Many chunks |
| **Chunking** | RecursiveCharacterTextSplitter | 800 chars, 150 overlap |
| **Validation** | Pydantic v2 | SpeechMetadata, SpeechChunkMetadata, SearchResult |
| **Denormalization** | Metadata in chunks | Fast filtering without JOINs |

**Estimated Scale (10,000 speeches)**:
- Speeches table: 10,000 rows (~200 MB)
- Speech chunks table: 15,000-20,000 rows (~120 MB text + 61 MB vectors + 61 MB HNSW index)
- **Total**: ~450 MB (fits comfortably in 7.5 GB RAM instance)

---

**Data Model Version**: 1.0
**Alignment**: Constitution v2.6.0 (Google ADK architecture)
**Next**: See [contracts/](./contracts/) for MCP tool API specifications
