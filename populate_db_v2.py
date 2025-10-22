#!/usr/bin/env python3
"""Populate Cloud SQL database using LangChain's auto-initialization."""

import asyncio
from datetime import date
from langchain_google_cloud_sql_pg import PostgresEngine, PostgresVectorStore
from langchain_google_vertexai import VertexAIEmbeddings


# Sample speeches
SAMPLE_SPEECHES = [
    {
        "speech_id": "hansard_20240315_001",
        "speaker": "Hon. Chris Bowen MP",
        "party": "Labor",
        "chamber": "House of Representatives",
        "date": "2024-03-15",
        "text": "Mr Speaker, I rise today to address climate change and renewable energy policy. Australia stands at a crossroads between fossil fuel dependency and clean energy future. Our government has committed to reducing emissions by 43% by 2030, with net zero by 2050. Solar and wind energy are now the cheapest forms of new electricity generation. The renewable energy transformation will create thousands of jobs across regional Australia."
    },
    {
        "speech_id": "hansard_20240315_002",
        "speaker": "Hon. Julie Collins MP",
        "party": "Labor",
        "chamber": "House of Representatives",
        "date": "2024-03-15",
        "text": "Mr Speaker, housing affordability has become the defining challenge for a generation of Australians. Our Housing Australia Future Fund represents a $10 billion investment to build 30,000 new social and affordable homes. The Help to Buy scheme will help up to 40,000 home buyers purchase their first home. Every Australian deserves a safe, affordable place to call home."
    },
    {
        "speech_id": "hansard_20240315_003",
        "speaker": "Senator Bridget McKenzie",
        "party": "National",
        "chamber": "Senate",
        "date": "2024-03-15",
        "text": "Mr President, infrastructure investment is the lifeblood of regional Australia. The Inland Rail project will revolutionize freight movement along the eastern seaboard. Regional roads funding must be prioritized. Telecommunications infrastructure is equally critical with mobile black spot program expansion needed. Water infrastructure investment is essential for agricultural productivity."
    }
]


async def populate_database():
    """Initialize and populate database using LangChain."""
    
    print("\n" + "="*80)
    print("INITIALIZING AND POPULATING CLOUD SQL DATABASE")
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
    print(f"\n🔧 Initializing vector store table...")
    print(f"   Table: {table_name}")
    print(f"   Vector size: 768 (text-embedding-005)")
    
    await engine.ainit_vectorstore_table(
        table_name=table_name,
        vector_size=768
    )
    print(f"✅ Table initialized (pgvector extension auto-enabled!)")
    
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
    
    # Add speeches with metadata
    print(f"\n📝 Adding speeches to vector store...")
    texts = [speech["text"] for speech in SAMPLE_SPEECHES]
    metadatas = [
        {
            "speech_id": s["speech_id"],
            "speaker": s["speaker"],
            "party": s["party"],
            "chamber": s["chamber"],
            "date": s["date"]
        }
        for s in SAMPLE_SPEECHES
    ]
    
    print(f"   Processing {len(texts)} speeches...")
    print(f"   Generating 768-dimensional embeddings via Vertex AI...")
    
    ids = await store.aadd_texts(texts, metadatas=metadatas)
    
    print(f"✅ Added {len(ids)} speeches with embeddings!")
    
    # Test similarity search
    print(f"\n🔍 Testing similarity search...")
    query = "climate change and renewable energy"
    docs = await store.asimilarity_search(query, k=2)
    
    print(f"   Query: '{query}'")
    print(f"   Results: {len(docs)} documents")
    for i, doc in enumerate(docs, 1):
        print(f"\n   Result {i}:")
        print(f"      Speaker: {doc.metadata.get('speaker')}")
        print(f"      Party: {doc.metadata.get('party')}")
        print(f"      Preview: {doc.page_content[:100]}...")
    
    print("\n" + "="*80)
    print("DATABASE POPULATION COMPLETE!")
    print("="*80)
    print(f"\n✅ Summary:")
    print(f"   - Speeches ingested: {len(SAMPLE_SPEECHES)}")
    print(f"   - Embeddings generated: {len(ids)}")
    print(f"   - Vector dimensionality: 768")
    print(f"   - Extension enabled: pgvector 0.8.0")
    print(f"   - Table created: {table_name}")
    print(f"\n🎯 Database ready for MCP search tool testing!")


if __name__ == "__main__":
    asyncio.run(populate_database())
