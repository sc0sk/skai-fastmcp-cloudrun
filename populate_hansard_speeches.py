#!/usr/bin/env python3
"""Populate Cloud SQL database with actual Simon Kennedy Hansard speeches."""

import asyncio
import glob
from datetime import date
from pathlib import Path
from langchain_google_cloud_sql_pg import PostgresEngine, PostgresVectorStore
from langchain_google_vertexai import VertexAIEmbeddings
import yaml


def parse_hansard_markdown(file_path: str) -> dict:
    """Parse Hansard markdown file and extract frontmatter + content."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split frontmatter and content
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1])
            speech_text = parts[2].strip()

            return {
                'frontmatter': frontmatter,
                'text': speech_text,
                'file_path': file_path
            }

    raise ValueError(f"Invalid markdown format in {file_path}")


async def populate_database():
    """Initialize and populate database using LangChain."""

    print("\n" + "="*80)
    print("POPULATING CLOUD SQL WITH SIMON KENNEDY HANSARD SPEECHES")
    print("="*80)

    # Connection parameters
    project_id = "skai-fastmcp-cloudrun"
    region = "us-central1"
    instance = "hansard-db-v2"
    database = "hansard"
    table_name = "langchain_vector_store"

    print(f"\n📦 Creating PostgresEngine...")
    print(f"   Project: {project_id}")
    print(f"   Instance: {instance}")
    print(f"   Database: {database}")
    print(f"   Authentication: IAM")

    # Create engine (uses IAM authentication automatically)
    engine = await PostgresEngine.afrom_instance(
        project_id=project_id,
        region=region,
        instance=instance,
        database=database
    )
    print(f"✅ Engine created")

    # Initialize vector store table (auto-creates pgvector extension!)
    print(f"\n🔧 Creating vector store table...")
    print(f"   Table: {table_name}")
    print(f"   Vector size: 768 (text-embedding-005)")
    print(f"   Schema: langchain_id (UUID), content (TEXT), embedding (vector), langchain_metadata (JSON)")

    await engine.ainit_vectorstore_table(
        table_name=table_name,
        vector_size=768
    )
    print(f"✅ Table created with correct schema (pgvector extension auto-enabled!)")

    # Create embeddings service
    print(f"\n🤖 Creating Vertex AI embeddings service...")
    embedding = VertexAIEmbeddings(
        model_name="text-embedding-005",
        project=project_id
    )
    print(f"✅ Embeddings service created")

    # Create vector store
    print(f"\n📊 Creating PostgresVectorStore...")
    store = await PostgresVectorStore.create(
        engine=engine,
        table_name=table_name,
        embedding_service=embedding
    )
    print(f"✅ Vector store created")

    # Load all Hansard markdown files
    print(f"\n📄 Loading Hansard speeches from data/sk-hansard/...")
    hansard_dir = Path(__file__).parent / "data" / "sk-hansard"
    md_files = sorted(hansard_dir.glob("*.md"))

    print(f"   Found {len(md_files)} markdown files")

    speeches = []
    for md_file in md_files:
        try:
            parsed = parse_hansard_markdown(str(md_file))
            speeches.append(parsed)
        except Exception as e:
            print(f"   ⚠️  Skipped {md_file.name}: {e}")

    print(f"   Successfully parsed {len(speeches)} speeches")

    # Prepare texts and metadata for ingestion
    print(f"\n📝 Preparing speeches for vector store...")
    texts = [speech['text'] for speech in speeches]
    metadatas = [
        {
            'speech_id': speech['frontmatter'].get('utterance_id', ''),
            'speaker': speech['frontmatter'].get('speaker', ''),
            'speaker_id': speech['frontmatter'].get('speaker_id', ''),
            'date': speech['frontmatter'].get('date', ''),
            'chamber': speech['frontmatter'].get('chamber', ''),
            'electorate': speech['frontmatter'].get('electorate', ''),
            'party': speech['frontmatter'].get('party', ''),
            'debate': speech['frontmatter'].get('debate', ''),
            'themes': ','.join(speech['frontmatter'].get('themes', [])),
            'tags': ','.join(speech['frontmatter'].get('tags', [])),
            'summary': speech['frontmatter'].get('summary', '')[:500],  # Truncate to 500 chars
        }
        for speech in speeches
    ]

    print(f"   Processing {len(texts)} speeches...")
    print(f"   Generating 768-dimensional embeddings via Vertex AI...")
    print(f"   (This may take a few minutes...)")

    # Add speeches to vector store (generates embeddings automatically)
    ids = await store.aadd_texts(texts, metadatas=metadatas)

    print(f"✅ Added {len(ids)} speeches with embeddings!")

    # Test similarity search
    print(f"\n🔍 Testing similarity search...")
    query = "cost of living and inflation"
    docs = await store.asimilarity_search(query, k=3)

    print(f"   Query: '{query}'")
    print(f"   Results: {len(docs)} documents")
    for i, doc in enumerate(docs, 1):
        print(f"\n   Result {i}:")
        print(f"      Speaker: {doc.metadata.get('speaker')}")
        print(f"      Date: {doc.metadata.get('date')}")
        print(f"      Chamber: {doc.metadata.get('chamber')}")
        print(f"      Themes: {doc.metadata.get('themes')}")
        print(f"      Preview: {doc.page_content[:150]}...")

    print("\n" + "="*80)
    print("DATABASE POPULATION COMPLETE!")
    print("="*80)
    print(f"\n✅ Summary:")
    print(f"   - Speeches ingested: {len(speeches)}")
    print(f"   - Embeddings generated: {len(ids)}")
    print(f"   - Vector dimensionality: 768")
    print(f"   - Extension enabled: pgvector 0.8.0")
    print(f"   - Table created: {table_name}")
    print(f"\n🎯 Database ready for MCP search tool testing!")
    print(f"\n📊 Metadata fields stored:")
    print(f"   - speech_id, speaker, speaker_id, date")
    print(f"   - chamber, electorate, party, debate")
    print(f"   - themes, tags, summary")


if __name__ == "__main__":
    asyncio.run(populate_database())
