# Australian Hansard RAG MVP

Retrieval-Augmented Generation (RAG) server for Australian parliamentary speeches using FastMCP on Google Cloud Run.

## Architecture

- **Framework**: FastMCP 2.14.0+ with Google ADK alignment
- **Embeddings**: Vertex AI `gemini-embedding-001` (768 dimensions)
- **Vector Database**: Cloud SQL PostgreSQL + pgvector v0.8.0
- **Text Processing**: LangChain RecursiveCharacterTextSplitter
- **Search**: Hybrid (vector similarity + full-text + metadata filters)

## Features

### MCP Tools

1. **ingest_markdown_speeches** - Load speeches from Markdown files with YAML frontmatter
2. **search_speeches** - Hybrid semantic search with metadata filtering
3. **get_speech** - Retrieve full speech by UUID

### MCP Resources

1. **hansard://speech/{speech_id}** - Individual speech resource
2. **hansard://speeches** - List all speeches with pagination
3. **hansard://dataset/stats** - Dataset statistics

## Quick Start

### Prerequisites

- Python 3.11+
- Google Cloud Project with billing enabled
- Google Cloud SDK (`gcloud`) installed
- `uv` package manager ([installation](https://github.com/astral-sh/uv))

### Installation

```bash
# Clone repository
git clone https://github.com/sc0sk/skai-fastmcp-cloudrun.git
cd skai-fastmcp-cloudrun
git checkout 001-hansard-rag-implementation

# Install dependencies
uv sync

# Copy environment template
cp .env.example .env

# Edit .env with your GCP project ID
nano .env
```

### Google Cloud Setup

```bash
# Login to Google Cloud
gcloud auth login
gcloud auth application-default login

# Set project
export GCP_PROJECT_ID="your-project-id"
gcloud config set project $GCP_PROJECT_ID

# Enable required APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable run.googleapis.com

# Create Cloud SQL instance (if not exists)
# See specs/001-hansard-rag-implementation/quickstart.md for detailed setup
```

### Running Locally

```bash
# Activate virtual environment
source .venv/bin/activate  # Or: .venv\Scripts\activate on Windows

# Run FastMCP server in dev mode
fastmcp dev src/server.py

# Server starts on stdio transport
# Open MCP Inspector at http://localhost:6274 (auto-opens in browser)
```

### Testing with MCP Inspector

```bash
# Ingest sample dataset (65 speeches)
{
  "name": "ingest_markdown_speeches",
  "arguments": {
    "directory_path": "/home/user/skai-fastmcp-cloudrun/data/sk-hansard"
  }
}

# Search speeches
{
  "name": "search_speeches",
  "arguments": {
    "query": "climate change policy",
    "use_hybrid": true,
    "speaker": "Simon Kennedy",
    "top_k": 5
  }
}

# Retrieve speech
{
  "name": "get_speech",
  "arguments": {
    "speech_id": "<uuid-from-search>",
    "include_context": true
  }
}
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_models.py -v

# View coverage report
open htmlcov/index.html
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type check
mypy src/
```

## Project Structure

```
src/
├── models/              # Pydantic models
│   ├── speech.py        # SpeechMetadata, SpeechDetail
│   └── results.py       # IngestionResult, SearchResult
├── storage/             # Database layer
│   ├── vector_store.py  # Cloud SQL pgvector integration
│   ├── metadata_store.py # Metadata storage
│   └── embeddings.py    # Vertex AI embeddings wrapper
├── tools/               # MCP tools
│   ├── ingest.py        # Ingestion tool
│   ├── search.py        # Search tool
│   └── retrieve.py      # Retrieval tool
├── processing/          # Text processing
│   ├── chunker.py       # Text chunking
│   └── validators.py    # Markdown parser
└── server.py            # FastMCP server entrypoint

tests/
├── unit/                # Unit tests
├── integration/         # Integration tests
└── fixtures/            # Test data
```

## Sample Dataset

**Location**: `/data/sk-hansard/`
**Format**: Markdown files with YAML frontmatter (Obsidian-compatible)
**Count**: 65 speeches from Australian House of Representatives
**Speaker**: Simon Kennedy MP (Cook, NSW, Liberal Party)
**Date Range**: 2024-05-28 to 2025-10-09

## Documentation

- [Implementation Plan](specs/001-hansard-rag-implementation/plan.md)
- [Quickstart Guide](specs/001-hansard-rag-implementation/quickstart.md)
- [Data Model](specs/001-hansard-rag-implementation/data-model.md)
- [API Contracts](specs/001-hansard-rag-implementation/contracts/)

## Deployment

See [quickstart.md](specs/001-hansard-rag-implementation/quickstart.md) for Cloud Run deployment instructions.

## License

MIT
