#!/usr/bin/env python3
"""Ingest Hansard markdown files with YAML frontmatter → JSONB metadata.

Simple, clean approach:
1. Parse YAML frontmatter → Python dict
2. Convert to JSON-serializable format → JSONB
3. Use LangChain PostgresVectorStore (default schema: id, content, embedding, langchain_metadata)
4. All 20+ rich metadata fields stored in langchain_metadata JSONB column
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_cloud_sql_pg import PostgresEngine, PostgresVectorStore
from langchain_google_vertexai import VertexAIEmbeddings
from parsers.hansard_parser import HansardMarkdownParser


def to_json_serializable(obj: Any) -> Any:
    """Recursively convert to JSON-serializable types."""
    if hasattr(obj, 'isoformat'):  # date/datetime
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_json_serializable(item) for item in obj]
    elif obj is None:
        return None
    else:
        return obj


async def main():
    """Ingest all Hansard markdown files."""
    print("="* 80)
    print("Hansard JSONB Ingestion")
    print("=" * 80)

    # 1. Find files
    data_dir = Path("data/hansard_reps")
    print(f"\n📁 Scanning {data_dir}...")

    if not data_dir.exists():
        print(f"   ❌ Directory not found: {data_dir}")
        sys.exit(1)

    md_files = list(data_dir.glob("*.md"))
    print(f"   Found {len(md_files)} files")

    if not md_files:
        print("   ⚠️  No files to process")
        return

    # 2. Connect to database
    print(f"\n🔌 Connecting to Cloud SQL...")
    engine = await PostgresEngine.afrom_instance(
        project_id=os.getenv("GCP_PROJECT_ID", "skai-fastmcp-cloudrun"),
        region=os.getenv("GCP_REGION", "us-central1"),
        instance=os.getenv("CLOUDSQL_INSTANCE", "hansard-db-v2"),
        database=os.getenv("CLOUDSQL_DATABASE", "hansard"),
    )

    # 3. Initialize embeddings
    print(f"\n🤖 Initializing Vertex AI embeddings...")
    embeddings = VertexAIEmbeddings(
        model_name="text-embedding-005",
        project=os.getenv("GCP_PROJECT_ID", "skai-fastmcp-cloudrun"),
    )

    # 4. Create vector store (uses existing table or creates new one)
    print(f"\n📊 Initializing vector store...")
    vector_store = await PostgresVectorStore.create(
        engine=engine,
        table_name="hansard_speeches",
        embedding_service=embeddings,
    )
    print(f"   ✅ Vector store ready: hansard_speeches")
    print(f"   Schema: langchain_id, content, embedding, langchain_metadata")

    # 5. Initialize text splitter
    print(f"✂️  Text splitter: 800 chars, 150 overlap")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        length_function=len,
    )

    # 6. Process files
    print(f"\n{'=' * 80}")
    print("Processing Files")
    print("=" * 80)

    success = 0
    errors = 0
    total_chunks = 0

    for idx, md_file in enumerate(md_files, 1):
        try:
            print(f"\n[{idx}/{len(md_files)}] {md_file.name}")

            # Parse markdown + YAML frontmatter
            parser = HansardMarkdownParser(str(md_file))
            data = parser.parse()

            # Validate required fields
            required = ['speaker', 'date', 'chamber', 'full_text']
            missing = [f for f in required if not data.get(f)]
            if missing:
                print(f"   ⚠️  Skipped: Missing {missing}")
                errors += 1
                continue

            # Extract speech text
            speech_text = data.pop('full_text')

            # Chunk text
            chunks = splitter.split_text(speech_text)
            print(f"   ✂️  {len(chunks)} chunks")

            # Prepare texts and metadata for LangChain
            texts = []
            metadatas = []

            for chunk_idx, chunk_text in enumerate(chunks):
                # All frontmatter → JSONB metadata
                metadata = to_json_serializable({
                    **data,  # ALL frontmatter fields (speaker, party, entities, themes, etc.)
                    'chunk_index': chunk_idx,
                    'chunk_total': len(chunks),
                    'filename': md_file.name,
                })

                texts.append(chunk_text)
                metadatas.append(metadata)

            # Store with embeddings
            print(f"   💾 Storing...")
            await vector_store.aadd_texts(texts=texts, metadatas=metadatas)

            success += 1
            total_chunks += len(chunks)
            print(f"   ✅ Done ({total_chunks} total chunks)")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            errors += 1

    # 7. Summary
    print(f"\n{'=' * 80}")
    print("Summary")
    print("=" * 80)
    print(f"✅ Speeches: {success}")
    print(f"❌ Errors: {errors}")
    print(f"📦 Chunks: {total_chunks}")
    print(f"📊 Avg chunks/speech: {total_chunks / success if success else 0:.1f}")

    # Close connection
    await engine.close()
    print(f"\n🔌 Connection closed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
