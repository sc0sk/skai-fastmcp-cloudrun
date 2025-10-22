#!/usr/bin/env python3
"""Drop the table, recreate it, and repopulate with Hansard speeches."""

import asyncio
import glob
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


async def main():
    """Drop table, recreate it, and populate database."""
    print("\n" + "="*80)
    print("RESET AND REPOPULATE HANSARD DATABASE")
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

    # Create engine
    engine = await PostgresEngine.afrom_instance(
        project_id=project_id,
        region=region,
        instance=instance,
        database=database
    )
    print(f"✅ Engine created")

    # Drop existing table
    print(f"\n⚠️  Dropping table: {table_name}")
    try:
        # Use SQLAlchemy text construct
        from sqlalchemy import text
        async with engine._pool.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
        print(f"✅ Table dropped")
    except Exception as e:
        print(f"⚠️  Error dropping table (may not exist): {e}")

    # Create table with correct schema
    print(f"\n🔧 Creating table with correct schema...")
    print(f"   Table: {table_name}")
    print(f"   Vector size: 768 (text-embedding-005)")

    await engine.ainit_vectorstore_table(
        table_name=table_name,
        vector_size=768
    )
    print(f"✅ Table created with correct schema!")

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

    # Load Hansard speeches
    print(f"\n📚 Loading Hansard speeches...")
    data_dir = Path("data/sk-hansard")
    markdown_files = glob.glob(str(data_dir / "*.md"))

    print(f"   Found {len(markdown_files)} markdown files")

    speeches = []
    for file_path in markdown_files:
        try:
            speech = parse_hansard_markdown(file_path)
            speeches.append(speech)
        except Exception as e:
            print(f"   ⚠️  Skipping {Path(file_path).name}: {e}")

    print(f"   Loaded {len(speeches)} valid speeches")

    # Prepare texts and metadata
    print(f"\n🔄 Preparing data for ingestion...")
    texts = [speech['text'] for speech in speeches]
    metadatas = [
        {
            'speech_id': speech['frontmatter'].get('speech_id', ''),
            'speaker': speech['frontmatter'].get('speaker', ''),
            'speaker_id': speech['frontmatter'].get('speaker_id', ''),
            'date': speech['frontmatter'].get('date', ''),
            'chamber': speech['frontmatter'].get('chamber', ''),
            'electorate': speech['frontmatter'].get('electorate', ''),
            'party': speech['frontmatter'].get('party', ''),
            'debate': speech['frontmatter'].get('debate', ''),
            'themes': ','.join(speech['frontmatter'].get('themes', [])),
            'tags': ','.join(speech['frontmatter'].get('tags', [])),
            'summary': speech['frontmatter'].get('summary', '')[:500],
        }
        for speech in speeches
    ]

    print(f"   Processing {len(texts)} speeches...")
    print(f"   Generating 768-dimensional embeddings via Vertex AI...")
    print(f"   (This may take a few minutes...)")

    # Add speeches to vector store
    ids = await store.aadd_texts(texts, metadatas=metadatas)

    print(f"\n✅ SUCCESS! Added {len(ids)} speeches with embeddings!")

    # Test similarity search
    print(f"\n🔍 Testing similarity search...")
    query = "cost of living and inflation"
    docs = await store.asimilarity_search(query, k=3)

    print(f"   Query: '{query}'")
    print(f"   Results: {len(docs)} documents\n")

    for i, doc in enumerate(docs, 1):
        metadata = doc.metadata
        print(f"   {i}. Speaker: {metadata.get('speaker', 'Unknown')}")
        print(f"      Date: {metadata.get('date', 'Unknown')}")
        print(f"      Excerpt: {doc.page_content[:100]}...\n")

    print(f"🎉 Database reset and repopulated successfully!")
    await engine.close()


if __name__ == "__main__":
    asyncio.run(main())
