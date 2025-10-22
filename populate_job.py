#!/usr/bin/env python3
"""Cloud Run Job to populate database with Hansard speeches."""

import asyncio
import os
from pathlib import Path
from langchain_google_cloud_sql_pg import PostgresEngine, PostgresVectorStore
from langchain_google_vertexai import VertexAIEmbeddings
import yaml


def parse_hansard_markdown(file_path: str) -> dict:
    """Parse Hansard markdown file and extract frontmatter + content."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

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
    """Populate database using environment variables from Cloud Run."""

    print("\n" + "="*80)
    print("POPULATING HANSARD DATABASE (Cloud Run Job)")
    print("="*80)

    # Get config from environment
    project_id = os.getenv("GCP_PROJECT_ID", "skai-fastmcp-cloudrun")
    region = os.getenv("GCP_REGION", "us-central1")
    instance = os.getenv("CLOUDSQL_INSTANCE", "hansard-db-v2")
    database = os.getenv("CLOUDSQL_DATABASE", "hansard")
    table_name = "langchain_vector_store"

    print(f"\n📦 Connection Config:")
    print(f"   Project: {project_id}")
    print(f"   Instance: {instance}")
    print(f"   Database: {database}")
    print(f"   Table: {table_name}")
    print(f"   Authentication: IAM (Cloud Run service account)")

    # Create engine with IAM auth
    print(f"\n🔌 Creating PostgresEngine...")
    engine = await PostgresEngine.afrom_instance(
        project_id=project_id,
        region=region,
        instance=instance,
        database=database
    )
    print(f"✅ Engine created")

    # Initialize table
    print(f"\n🔧 Initializing vector store table...")
    await engine.ainit_vectorstore_table(
        table_name=table_name,
        vector_size=768
    )
    print(f"✅ Table initialized")

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

    # Load Hansard files
    print(f"\n📄 Loading Hansard speeches...")
    hansard_dir = Path(__file__).parent / "data" / "sk-hansard"

    if not hansard_dir.exists():
        print(f"❌ Error: Directory not found: {hansard_dir}")
        return

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

    # Prepare data
    print(f"\n📝 Preparing speeches for ingestion...")
    texts = [speech['text'] for speech in speeches]
    metadatas = [
        {
            'speech_id': speech['frontmatter'].get('utterance_id', ''),
            'speaker': speech['frontmatter'].get('speaker', ''),
            'date': speech['frontmatter'].get('date', ''),
            'chamber': speech['frontmatter'].get('chamber', ''),
            'party': speech['frontmatter'].get('party', ''),
            'debate': speech['frontmatter'].get('debate', ''),
            'summary': speech['frontmatter'].get('summary', '')[:500],
        }
        for speech in speeches
    ]

    print(f"   Processing {len(texts)} speeches...")
    print(f"   Generating 768-dimensional embeddings via Vertex AI...")
    print(f"   (This may take several minutes...)")

    # Add to vector store
    ids = await store.aadd_texts(texts, metadatas=metadatas)

    print(f"\n✅ SUCCESS! Added {len(ids)} speeches with embeddings!")

    # Test search
    print(f"\n🔍 Testing similarity search...")
    query = "renewable energy and climate change"
    docs = await store.asimilarity_search(query, k=3)

    print(f"   Query: '{query}'")
    print(f"   Results: {len(docs)} documents")
    for i, doc in enumerate(docs, 1):
        print(f"\n   Result {i}:")
        print(f"      Speaker: {doc.metadata.get('speaker')}")
        print(f"      Date: {doc.metadata.get('date')}")
        print(f"      Preview: {doc.page_content[:150]}...")

    print(f"\n🎉 Population complete!")


if __name__ == "__main__":
    asyncio.run(main())
