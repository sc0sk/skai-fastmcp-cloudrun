# Quickstart: Admin Markdown Ingestion

**Feature**: 012-admin-markdown-ingestion
**Audience**: Developers implementing the feature
**Purpose**: Rapid implementation guide with code examples

## Prerequisites

- Existing FastMCP server running
- OAuth 2.1 bearer token authentication configured
- Admin role configured in JWT claims
- Cloud SQL PostgreSQL with speeches and langchain_pg_embedding tables
- Vertex AI text-embedding-005 access

## Installation

### 1. Add Dependencies

```bash
# Add to pyproject.toml or requirements.txt
uv add python-frontmatter
# LangChain dependencies already exist
```

### 2. Environment Configuration

```bash
# Add to .env or Cloud Run environment variables
ADMIN_ROLE_CLAIM=role
ADMIN_ROLE_VALUE=admin
INGESTION_BASE_DIR=/data/hansard  # Allowed directory for file access
DUPLICATE_POLICY=skip  # skip, update, or error
CHUNK_SIZE=1000
CHUNK_OVERLAP=100
EMBEDDING_BATCH_SIZE=250
```

## Implementation Steps

### Step 1: Create Markdown Parser (10 min)

**File**: `src/tools/ingest/markdown_parser.py`

```python
"""Markdown file parsing with YAML frontmatter extraction."""
import frontmatter
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
from datetime import date
from typing import Optional
from models.enums import PartyEnum, ChamberEnum


class SpeechFrontmatter(BaseModel):
    """Parsed speech metadata from YAML frontmatter."""

    speech_id: str
    speaker: str = Field(min_length=1, max_length=200)
    party: PartyEnum
    chamber: ChamberEnum
    date: date
    title: str = Field(min_length=1, max_length=500)
    state: Optional[str] = Field(default=None, max_length=50)
    hansard_reference: Optional[str] = Field(default=None, max_length=100)

    @field_validator('date')
    @classmethod
    def date_not_future(cls, v: date) -> date:
        from datetime import date as date_type
        today = date_type.today()
        if v > today:
            raise ValueError(f"Speech date cannot be in future: {v}")
        return v


def parse_markdown_file(file_path: str | Path) -> tuple[SpeechFrontmatter, str]:
    """Parse markdown file with YAML frontmatter.

    Args:
        file_path: Path to markdown file

    Returns:
        (parsed_metadata, content_text)

    Raises:
        ValueError: If frontmatter is invalid or missing required fields
        FileNotFoundError: If file doesn't exist
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with path.open('r', encoding='utf-8') as f:
        try:
            post = frontmatter.load(f)
        except Exception as e:
            raise ValueError(f"Failed to parse YAML frontmatter: {e}")

    if not post.metadata:
        raise ValueError("Markdown file missing YAML frontmatter")

    # Validate and parse metadata
    try:
        metadata = SpeechFrontmatter(**post.metadata)
    except Exception as e:
        raise ValueError(f"Invalid frontmatter metadata: {e}")

    content = post.content.strip()
    if not content:
        raise ValueError("Speech text content is empty")

    return metadata, content
```

**Test**:
```python
# tests/unit/test_markdown_parser.py
def test_parse_valid_markdown():
    metadata, content = parse_markdown_file("test_data/valid_speech.md")
    assert metadata.speaker == "Simon Kennedy"
    assert metadata.party == PartyEnum.LIBERAL
    assert len(content) > 0

def test_parse_missing_frontmatter():
    with pytest.raises(ValueError, match="missing YAML frontmatter"):
        parse_markdown_file("test_data/no_frontmatter.md")
```

---

### Step 2: Add Path Validation (5 min)

**File**: `src/tools/ingest/path_validator.py`

```python
"""File path validation for security."""
import os
from pathlib import Path


def validate_file_path(
    file_path: str,
    base_dir: str | None = None
) -> Path:
    """Validate file path is within allowed directory.

    Args:
        file_path: Path to validate
        base_dir: Allowed base directory (from env if None)

    Returns:
        Resolved absolute path

    Raises:
        ValueError: If path is outside allowed directory
        FileNotFoundError: If file doesn't exist
    """
    if base_dir is None:
        base_dir = os.getenv("INGESTION_BASE_DIR", "/data/hansard")

    base = Path(base_dir).resolve()
    target = Path(file_path).resolve()

    # Check target is within base (prevents directory traversal)
    try:
        target.relative_to(base)
    except ValueError:
        raise ValueError(
            f"Path {file_path} is outside allowed directory {base_dir}. "
            f"This is a security restriction to prevent directory traversal."
        )

    if not target.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not target.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    return target
```

---

### Step 3: Implement Admin Authorization (10 min)

**File**: `src/tools/ingest/auth.py`

```python
"""Admin authorization for ingestion tools."""
from fastmcp import Context
import os


async def require_admin_role(ctx: Context) -> None:
    """Validate request has admin role.

    Args:
        ctx: FastMCP context with user claims

    Raises:
        PermissionError: If user lacks admin role
    """
    role_claim = os.getenv("ADMIN_ROLE_CLAIM", "role")
    required_role = os.getenv("ADMIN_ROLE_VALUE", "admin")

    if not ctx.user:
        raise PermissionError(
            "Authentication required. No user information in request context."
        )

    user_role = ctx.user.get(role_claim)

    if user_role != required_role:
        raise PermissionError(
            f"Admin privileges required for ingestion operations. "
            f"Your role: {user_role or 'none'}, required: {required_role}"
        )
```

---

### Step 4: Create Single File Ingestion Tool (20 min)

**File**: `src/tools/ingest_markdown_file.py`

```python
"""Single file markdown ingestion tool."""
from fastmcp import FastMCP, Context
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional
import os

from tools.ingest.markdown_parser import parse_markdown_file
from tools.ingest.path_validator import validate_file_path
from tools.ingest.auth import require_admin_role
from storage.vector_store import get_default_vector_store
from storage.metadata_store import get_default_metadata_store


class DuplicatePolicy(str, Enum):
    SKIP = "skip"
    UPDATE = "update"
    ERROR = "error"


class IngestFileInput(BaseModel):
    file_path: str = Field(description="Path to markdown file")
    duplicate_policy: DuplicatePolicy = Field(
        default=DuplicatePolicy.SKIP,
        description="How to handle duplicate speech_id"
    )
    validate_path: bool = Field(
        default=True,
        description="Validate path is within allowed directory"
    )


async def ingest_markdown_file(
    file_path: str,
    duplicate_policy: str = "skip",
    validate_path: bool = True,
    ctx: Optional[Context] = None
) -> dict:
    """Import parliamentary speech from markdown file.

    Admin-only. Parses YAML frontmatter, generates embeddings, stores in database.
    """
    # 1. Authorize
    if ctx:
        await require_admin_role(ctx)

    # 2. Validate path
    if validate_path:
        validated_path = validate_file_path(file_path)
    else:
        validated_path = Path(file_path)

    # 3. Parse markdown
    metadata, content = parse_markdown_file(validated_path)

    # 4. Get stores
    vector_store = await get_default_vector_store()
    metadata_store = await get_default_metadata_store()

    # 5. Ingest with transaction
    async with metadata_store._get_pool() as conn:
        async with conn.transaction():
            # Check for duplicate
            exists = await metadata_store.get_speech(metadata.speech_id)

            if exists:
                if duplicate_policy == "skip":
                    return {
                        "status": "skipped",
                        "speech_id": metadata.speech_id,
                        "message": "Speech already exists (skipped per policy)"
                    }
                elif duplicate_policy == "error":
                    raise ValueError(f"Speech ID '{metadata.speech_id}' already exists")
                # UPDATE policy continues...

            # Store metadata
            await metadata_store.store_speech(
                speech_id=metadata.speech_id,
                speaker=metadata.speaker,
                party=metadata.party.value,
                chamber=metadata.chamber.value,
                state=metadata.state,
                date=metadata.date,
                title=metadata.title,
                text=content,
                hansard_reference=metadata.hansard_reference
            )

            # Chunk and embed
            from langchain.text_splitter import RecursiveCharacterTextSplitter

            chunk_size = int(os.getenv("CHUNK_SIZE", "1000"))
            chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "100"))

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", ". ", " ", ""]
            )

            chunks = splitter.split_text(content)

            # Store chunks with embeddings
            chunk_metadata = [
                {
                    "speech_id": metadata.speech_id,
                    "speaker": metadata.speaker,
                    "party": metadata.party.value,
                    "chamber": metadata.chamber.value,
                    "date": str(metadata.date),
                    "chunk_index": i,
                    "chunk_total": len(chunks)
                }
                for i in range(len(chunks))
            ]

            await vector_store.add_chunks(
                texts=chunks,
                metadatas=chunk_metadata,
                speech_id=metadata.speech_id,
                ctx=ctx  # For progress reporting
            )

    return {
        "status": "success",
        "speech_id": metadata.speech_id,
        "speaker": metadata.speaker,
        "chunks_created": len(chunks),
        "message": "Speech ingested successfully"
    }


# Tool metadata for MCP registration
INGEST_FILE_METADATA = {
    "tags": ["admin-only", "write", "ingestion"],
    "requires_auth": True,
    "required_role": "admin"
}
```

---

### Step 5: Register Tools with FastMCP (5 min)

**File**: `src/server.py` (add to existing file)

```python
# Import new tools
from tools.ingest_markdown_file import (
    ingest_markdown_file,
    INGEST_FILE_METADATA
)

# Register tool
mcp.tool(
    ingest_markdown_file,
    name="ingest_markdown_file",
    description="""Import parliamentary speech from markdown file (admin-only)...""",
    metadata=INGEST_FILE_METADATA
)
```

---

### Step 6: Write Tests (15 min)

**File**: `tests/unit/test_ingest_markdown_file.py`

```python
import pytest
from tools.ingest_markdown_file import ingest_markdown_file
from fastmcp import Context


@pytest.fixture
def admin_context():
    """Mock admin context."""
    ctx = Context()
    ctx.user = {"role": "admin", "username": "admin@example.com"}
    return ctx


@pytest.fixture
def user_context():
    """Mock non-admin context."""
    ctx = Context()
    ctx.user = {"role": "user", "username": "user@example.com"}
    return ctx


async def test_ingest_valid_file(admin_context, tmp_path):
    """Test successful ingestion of valid markdown file."""
    # Create test file
    test_file = tmp_path / "test_speech.md"
    test_file.write_text("""---
speech_id: test_001
speaker: Test Speaker
party: Liberal
chamber: REPS
date: 2024-01-15
title: Test Speech
---

This is a test speech about climate policy.
""")

    result = await ingest_markdown_file(
        file_path=str(test_file),
        validate_path=False,  # Skip path validation for test
        ctx=admin_context
    )

    assert result["status"] == "success"
    assert result["speech_id"] == "test_001"
    assert result["chunks_created"] > 0


async def test_ingest_requires_admin(user_context, tmp_path):
    """Test that non-admin users are rejected."""
    test_file = tmp_path / "test.md"
    test_file.write_text("---\nspeech_id: test\n---\nContent")

    with pytest.raises(PermissionError, match="Admin privileges required"):
        await ingest_markdown_file(
            file_path=str(test_file),
            validate_path=False,
            ctx=user_context
        )


async def test_ingest_duplicate_skip(admin_context):
    """Test duplicate handling with skip policy."""
    # Ingest once
    result1 = await ingest_markdown_file("test_speech.md", ctx=admin_context)
    assert result1["status"] == "success"

    # Ingest again with skip policy
    result2 = await ingest_markdown_file(
        "test_speech.md",
        duplicate_policy="skip",
        ctx=admin_context
    )
    assert result2["status"] == "skipped"
```

---

## Testing Your Implementation

### Manual Testing

1. **Create test markdown file**:
```bash
cat > /data/hansard/test_speech.md <<EOF
---
speech_id: manual_test_001
speaker: Simon Kennedy
party: Liberal
chamber: REPS
date: 2024-10-24
title: Test Speech on Climate Policy
---

This is a test speech about climate change and renewable energy.
We must take action now to address this critical issue.
EOF
```

2. **Get admin bearer token**:
```bash
# Use existing OAuth flow or generate test token
export ADMIN_TOKEN="your_admin_bearer_token_here"
```

3. **Test via Claude CLI**:
```bash
claude -p --dangerously-skip-permissions \
  "Use ingest_markdown_file to import /data/hansard/test_speech.md"
```

4. **Verify ingestion**:
```bash
claude -p "Search for 'climate' and verify the test speech appears in results"
```

### Integration Testing

```bash
# Run full test suite
pytest tests/unit/test_ingest_markdown_file.py -v
pytest tests/integration/test_ingestion_e2e.py -v
```

## Deployment

### 1. Environment Variables

Add to Cloud Run deployment:
```bash
gcloud run services update hansard-mcp-server \
  --region us-central1 \
  --set-env-vars INGESTION_BASE_DIR=/data/hansard,DUPLICATE_POLICY=skip
```

### 2. Verify Admin Roles

Ensure JWT tokens include role claims:
```json
{
  "sub": "admin@example.com",
  "role": "admin",
  "iat": 1234567890
}
```

### 3. Test in Production

```bash
# Upload test file to Cloud Run persistent storage or mount
# Then test via MCP client
```

## Troubleshooting

### "Path outside allowed directory"
- Check `INGESTION_BASE_DIR` environment variable
- Ensure file path is within base directory
- Use absolute paths or verify relative path resolution

### "Admin privileges required"
- Verify bearer token includes `role: admin` claim
- Check `ADMIN_ROLE_CLAIM` and `ADMIN_ROLE_VALUE` env vars
- Confirm token hasn't expired

### "Speech ID already exists"
- Check duplicate_policy parameter (skip/update/error)
- Query database to verify if speech_id exists
- Use unique speech IDs for each file

### Embedding generation timeout
- Check Vertex AI quota and permissions
- Verify `GCP_PROJECT_ID` and `GCP_REGION` are set
- Reduce `CHUNK_SIZE` or `EMBEDDING_BATCH_SIZE` if needed

## Next Steps

1. Implement `ingest_markdown_bulk` for directory processing
2. Add `validate_markdown_file` for dry-run validation
3. Add comprehensive logging and audit trail
4. Implement retry logic for transient failures
5. Add metrics collection (ingestion rate, success/failure counts)

## Time Estimates

- Step 1 (Parser): 10 min
- Step 2 (Path validation): 5 min
- Step 3 (Auth): 10 min
- Step 4 (Single file tool): 20 min
- Step 5 (Registration): 5 min
- Step 6 (Tests): 15 min

**Total**: ~65 minutes for single file ingestion MVP
