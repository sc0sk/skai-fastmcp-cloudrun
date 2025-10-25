#!/usr/bin/env python3
"""Ingest Hansard markdown files using LangChain best practices.

Architecture:
- Uses LangChain's default schema with custom metadata columns
- Stores frequently-filtered fields (speaker, party, chamber, date, speech_type) as typed columns
- Stores complex nested metadata (entities, themes, policy_areas, etc.) in langchain_metadata JSONB
- Enables political/communications analysis queries with efficient SQL filtering
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_cloud_sql_pg import PostgresEngine, PostgresVectorStore
from langchain_google_vertexai import VertexAIEmbeddings
from parsers.hansard_parser import HansardMarkdownParser


def serialize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Convert metadata to JSON-serializable format.

    - Dates → ISO strings
    - Complex objects → JSON strings or preserve as dicts/lists
    - None values → exclude
    """
    result = {}
    for key, value in metadata.items():
        if value is None:
            continue
        elif hasattr(value, 'isoformat'):  # date/datetime objects
            result[key] = value.isoformat()
        elif isinstance(value, (dict, list)):  # Complex nested structures
            result[key] = value  # Keep as-is (will be stored in JSONB)
        else:
            result[key] = value
    return result


async def ingest_speeches(data_dir: str = "data/hansard_reps"):
    """Ingest all Hansard markdown files from directory."""
    print(f"🔍 Discovering markdown files in {data_dir}...")

    data_path = Path(data_dir)
    if not data_path.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    md_files = list(data_path.glob("*.md"))
    print(f"📁 Found {len(md_files)} files")

    if len(md_files) == 0:
        print("⚠️  No markdown files found!")
        return

    # Initialize components
    print("🔌 Connecting to Cloud SQL...")
    engine = await PostgresEngine.afrom_instance(
        project_id=os.getenv("GCP_PROJECT_ID", "skai-fastmcp-cloudrun"),
        region=os.getenv("GCP_REGION", "us-central1"),
        instance=os.getenv("CLOUDSQL_INSTANCE", "hansard-db-v2"),
        database=os.getenv("CLOUDSQL_DATABASE", "hansard"),
    )

    print("🤖 Initializing Vertex AI embeddings (text-embedding-005)...")
    embeddings = VertexAIEmbeddings(
        model_name="text-embedding-005",
        project=os.getenv("GCP_PROJECT_ID", "skai-fastmcp-cloudrun"),
    )

    print("📊 Initializing vector store...")
    vector_store = await PostgresVectorStore.create(
        engine=engine,
        table_name="hansard_speeches",
        embedding_service=embeddings,
    )

    print("✂️  Initializing text splitter (800 chars, 150 overlap)...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        length_function=len,
    )

    # Process each file
    success_count = 0
    error_count = 0
    total_chunks = 0

    for idx, md_file in enumerate(md_files, 1):
        try:
            print(f"\n[{idx}/{len(md_files)}] Processing {md_file.name}...")

            # Parse markdown file
            parser = HansardMarkdownParser(str(md_file))
            parsed_data = parser.parse()

            # Validate required fields
            required_fields = ['speaker', 'date', 'chamber', 'full_text']
            missing = [f for f in required_fields if f not in parsed_data or not parsed_data[f]]
            if missing:
                print(f"  ⚠️  Skipped: Missing required fields: {missing}")
                error_count += 1
                continue

            # Chunk the speech text
            full_text = parsed_data.pop('full_text')
            chunks = text_splitter.split_text(full_text)
            print(f"  ✂️  Split into {len(chunks)} chunks")

            # Prepare metadata for each chunk
            chunk_texts = []
            chunk_metadatas = []

            for chunk_idx, chunk_text in enumerate(chunks):
                # Build metadata dictionary
                metadata = serialize_metadata({
                    # Core fields (extracted to custom columns by LangChain)
                    'speaker': parsed_data.get('speaker'),
                    'party': parsed_data.get('party'),
                    'chamber': parsed_data.get('chamber'),
                    'date': parsed_data.get('date'),  # Already converted to date object
                    'speech_type': parsed_data.get('speech_type'),
                    'electorate': parsed_data.get('electorate'),
                    'speaker_id': parsed_data.get('speaker_id'),
                    'utterance_id': parsed_data.get('utterance_id'),
                    'debate': parsed_data.get('debate'),

                    # Chunk-specific
                    'chunk_index': chunk_idx,
                    'chunk_total': len(chunks),
                    'chunk_size': len(chunk_text),

                    # Complex nested metadata (stored in langchain_metadata JSONB)
                    'summary': parsed_data.get('summary'),
                    'entities': parsed_data.get('entities'),
                    'themes': parsed_data.get('themes'),
                    'subthemes': parsed_data.get('subthemes'),
                    'tags': parsed_data.get('tags'),
                    'rhetoric_intent': parsed_data.get('rhetoric_intent'),
                    'policy_areas': parsed_data.get('policy_areas'),
                    'political_stance': parsed_data.get('political_stance'),
                    'legislative_metadata': parsed_data.get('legislative_metadata'),
                    'content_analysis': parsed_data.get('content_analysis'),
                    'key_mentions': parsed_data.get('key_mentions'),
                    'local_references': parsed_data.get('local_references'),
                    'storytelling': parsed_data.get('storytelling'),
                    'evidence_base': parsed_data.get('evidence_base'),
                    'parliamentary_interaction': parsed_data.get('parliamentary_interaction'),
                    'communications_utility': parsed_data.get('communications_utility'),

                    # Source tracking
                    'source_file': parsed_data.get('source_file'),
                    'parliament': parsed_data.get('parliament'),
                    'session': parsed_data.get('session'),
                    'period': parsed_data.get('period'),
                })

                chunk_texts.append(chunk_text)
                chunk_metadatas.append(metadata)

            # Store chunks with embeddings
            print(f"  🔗 Storing {len(chunks)} chunks with embeddings...")
            await vector_store.aadd_texts(
                texts=chunk_texts,
                metadatas=chunk_metadatas,
            )

            success_count += 1
            total_chunks += len(chunks)
            print(f"  ✅ Success ({total_chunks} total chunks so far)")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            error_count += 1
            continue

    # Final summary
    print(f"\n{'='*60}")
    print(f"📊 Ingestion Complete")
    print(f"{'='*60}")
    print(f"✅ Successfully ingested: {success_count} speeches")
    print(f"❌ Errors: {error_count}")
    print(f"📦 Total chunks created: {total_chunks}")
    print(f"📈 Average chunks per speech: {total_chunks / success_count if success_count > 0 else 0:.1f}")

    await engine.close()


if __name__ == "__main__":
    asyncio.run(ingest_speeches())
