# Hansard Speech Data Population Guide

Based on LangChain + PGVector best practices (2025).

## Overview

This guide explains how to populate the `hansard_speeches` table with Australian parliamentary speech data, including metadata extraction, text chunking, embedding generation, and batch insertion.

## Best Practices Summary

### 1. **Use Latest LangChain Package**
- ✅ We use `langchain-google-cloud-sql-pg` (dedicated Google Cloud SQL package)
- ✅ Built on `psycopg3` for PostgreSQL connectivity
- ✅ Embedded Cloud SQL Python connector for IAM auth

### 2. **Metadata Management**
- ✅ Store frequently-filtered fields in dedicated columns (speaker, party, chamber, date)
- ✅ Use `langchain_metadata` JSONB for additional metadata
- ✅ Never use user-generated data for table/column names (security)

### 3. **Document Chunking**
- ✅ Use `RecursiveCharacterTextSplitter` from LangChain
- Recommended chunk size: 1000-2000 characters
- Overlap: 200-400 characters (20% of chunk size)

### 4. **Embedding Generation**
- ✅ Use Vertex AI `text-embedding-005` (768 dimensions)
- Batch processing for efficiency
- Rate limit awareness

### 5. **ID Management**
- Documents added by ID will overwrite existing ones
- Auto-generated UUIDs if IDs not provided
- Use content-based hashing for deduplication

### 6. **Indexing**
- ✅ HNSW index for vector similarity search
- ✅ B-tree indexes for metadata columns

## Data Population Workflow

### Step 1: Read Hansard Speech Files

Source data location: `/home/user/sk-hansard-converter/output_md_enhanced/reps/`

```python
import os
from pathlib import Path

HANSARD_DATA_DIR = Path("/home/user/sk-hansard-converter/output_md_enhanced/reps")

def load_hansard_speeches():
    """Load all Hansard markdown files."""
    markdown_files = list(HANSARD_DATA_DIR.glob("**/*.md"))
    print(f"Found {len(markdown_files)} Hansard speech files")
    return markdown_files
```

### Step 2: Extract Metadata from Markdown

Parse frontmatter and content:

```python
import re
from datetime import datetime

def extract_metadata(markdown_content: str) -> dict:
    """Extract metadata from Hansard markdown frontmatter."""
    # Parse YAML frontmatter (between --- delimiters)
    frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n'
    match = re.search(frontmatter_pattern, markdown_content, re.DOTALL)

    if not match:
        return {}

    frontmatter = match.group(1)
    metadata = {}

    # Extract key fields
    for line in frontmatter.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            metadata[key.strip()] = value.strip()

    # Map to database columns
    return {
        "speaker": metadata.get("speaker"),
        "party": metadata.get("party"),
        "chamber": metadata.get("chamber", "House of Representatives"),
        "date": datetime.strptime(metadata.get("date"), "%Y-%m-%d").date() if metadata.get("date") else None,
        "speech_type": metadata.get("speech_type"),
        "electorate": metadata.get("electorate"),
        "speaker_id": metadata.get("speaker_id"),
        "utterance_id": metadata.get("utterance_id"),
        "debate": metadata.get("debate"),
    }

def extract_content(markdown_content: str) -> str:
    """Extract speech content (remove frontmatter)."""
    frontmatter_pattern = r'^---\s*\n.*?\n---\s*\n'
    content = re.sub(frontmatter_pattern, '', markdown_content, flags=re.DOTALL)
    return content.strip()
```

### Step 3: Chunk Text Content

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

def chunk_speech(content: str, metadata: dict) -> list:
    """Split speech into chunks with metadata."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,  # ~1500 characters per chunk
        chunk_overlap=300,  # 20% overlap for context
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = text_splitter.split_text(content)

    # Attach metadata to each chunk
    documents = []
    for i, chunk in enumerate(chunks):
        doc_metadata = metadata.copy()
        doc_metadata["chunk_index"] = i
        doc_metadata["total_chunks"] = len(chunks)
        documents.append({
            "content": chunk,
            "metadata": doc_metadata,
        })

    return documents
```

### Step 4: Generate Embeddings & Insert to Database

```python
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_google_cloud_sql_pg import PostgresVectorStore, PostgresEngine
from config import VECTOR_TABLE_NAME, DEFAULT_GCP_PROJECT_ID, DEFAULT_GCP_REGION

async def populate_database(documents: list):
    """Generate embeddings and insert documents into vector store."""

    # Initialize Vertex AI embeddings
    embeddings = VertexAIEmbeddings(
        model_name="text-embedding-005",
        project=DEFAULT_GCP_PROJECT_ID,
        location=DEFAULT_GCP_REGION,
    )

    # Connect to Cloud SQL
    engine = await PostgresEngine.afrom_instance(
        project_id=DEFAULT_GCP_PROJECT_ID,
        region=DEFAULT_GCP_REGION,
        instance="hansard-db-v2",
        database="hansard",
    )

    # Initialize vector store
    vector_store = await PostgresVectorStore.create(
        engine=engine,
        embedding_service=embeddings,
        table_name=VECTOR_TABLE_NAME,
    )

    # Batch insert documents (LangChain handles embedding generation)
    texts = [doc["content"] for doc in documents]
    metadatas = [doc["metadata"] for doc in documents]

    print(f"Inserting {len(texts)} chunks into database...")
    ids = await vector_store.aadd_texts(
        texts=texts,
        metadatas=metadatas,
    )

    print(f"✅ Inserted {len(ids)} chunks successfully")
    await engine.close()
    return ids
```

### Step 5: Complete Population Script

```python
import asyncio
from pathlib import Path

async def populate_hansard_database():
    """Complete workflow to populate Hansard speech database."""

    # Load speech files
    markdown_files = load_hansard_speeches()

    all_documents = []

    # Process each speech file
    for file_path in markdown_files[:10]:  # Start with first 10 speeches
        with open(file_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()

        # Extract metadata and content
        metadata = extract_metadata(markdown_content)
        content = extract_content(markdown_content)

        # Chunk the speech
        chunks = chunk_speech(content, metadata)
        all_documents.extend(chunks)

    print(f"Processed {len(all_documents)} total chunks from {len(markdown_files[:10])} speeches")

    # Insert to database with embeddings
    await populate_database(all_documents)

if __name__ == "__main__":
    asyncio.run(populate_hansard_database())
```

## Performance Considerations

### Batch Size
- **Recommended**: 50-100 documents per batch
- Vertex AI embedding rate limits: 600 requests/min for text-embedding-005
- LangChain's `aadd_texts` handles batching automatically

### Rate Limiting
```python
import time

# For large datasets, add rate limiting
for i in range(0, len(documents), 100):
    batch = documents[i:i+100]
    await vector_store.aadd_texts(...)
    if i + 100 < len(documents):
        time.sleep(10)  # Wait 10s between batches
```

### Progress Tracking
```python
from tqdm import tqdm

for file_path in tqdm(markdown_files, desc="Processing speeches"):
    # ... process speech
```

## Deduplication Strategy

Use content-based hashing to prevent duplicate insertions:

```python
import hashlib

def generate_content_hash(content: str, metadata: dict) -> str:
    """Generate unique hash for document."""
    unique_str = f"{metadata.get('utterance_id')}:{content[:100]}"
    return hashlib.sha256(unique_str.encode()).hexdigest()

# Use as document ID
ids = await vector_store.aadd_texts(
    texts=texts,
    metadatas=metadatas,
    ids=[generate_content_hash(t, m) for t, m in zip(texts, metadatas)],
)
```

## Verification

After population, verify the data:

```sql
-- Check total chunks
SELECT COUNT(*) FROM hansard_speeches;

-- Check speeches by chamber
SELECT chamber, COUNT(*) FROM hansard_speeches GROUP BY chamber;

-- Check date range
SELECT MIN(date), MAX(date) FROM hansard_speeches;

-- Sample vector embeddings
SELECT langchain_id, speaker, LEFT(content, 50),
       array_length(embedding::vector, 1) as embedding_dim
FROM hansard_speeches LIMIT 5;
```

## Next Steps

1. ✅ Initialize schema (see [README_NEXT_STEPS.md](README_NEXT_STEPS.md))
2. Run population script with sample speeches (10-20 files)
3. Test search functionality
4. Scale up to full dataset (thousands of speeches)
5. Monitor performance and optimize batch sizes

## References

- [LangChain PGVector Documentation](https://python.langchain.com/docs/integrations/vectorstores/pgvector/)
- [Google Cloud SQL + LangChain Best Practices](https://cloud.google.com/blog/products/databases/using-pgvector-llms-and-langchain-with-google-cloud-databases)
- [Vertex AI Text Embeddings](https://cloud.google.com/vertex-ai/docs/generative-ai/embeddings/get-text-embeddings)
