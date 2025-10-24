#!/usr/bin/env python3
"""Populate hansard_speeches table with markdown files from sk-hansard-converter output.

Extracts YAML frontmatter metadata and stores:
- Simple fields in dedicated columns (speaker, party, chamber, date, etc.)
- Complex nested data in langchain_metadata JSONB (entities, themes, summary)
"""

import asyncio
import os
import sys
import yaml
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_google_cloud_sql_pg import PostgresVectorStore, PostgresEngine
from config import (
    VECTOR_TABLE_NAME,
    DEFAULT_GCP_PROJECT_ID,
    DEFAULT_GCP_REGION,
    CLOUDSQL_INSTANCE_NAME,
    DEFAULT_CLOUDSQL_DATABASE,
)

# Hansard data directory
HANSARD_DATA_DIR = Path("/home/user/sk-hansard-converter/output_md_enhanced/reps")


def extract_frontmatter_and_content(markdown_content: str) -> tuple[Dict[str, Any], str]:
    """Extract YAML frontmatter and content from markdown file."""
    # Match YAML frontmatter between --- delimiters
    frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n'
    match = re.search(frontmatter_pattern, markdown_content, re.DOTALL)

    if not match:
        return {}, markdown_content

    frontmatter_yaml = match.group(1)
    content = re.sub(frontmatter_pattern, '', markdown_content, count=1, flags=re.DOTALL)

    # Parse YAML
    metadata = yaml.safe_load(frontmatter_yaml) or {}

    return metadata, content.strip()


def prepare_metadata(frontmatter: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Split metadata into column values and JSONB data.

    Returns:
        tuple: (column_metadata, jsonb_metadata)
    """
    # Extract simple fields for dedicated columns
    column_metadata = {
        "speaker": frontmatter.get("speaker"),
        "party": frontmatter.get("party"),
        "chamber": frontmatter.get("chamber"),
        "date": frontmatter.get("date"),  # Will be converted to date object
        "speech_type": frontmatter.get("debate"),  # Using debate as speech_type
        "electorate": frontmatter.get("electorate"),
        "speaker_id": frontmatter.get("speaker_id"),
        "utterance_id": frontmatter.get("utterance_id"),
        "debate": frontmatter.get("debate"),
    }

    # Extract complex nested data for JSONB
    jsonb_metadata = {
        "summary": frontmatter.get("summary"),
        "entities": frontmatter.get("entities", {}),
        "themes": frontmatter.get("themes", []),
        "parliament": frontmatter.get("parliament"),
        "session": frontmatter.get("session"),
        "period": frontmatter.get("period"),
        "source_file": frontmatter.get("source_file"),
    }

    # Convert date string to date object
    if column_metadata["date"]:
        try:
            column_metadata["date"] = datetime.strptime(
                column_metadata["date"], "%Y-%m-%d"
            ).date()
        except (ValueError, TypeError):
            column_metadata["date"] = None

    return column_metadata, jsonb_metadata


def chunk_speech(content: str, column_metadata: Dict[str, Any],
                 jsonb_metadata: Dict[str, Any]) -> List[tuple[str, Dict[str, Any]]]:
    """
    Split speech content into chunks with metadata.

    Returns:
        List of (chunk_text, full_metadata) tuples
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,  # ~1500 characters per chunk
        chunk_overlap=300,  # 20% overlap for context
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = text_splitter.split_text(content)

    documents = []
    for i, chunk_text in enumerate(chunks):
        # Combine column metadata with JSONB metadata
        full_metadata = column_metadata.copy()

        # Add chunk-specific data to JSONB
        chunk_jsonb = jsonb_metadata.copy()
        chunk_jsonb["chunk_index"] = i
        chunk_jsonb["total_chunks"] = len(chunks)

        # Store JSONB data in langchain_metadata field
        full_metadata["langchain_metadata"] = chunk_jsonb

        documents.append((chunk_text, full_metadata))

    return documents


async def populate_database(documents: List[tuple[str, Dict[str, Any]]],
                           batch_size: int = 50):
    """
    Generate embeddings and insert documents into vector store.

    Args:
        documents: List of (text, metadata) tuples
        batch_size: Number of documents to process per batch
    """
    print(f"🔌 Connecting to Cloud SQL...")

    # Initialize Vertex AI embeddings
    embeddings = VertexAIEmbeddings(
        model_name="text-embedding-005",
        project=os.getenv("GCP_PROJECT_ID", DEFAULT_GCP_PROJECT_ID),
        location=os.getenv("GCP_REGION", DEFAULT_GCP_REGION),
    )

    # Connect to Cloud SQL
    engine = await PostgresEngine.afrom_instance(
        project_id=os.getenv("GCP_PROJECT_ID", DEFAULT_GCP_PROJECT_ID),
        region=os.getenv("GCP_REGION", DEFAULT_GCP_REGION),
        instance=os.getenv("CLOUDSQL_INSTANCE", CLOUDSQL_INSTANCE_NAME),
        database=os.getenv("CLOUDSQL_DATABASE", DEFAULT_CLOUDSQL_DATABASE),
        user=os.getenv("CLOUDSQL_USER"),
        password=os.getenv("CLOUDSQL_PASSWORD"),
    )

    print(f"📊 Initializing vector store...")

    # Initialize vector store
    vector_store = await PostgresVectorStore.create(
        engine=engine,
        embedding_service=embeddings,
        table_name=VECTOR_TABLE_NAME,
    )

    # Batch insert documents
    texts = [doc[0] for doc in documents]
    metadatas = [doc[1] for doc in documents]

    print(f"📝 Inserting {len(texts)} chunks in batches of {batch_size}...")

    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        batch_metadatas = metadatas[i:i+batch_size]

        print(f"   Batch {i//batch_size + 1}: Inserting {len(batch_texts)} chunks...")

        ids = await vector_store.aadd_texts(
            texts=batch_texts,
            metadatas=batch_metadatas,
        )

        print(f"   ✅ Inserted {len(ids)} chunks")

    print(f"✅ All chunks inserted successfully")
    await engine.close()


async def populate_hansard_database(max_files: int = None):
    """
    Complete workflow to populate Hansard speech database.

    Args:
        max_files: Maximum number of files to process (None for all)
    """
    # Load speech files
    markdown_files = sorted(HANSARD_DATA_DIR.glob("**/*.md"))

    if max_files:
        markdown_files = markdown_files[:max_files]

    print(f"📁 Found {len(markdown_files)} Hansard speech files")

    all_documents = []
    processed_files = 0
    skipped_files = 0

    # Process each speech file
    for file_path in markdown_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()

            # Extract metadata and content
            frontmatter, content = extract_frontmatter_and_content(markdown_content)

            if not content.strip():
                print(f"⚠️  Skipping {file_path.name}: Empty content")
                skipped_files += 1
                continue

            # Prepare metadata for columns and JSONB
            column_metadata, jsonb_metadata = prepare_metadata(frontmatter)

            # Chunk the speech
            chunks = chunk_speech(content, column_metadata, jsonb_metadata)
            all_documents.extend(chunks)

            processed_files += 1

            if processed_files % 10 == 0:
                print(f"   Processed {processed_files}/{len(markdown_files)} files...")

        except Exception as e:
            print(f"❌ Error processing {file_path.name}: {e}")
            skipped_files += 1
            continue

    print(f"\n📊 Processing summary:")
    print(f"   Files processed: {processed_files}")
    print(f"   Files skipped: {skipped_files}")
    print(f"   Total chunks generated: {len(all_documents)}")

    if all_documents:
        # Insert to database with embeddings
        await populate_database(all_documents)
    else:
        print("⚠️  No documents to insert")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Populate Hansard speech database")
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Maximum number of files to process (default: all)"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode: process only 5 files"
    )

    args = parser.parse_args()

    max_files = 5 if args.test else args.max_files

    if args.test:
        print("🧪 Running in TEST mode (5 files only)")

    asyncio.run(populate_hansard_database(max_files=max_files))
