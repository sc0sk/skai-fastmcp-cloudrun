# Data Model: Admin Markdown Ingestion

**Feature**: 012-admin-markdown-ingestion
**Date**: 2025-10-24
**Purpose**: Define data structures, validation rules, and relationships

## Entity Overview

```
┌─────────────────┐
│ MarkdownFile    │
│ (Input)         │
└────────┬────────┘
         │ parses to
         ▼
┌─────────────────┐      ┌──────────────────┐
│ SpeechMetadata  │──────│ VectorChunk      │
│ (speeches table)│ 1:N  │ (langchain_pg_   │
└─────────────────┘      │  embedding table)│
         │               └──────────────────┘
         │ tracks via
         ▼
┌─────────────────┐
│ IngestionJob    │
│ (logs/tracking) │
└─────────────────┘
```

## Entities

### 1. MarkdownFile (Input Model)

**Purpose**: Represents a markdown file with YAML frontmatter before parsing

**Structure**:
```python
class MarkdownFileInput(BaseModel):
    """Input specification for markdown file ingestion."""

    file_path: str = Field(
        description="Absolute or relative path to markdown file"
    )
    validate_path: bool = Field(
        default=True,
        description="Whether to validate path is within allowed directory"
    )
    duplicate_policy: DuplicatePolicy = Field(
        default=DuplicatePolicy.SKIP,
        description="How to handle duplicate speech_id"
    )

class DuplicatePolicy(str, Enum):
    """Policy for handling duplicate speech IDs."""
    SKIP = "skip"       # Skip if exists (no-op)
    UPDATE = "update"   # Update existing record
    ERROR = "error"     # Raise error on duplicate
```

**Validation Rules**:
- `file_path` MUST be non-empty string
- If `validate_path` is True, path MUST resolve within `INGESTION_BASE_DIR`
- File MUST exist and be readable
- File MUST be valid UTF-8 text

**State Transitions**: None (input only)

---

### 2. SpeechFrontmatter (Parsed Metadata)

**Purpose**: Represents extracted YAML frontmatter from markdown file

**Structure**:
```python
class SpeechFrontmatter(BaseModel):
    """Parsed frontmatter metadata from markdown file."""

    speech_id: str = Field(
        description="Unique identifier for speech (from frontmatter)"
    )
    speaker: str = Field(
        min_length=1,
        max_length=200,
        description="Speaker name"
    )
    party: PartyEnum = Field(
        description="Political party affiliation"
    )
    chamber: ChamberEnum = Field(
        description="Parliamentary chamber (REPS or SENATE)"
    )
    date: date = Field(
        description="Speech date in ISO 8601 format"
    )
    title: str = Field(
        min_length=1,
        max_length=500,
        description="Speech title or topic"
    )
    state: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Electoral state/territory (optional)"
    )
    hansard_reference: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Official Hansard reference number (optional)"
    )

class PartyEnum(str, Enum):
    """Australian political parties."""
    LIBERAL = "Liberal"
    LABOR = "Labor"
    GREENS = "Greens"
    NATIONAL = "National"
    INDEPENDENT = "Independent"

class ChamberEnum(str, Enum):
    """Parliamentary chambers."""
    REPS = "REPS"           # House of Representatives
    SENATE = "SENATE"       # Senate
```

**Validation Rules**:
- All required fields MUST be present in frontmatter
- `speech_id` MUST be unique across all speeches (enforced by database)
- `speaker` MUST be non-empty (1-200 chars)
- `party` MUST be valid PartyEnum value
- `chamber` MUST be valid ChamberEnum value
- `date` MUST be valid ISO 8601 date (YYYY-MM-DD), not in future
- `title` MUST be non-empty (1-500 chars)
- `state` if provided, MUST be 2-3 letter Australian state code (NSW, VIC, QLD, WA, SA, TAS, ACT, NT)

**Relationship**: 1:1 with SpeechMetadata after ingestion

---

### 3. SpeechMetadata (Database Entity)

**Purpose**: Represents stored speech metadata in PostgreSQL speeches table

**Structure**:
```python
class SpeechMetadata(BaseModel):
    """Complete speech metadata stored in database."""

    speech_id: str = Field(primary_key=True)
    speaker: str
    party: str  # Stored as string in DB
    chamber: str  # Stored as string in DB
    state: Optional[str]
    date: date
    title: str
    text: str  # Full markdown content
    word_count: int  # Computed from text
    hansard_reference: Optional[str]
    created_at: datetime  # Auto-generated
    updated_at: datetime  # Auto-updated

    # Computed fields
    chunk_count: int  # Number of associated vector chunks
```

**Database Schema**:
```sql
CREATE TABLE IF NOT EXISTS speeches (
    speech_id VARCHAR(255) PRIMARY KEY,
    speaker VARCHAR(200) NOT NULL,
    party VARCHAR(50) NOT NULL,
    chamber VARCHAR(10) NOT NULL,
    state VARCHAR(10),
    date DATE NOT NULL,
    title VARCHAR(500) NOT NULL,
    text TEXT NOT NULL,
    word_count INTEGER NOT NULL,
    hansard_reference VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_speeches_date ON speeches(date);
CREATE INDEX idx_speeches_speaker ON speeches(speaker);
CREATE INDEX idx_speeches_party ON speeches(party);
CREATE INDEX idx_speeches_chamber ON speeches(chamber);
```

**Validation Rules**:
- `speech_id` MUST be unique (primary key constraint)
- `word_count` MUST be computed accurately from text (using `len(text.split())`)
- `created_at` and `updated_at` MUST be automatically managed by database
- All constraints from SpeechFrontmatter apply

**Relationships**:
- 1:N with VectorChunk (one speech has many chunks)
- 1:N with IngestionLog (one speech referenced in multiple ingestion attempts)

---

### 4. VectorChunk (Embedding Entity)

**Purpose**: Represents a text chunk with its vector embedding in langchain_pg_embedding table

**Structure**:
```python
class VectorChunk(BaseModel):
    """Text chunk with vector embedding."""

    chunk_id: str  # UUID generated by LangChain
    speech_id: str  # Foreign key to speeches table
    chunk_index: int  # Position within speech (0-based)
    chunk_total: int  # Total chunks for this speech
    chunk_text: str  # Actual text content
    embedding: list[float]  # 768-dim vector from text-embedding-005
    metadata: dict  # Additional metadata (speaker, party, chamber, date)

    # Metadata fields for filtering
    speaker: str
    party: str
    chamber: str
    date: str  # ISO 8601 date string
```

**LangChain Schema** (managed by LangChain):
```sql
CREATE TABLE langchain_pg_embedding (
    uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document TEXT NOT NULL,  -- chunk_text
    cmetadata JSONB,         -- metadata dict
    embedding vector(768)    -- pgvector type
);

CREATE INDEX ON langchain_pg_embedding
    USING ivfflat (embedding vector_cosine_ops);
```

**Validation Rules**:
- `chunk_index` MUST be 0 <= index < chunk_total
- `chunk_total` MUST match actual number of chunks for speech_id
- `chunk_text` MUST be non-empty
- `embedding` MUST be exactly 768 dimensions (text-embedding-005 output)
- `metadata` MUST include: speech_id, speaker, party, chamber, date, chunk_index, chunk_total

**Relationships**:
- N:1 with SpeechMetadata (many chunks belong to one speech)

---

### 5. IngestionJob (Tracking Entity)

**Purpose**: Represents a single or bulk ingestion operation for logging and auditing

**Structure**:
```python
class IngestionJob(BaseModel):
    """Ingestion operation tracking."""

    job_id: str  # UUID
    job_type: JobType  # SINGLE or BULK
    started_at: datetime
    completed_at: Optional[datetime]
    status: JobStatus
    admin_user: str  # From bearer token claims
    file_paths: list[str]  # Files to ingest
    total_files: int
    succeeded_count: int
    failed_count: int
    failures: list[IngestionFailure]  # Detailed error records

class JobType(str, Enum):
    """Type of ingestion operation."""
    SINGLE = "single"
    BULK = "bulk"

class JobStatus(str, Enum):
    """Ingestion job status."""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some succeeded, some failed

class IngestionFailure(BaseModel):
    """Detailed failure record."""
    file_path: str
    error_type: str  # e.g., "ValidationError", "DatabaseError"
    error_message: str
    timestamp: datetime
```

**Storage**: In-memory or separate `ingestion_logs` table (optional for MVP)

**Validation Rules**:
- `job_id` MUST be unique UUID
- `succeeded_count + failed_count` MUST equal `total_files`
- `status` = COMPLETED when all files processed
- `status` = PARTIAL when some succeeded, some failed
- `status` = FAILED when all files failed

**State Transitions**:
```
IN_PROGRESS → COMPLETED (all succeeded)
IN_PROGRESS → PARTIAL (some failed)
IN_PROGRESS → FAILED (all failed)
```

---

## Validation Summary

### Metadata Validation Pipeline

```
1. File Path Validation
   ├─ Path exists?
   ├─ Within base directory?
   └─ UTF-8 encoded?

2. Frontmatter Parsing
   ├─ Valid YAML syntax?
   ├─ All required fields present?
   └─ Frontmatter delimiters (---) correct?

3. Field Format Validation
   ├─ speech_id: non-empty string
   ├─ speaker: 1-200 chars
   ├─ party: valid PartyEnum
   ├─ chamber: valid ChamberEnum
   ├─ date: ISO 8601, not future
   ├─ title: 1-500 chars
   └─ state: optional, 2-3 chars

4. Content Validation
   ├─ Text not empty?
   ├─ Text under 10MB?
   └─ Valid markdown structure?

5. Duplicate Check
   ├─ speech_id exists in DB?
   └─ Apply duplicate policy
```

### Error Messages

| Validation Failure | Error Message | Error Type |
|-------------------|---------------|------------|
| File not found | `File not found: {path}` | `FileNotFoundError` |
| Outside base dir | `Path outside allowed directory: {path}` | `ValueError` |
| No frontmatter | `Markdown file missing YAML frontmatter` | `ValueError` |
| Malformed YAML | `Invalid YAML in frontmatter: {yaml_error}` | `ValueError` |
| Missing required field | `Required field '{field}' missing from frontmatter` | `ValidationError` |
| Invalid date format | `Invalid date format: {value}. Expected YYYY-MM-DD` | `ValidationError` |
| Invalid party | `Invalid party: {value}. Must be one of: {enum_values}` | `ValidationError` |
| Duplicate speech_id | `Speech ID '{speech_id}' already exists` | `DuplicateError` |
| Empty text content | `Speech text content is empty` | `ValueError` |

## Data Flow

```
Input File
    │
    ├─ Parse Frontmatter → SpeechFrontmatter
    │                            │
    │                            ├─ Validate → ValidationError?
    │                            │
    │                            └─ Transform → SpeechMetadata
    │
    ├─ Extract Content → Markdown Text
    │                         │
    │                         ├─ Chunk → list[str]
    │                         │
    │                         ├─ Embed → list[vector(768)]
    │                         │
    │                         └─ Package → list[VectorChunk]
    │
    └─ Transaction BEGIN
            │
            ├─ INSERT SpeechMetadata
            │
            ├─ INSERT VectorChunk (bulk)
            │
            └─ COMMIT (or ROLLBACK on error)
                    │
                    └─ Update IngestionJob
```

## Performance Considerations

### Database Indexes

Required indexes for efficient queries:
- `speeches.speech_id` (primary key, automatic)
- `speeches.date` (range queries)
- `speeches.speaker` (filtering)
- `speeches.party` (filtering)
- `speeches.chamber` (filtering)
- `langchain_pg_embedding.embedding` (vector similarity, ivfflat index)

### Batch Operations

- Bulk insert vector chunks (100-500 at a time)
- Batch embedding generation (250 texts per API call)
- Transaction per file (not per chunk)

### Memory Usage

- Stream file reading (don't load entire file into memory)
- Process chunks sequentially (don't accumulate all embeddings)
- Clear embeddings after database insert

## Testing Checklist

- [ ] Valid frontmatter parsing
- [ ] Malformed YAML handling
- [ ] Missing required fields
- [ ] Invalid enum values
- [ ] Date format validation
- [ ] Duplicate speech_id (all policies)
- [ ] Path traversal prevention
- [ ] Transaction rollback on error
- [ ] Chunk count accuracy
- [ ] Embedding dimension validation
- [ ] Metadata preservation in chunks
