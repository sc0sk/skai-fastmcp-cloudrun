# Feature Specification: Admin-Protected Markdown Ingestion with Vector Embeddings

**Feature Branch**: `012-admin-markdown-ingestion`
**Created**: 2025-10-24
**Status**: Draft
**Input**: User description: "Add secure admin-only markdown ingestion with metadata extraction, LangChain integration, and vector embeddings. The feature should parse markdown files, extract frontmatter metadata, populate database tables (speeches + langchain_pg_embedding), generate embeddings via Vertex AI, and expose admin-protected MCP tools with bearer token authentication."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bulk Import Parliamentary Speeches (Priority: P1)

An administrator needs to import a batch of parliamentary speech markdown files into the system to make them searchable. Each markdown file contains YAML frontmatter with metadata (speaker, party, chamber, date) and the speech text in markdown format. The administrator authenticates with their admin bearer token and uses a bulk ingestion tool to process all files in a directory.

**Why this priority**: This is the core value proposition - getting content into the system. Without this, no other features can function. It's the foundation that enables search, retrieval, and analysis.

**Independent Test**: Can be fully tested by authenticating with an admin token, providing a directory path with markdown files, and verifying that speeches appear in the database with correct metadata and are searchable.

**Acceptance Scenarios**:

1. **Given** an administrator has a directory with 10 markdown files with valid frontmatter, **When** they run the bulk ingestion tool with their admin token, **Then** all 10 speeches are imported with correct metadata, vector embeddings are generated, and they become searchable
2. **Given** an administrator provides an admin token, **When** they attempt to ingest files, **Then** the system validates the token has admin privileges before allowing ingestion
3. **Given** markdown files have YAML frontmatter with speaker, party, chamber, and date fields, **When** the ingestion process runs, **Then** this metadata is extracted and stored in the speeches table
4. **Given** speech text content in markdown format, **When** ingestion completes, **Then** the text is chunked, embedded using Vertex AI, and stored in the vector database for semantic search

---

### User Story 2 - Single File Import with Validation (Priority: P2)

An administrator wants to import a single new speech markdown file and receive immediate feedback about any validation errors or metadata issues. They provide the file path and receive detailed status reporting showing extraction, validation, embedding generation, and database storage progress.

**Why this priority**: Single file import with validation feedback is essential for quality control and troubleshooting. It provides immediate visibility into the ingestion process and helps administrators catch errors early.

**Independent Test**: Can be tested by providing a single markdown file with intentionally missing or malformed metadata, verifying that appropriate error messages are returned without crashing the system.

**Acceptance Scenarios**:

1. **Given** a markdown file with complete, valid frontmatter, **When** an administrator imports it using the single-file tool, **Then** the system reports successful extraction, validation, embedding generation, and database storage
2. **Given** a markdown file missing required metadata fields (e.g., no date), **When** an administrator attempts import, **Then** the system returns a clear error message identifying the missing fields without partially importing the data
3. **Given** a markdown file with an invalid date format, **When** import is attempted, **Then** the system rejects the file with a specific error about the date format issue
4. **Given** a duplicate speech ID already exists in the database, **When** an administrator tries to import the same file again, **Then** the system detects the duplicate and either skips or updates based on configuration

---

### User Story 3 - Monitor Ingestion Progress (Priority: P3)

An administrator running a bulk ingestion of 100+ files wants to monitor real-time progress, see how many files have been processed, identify any failures, and understand the overall status without waiting for completion.

**Why this priority**: Progress monitoring improves user experience for long-running operations but isn't essential for MVP functionality. The ingestion can work without real-time progress updates.

**Independent Test**: Can be tested by starting a bulk ingestion job and observing progress updates every N files or every N seconds, verifying that counts, success/failure stats, and estimated completion time are displayed.

**Acceptance Scenarios**:

1. **Given** a bulk ingestion of 50 files is in progress, **When** the administrator checks status, **Then** they see current progress (e.g., "25/50 complete"), success count, failure count, and processing rate
2. **Given** some files fail during bulk ingestion, **When** ingestion completes, **Then** the administrator receives a summary report listing all failed files with specific error messages
3. **Given** a large ingestion job is running, **When** the administrator requests current status, **Then** they see estimated time remaining based on current processing rate

---

### Edge Cases

- What happens when a markdown file has no frontmatter at all?
- What happens when frontmatter is malformed YAML (syntax errors)?
- How does the system handle extremely large markdown files (>10MB)?
- What happens if Vertex AI embedding service is temporarily unavailable during ingestion?
- How does the system handle markdown files with non-UTF-8 encoding?
- What happens if database connection is lost mid-ingestion during a bulk operation?
- How does the system handle duplicate speech IDs across different files?
- What happens when required metadata fields are present but have empty/null values?
- How does the system handle special characters or HTML in markdown content?
- What happens if the administrator's bearer token expires during a long-running bulk ingestion?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST authenticate all ingestion requests using bearer token validation with admin role verification
- **FR-002**: System MUST parse YAML frontmatter from markdown files to extract metadata fields (speech_id, speaker, party, chamber, date, title)
- **FR-003**: System MUST validate that all required metadata fields are present and in correct format before ingestion
- **FR-004**: System MUST chunk speech text content into semantically meaningful segments for vector embedding
- **FR-005**: System MUST generate vector embeddings for each text chunk using Vertex AI text-embedding-005 model
- **FR-006**: System MUST store speech metadata in the speeches table (or equivalent metadata store)
- **FR-007**: System MUST store vector embeddings in the langchain_pg_embedding table with proper associations to source speeches
- **FR-008**: System MUST provide single-file ingestion tool accepting file path as input parameter
- **FR-009**: System MUST provide bulk ingestion tool accepting directory path or file pattern as input parameter
- **FR-010**: System MUST reject ingestion requests from users without admin privileges with appropriate error message
- **FR-011**: System MUST handle ingestion failures gracefully without corrupting existing data or leaving partial records
- **FR-012**: System MUST return detailed status information including success/failure counts and specific error messages for failed files
- **FR-013**: System MUST detect duplicate speech IDs and handle them according to configurable policy (skip, update, or error)
- **FR-014**: System MUST validate markdown file format and encoding before attempting to parse content
- **FR-015**: System MUST support rollback or cleanup of partially ingested data if ingestion fails mid-process

### Key Entities

- **Speech Metadata**: Represents core information about a parliamentary speech including unique identifier, speaker name, political party affiliation, chamber (House of Representatives or Senate), speech date, title, and full text content
- **Vector Embedding Chunk**: Represents a semantically meaningful text segment from a speech along with its vector embedding (768-dimensional for text-embedding-005), chunk index, association to parent speech, and metadata for filtering
- **Ingestion Job**: Represents a single or bulk ingestion operation including status, file list, success/failure counts, error details, timestamp, and requesting administrator
- **Admin Token**: Represents authentication credential with elevated privileges required for ingestion operations, includes role claims and expiration

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Administrators can successfully ingest individual markdown files with complete metadata in under 5 seconds per file
- **SC-002**: Bulk ingestion processes at least 10 files per minute on average for files of standard size (5-10KB)
- **SC-003**: System correctly rejects 100% of ingestion attempts from non-admin users with appropriate error messages
- **SC-004**: System achieves 99% success rate for ingesting well-formed markdown files with valid metadata
- **SC-005**: All ingested speeches become searchable via existing search tools within 10 seconds of ingestion completion
- **SC-006**: System handles ingestion failures without data corruption - failed ingestions leave zero partial records in database
- **SC-007**: Administrators receive actionable error messages for 100% of validation failures (missing fields, format errors, duplicates)
- **SC-008**: Vector embeddings generated during ingestion produce search results with similar relevance scores to manually ingested content (within 5% similarity score variance)
- **SC-009**: System can recover from transient failures (network issues, service unavailability) and retry failed operations without administrator intervention in at least 80% of cases
- **SC-010**: Bulk ingestion of 100 files completes with less than 5% failure rate for valid input files

## Assumptions

- Markdown files follow standard YAML frontmatter format with `---` delimiters
- Required metadata fields are: speech_id, speaker, party, chamber, date, title (text content is implicit)
- Speech text content is in markdown format following standard conventions
- Vertex AI text-embedding-005 model is available and configured in the project
- Admin bearer tokens follow existing OAuth 2.1 implementation with role claims
- Database tables (speeches, langchain_pg_embedding) already exist with proper schema
- Standard chunk size is 500-1000 characters with semantic boundary detection (paragraph breaks)
- Date format in frontmatter is ISO 8601 (YYYY-MM-DD)
- Party values are restricted to known Australian political parties (Liberal, Labor, Greens, National, Independent)
- Chamber values are either "REPS" (House of Representatives) or "SENATE"
- File encoding is UTF-8 unless otherwise specified
- Maximum individual file size is 10MB (configurable)
- Duplicate detection is based on speech_id uniqueness

## Out of Scope

- Automatic crawling or fetching of markdown files from external sources
- Real-time file watching or automatic ingestion when files are added to a directory
- User interface or web dashboard for managing ingestions (CLI/API only for MVP)
- Conversion from other document formats (PDF, DOCX) to markdown
- OCR or text extraction from images
- Editing or updating existing speeches through the ingestion tool (separate update feature)
- Version control or history tracking for speech updates
- Scheduled or automated ingestion jobs
- Export functionality (ingestion only, not extraction)
- Custom embedding models or model selection (fixed to text-embedding-005)
- Fine-tuning or customization of embedding generation process
- Multi-tenancy or organization-level isolation (single deployment scope)

## Dependencies

- **Vertex AI Text Embedding API**: Required for generating vector embeddings from text chunks
- **Cloud SQL PostgreSQL**: Required for storing speech metadata and vector embeddings
- **Existing OAuth 2.1 Implementation**: Required for bearer token validation and admin role verification
- **LangChain PostgreSQL Integration**: Required for vector store operations and similarity search
- **Python-frontmatter Library**: Required for parsing YAML frontmatter from markdown files (or equivalent)
- **Existing MCP Server Framework**: Required for exposing ingestion tools as MCP operations
- **Existing Database Schema**: Requires speeches table and langchain_pg_embedding table to be initialized

## Security Considerations

- All ingestion tools MUST require valid admin bearer tokens - no unauthenticated or user-level access permitted
- Token validation MUST verify admin role claims before allowing any ingestion operations
- Ingestion operations MUST be logged with administrator identity, timestamp, file list, and outcomes for audit trail
- File path inputs MUST be validated to prevent directory traversal attacks (e.g., preventing access to `../../etc/passwd`)
- Markdown content MUST be sanitized if ever rendered as HTML to prevent XSS attacks (though search is text-only)
- Database operations MUST use parameterized queries to prevent SQL injection
- Bearer tokens MUST be transmitted over HTTPS only (TLS 1.3)
- Failed authentication attempts MUST be rate-limited to prevent brute force attacks
- Ingestion error messages MUST NOT leak sensitive system information (file paths, database details)
- Admin tokens MUST have reasonable expiration times and be revocable

## Performance Considerations

- Bulk ingestion of large file sets (100+ files) MUST not block other system operations
- Vector embedding generation SHOULD be batched when possible to optimize API usage
- Database writes SHOULD be batched or use transactions to reduce connection overhead
- Progress updates for bulk operations SHOULD not significantly slow down ingestion processing
- Failed file ingestion MUST NOT impact processing of other files in bulk operations
- Memory usage during ingestion MUST remain bounded (streaming file processing for large files)
- Concurrent ingestion requests SHOULD be queued or limited to prevent resource exhaustion
