# Feature Specification: Real Hansard Data Ingestion

**Feature Branch**: `002-real-hansard-ingestion`
**Created**: 2025-10-23
**Status**: Draft
**Input**: User description: "Ingest real Australian Hansard speeches from markdown files into the database with proper parsing, chunking, and vector embedding generation"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Parse and Ingest Markdown Files (Priority: P1)

The system administrator needs to import 64 real Australian Hansard parliamentary speeches from pre-processed markdown files located in `data/hansard_reps/`, enabling the MCP server to answer questions about actual parliamentary proceedings.

**Why this priority**: This is the foundation - without real data, the RAG system provides no meaningful value. The 64 speeches represent real parliamentary proceedings that users need to search.

**Independent Test**: Can be fully tested by running the ingestion script against the `data/hansard_reps/` directory, verifying all 64 speeches appear in the database with correct metadata (speaker, party, electorate, date, chamber), and confirming vector embeddings exist for semantic search.

**Acceptance Scenarios**:

1. **Given** 64 markdown files exist in `data/hansard_reps/`, **When** the ingestion script runs, **Then** all files are discovered and queued for processing
2. **Given** a markdown file with YAML frontmatter (speaker, date, chamber, electorate, party, etc.), **When** parsed, **Then** all metadata fields are correctly extracted
3. **Given** parsed speech data with date format 'YYYY-MM-DD', **When** stored, **Then** date is converted to ISO format and stored correctly
4. **Given** speech text after the second `---` marker, **When** extracted, **Then** full speech content is captured without metadata
5. **Given** a speech exceeds 800 characters, **When** chunked, **Then** text splits at ~800 char boundaries with 150 char overlap
6. **Given** text chunks with metadata, **When** embeddings generated, **Then** each chunk has 768-dim vector suitable for search
7. **Given** all chunks with embeddings, **When** stored, **Then** chunks link to parent speech via speech_id

---

### User Story 2 - Handle Date Serialization for JSON Metadata (Priority: P2)

When storing chunk metadata that includes Python date objects, the system must convert dates to ISO string format before passing to LangChain's vector store to avoid JSON serialization errors.

**Why this priority**: Prevents runtime errors during ingestion. The previous attempt failed with "Object of type date is not JSON serializable" - this must be fixed before any ingestion can succeed.

**Independent Test**: Can be tested by ingesting a single speech with a date field, verifying the chunk metadata contains date as string ("2024-05-28") not date object, and confirming successful storage without serialization errors.

**Acceptance Scenarios**:

1. **Given** chunk metadata includes a date field, **When** prepared for vector store, **Then** date is converted to ISO string format (YYYY-MM-DD)
2. **Given** date-string metadata, **When** passed to LangChain aadd_texts, **Then** JSON serialization succeeds without errors
3. **Given** stored chunks, **When** retrieved, **Then** date metadata is available as string for filtering/display

---

### User Story 3 - Progress Tracking and Error Reporting (Priority: P3)

For the 64-file ingestion, the administrator needs visibility into progress (files processed, speeches ingested, chunks created) and any errors encountered to verify successful completion.

**Why this priority**: Improves operational visibility but not critical for core functionality. Helps with debugging and confidence during ingestion.

**Independent Test**: Can be tested by ingesting all 64 files and verifying console output shows progress updates, final summary (64 speeches, ~X chunks created), and error log if any files fail.

**Acceptance Scenarios**:

1. **Given** ingestion begins with 64 files, **When** processing, **Then** progress indicator shows current file number and estimated completion
2. **Given** ingestion completes successfully, **When** final report generated, **Then** shows 64 speeches ingested, total chunks created, and zero errors
3. **Given** errors occur (if any), **When** logged, **Then** error messages include file path and specific error reason

---

### Edge Cases

- What happens if a markdown file has missing required metadata fields (speaker, date, chamber)?
- How does the system handle markdown files with non-UTF-8 encoding?
- What if speech text is empty (only frontmatter, no content after `---`)?
- How are extremely long speeches (>100,000 characters) handled?
- What happens if the database connection is lost mid-ingestion?
- How does the system handle malformed YAML frontmatter?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST read all .md files from `data/hansard_reps/` directory
- **FR-002**: System MUST parse YAML frontmatter to extract ALL metadata fields including: basic metadata (speaker, date, chamber, party, electorate), analytical metadata (summary, entities, themes, tags, speech_type, rhetoric_intent, policy_areas, political_stance), legislative context (bill_reference, vote_position), content analysis (word_count, interruptions, statistical_claims), and communications utility (quotable_phrases, soundbite_potential, controversy_level)
- **FR-003**: System MUST extract speech text content after the second `---` marker (end of YAML frontmatter)
- **FR-004**: System MUST validate required fields (speaker, date, chamber, speech text) exist before ingestion
- **FR-005**: System MUST parse speaker field format "LastName, FirstName MP" and extract full name
- **FR-006**: System MUST use LangChain's PostgresEngine with custom metadata columns for frequently-filtered fields (speaker, party, chamber, date, speech_type) and JSONB column for complex nested metadata
- **FR-007**: System MUST chunk speech text into ~800 character segments with 150 character overlap
- **FR-008**: System MUST generate 768-dimensional vector embeddings using Vertex AI for each chunk
- **FR-009**: System MUST store chunks with embeddings and ALL metadata (flattened where appropriate) to enable political/communications analysis queries
- **FR-010**: System MUST serialize complex metadata fields (entities, themes, policy_areas, political_stance, key_mentions, communications_utility) as JSON for storage in langchain_metadata column
- **FR-011**: System MUST detect duplicate speeches based on content hash and skip re-ingestion
- **FR-012**: System MUST log errors for files that fail parsing without halting entire batch
- **FR-013**: System MUST provide progress reporting (files processed, speeches ingested, chunks created)
- **FR-014**: System MUST enable filtering by political stance, policy areas, speech type, themes, and communications utility metrics

### Key Entities

- **Hansard Markdown File**: Source file with YAML frontmatter (lines 1-185 in sample) containing metadata, followed by speech text. Filename pattern: `{speaker_id}-{date}-{utterance_id}.md`
- **YAML Frontmatter**: Metadata block containing speaker, speaker_id, date, debate, chamber, electorate, party, parliament, session, period, utterance_id, source_file, summary, entities, topics, speech_type, rhetoric_intent, policy_areas
- **Speech Record**: Database entry with core fields (speech_id, speaker, party, chamber, electorate, state, date, full_text) plus generated fields (content_hash, word_count, created_at)
- **Text Chunk**: Speech segment (~800 chars) with metadata (speech_id, chunk_index, speaker, date) and 768-dim embedding vector

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System successfully ingests all 64 markdown files from `data/hansard_reps/` with zero data loss
- **SC-002**: Ingestion completes within 10 minutes for 64 speeches (average <10 seconds per speech including embedding generation)
- **SC-003**: Zero JSON serialization errors during chunk metadata storage
- **SC-004**: Database contains exactly 64 speech records after ingestion
- **SC-005**: All speeches have associated chunks (minimum 1 chunk per speech, average 2-3 chunks per speech)
- **SC-006**: Vector embeddings enable semantic search queries to return relevant speeches with >80% accuracy for test questions about known speech content

## Dependencies *(mandatory)*

- Markdown files copied to `data/hansard_reps/` directory (64 files already copied)
- Existing database schema (speeches and speech_chunks tables) compatible with extracted metadata
- Vertex AI embeddings service accessible and configured (text-embedding-005, 768 dimensions)
- Cloud SQL database with IAM authentication configured
- LangChain PostgresVectorStore with proper JSON serialization for date fields

## Assumptions *(mandatory)*

- All 64 markdown files follow consistent format (YAML frontmatter ending at line ~185, speech text after)
- YAML frontmatter uses standard keys: speaker, date, chamber, electorate, party
- File encoding is UTF-8
- Date format in frontmatter is YYYY-MM-DD (ISO 8601)
- The `data/hansard_reps/` directory is accessible from ingestion script execution environment
- Ingestion is a one-time batch operation (not incremental/real-time)
- Existing chunking parameters (800 chars, 150 overlap) are appropriate for parliamentary speeches
- The fix for date serialization (converting date objects to ISO strings) will be applied before running ingestion

## Constraints *(mandatory)*

- Must not modify or delete source markdown files during ingestion
- Must use existing database schema without migrations
- Must use existing Vertex AI embedding service (text-embedding-005, 768 dimensions)
- Must preserve any existing sample data in database
- Must complete ingestion of 64 speeches within reasonable timeframe (<15 minutes)
- Error handling must not expose sensitive information in logs
- Must work within Cloud Run job execution time limits if deployed as a job

## Out of Scope

- Parsing or converting Hansard data from other formats (PDF, XML, HTML)
- Data quality improvements to source markdown files
- Custom markdown parsing for non-standard formats beyond YAML frontmatter
- User interface for managing or triggering ingestion
- Automated scheduling or monitoring of ingestion jobs
- Incremental updates as new Hansard data becomes available
- Data export or backup functionality
- Performance optimization beyond the specified success criteria
- Support for Senate speeches or other chambers (only House of Reps in current dataset)
- Extraction or storage of extended metadata fields (entities, summary, topics) beyond core fields needed for search
