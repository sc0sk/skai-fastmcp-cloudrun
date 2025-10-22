#!/usr/bin/env python3
"""Populate Cloud SQL database with sample speeches using LangChain."""

import asyncio
from datetime import date
from src.storage.vector_store import VectorStoreService
from src.storage.embeddings import EmbeddingService
from src.processing.chunking import chunk_text


# Sample Australian Hansard speeches
SAMPLE_SPEECHES = [
    {
        "speech_id": "hansard_20240315_001",
        "title": "Climate Change and Renewable Energy Policy",
        "speaker": "Hon. Chris Bowen MP",
        "party": "Labor",
        "chamber": "House of Representatives",
        "state": "NSW",
        "date": date(2024, 3, 15),
        "hansard_reference": "HR_2024_03_15_001",
        "full_text": """Mr Speaker, I rise today to address the critical issue of climate change and our government's comprehensive renewable energy policy. Australia stands at a crossroads. We can either continue down the path of fossil fuel dependency, or we can embrace the clean energy future that will create jobs, reduce emissions, and secure our prosperity for generations to come.

Our government has committed to reducing emissions by 43% by 2030, with a target of net zero by 2050. This is not just an environmental imperative—it's an economic opportunity. The renewable energy sector is already creating thousands of jobs across regional Australia.

Solar and wind energy are now the cheapest forms of new electricity generation. Battery storage technology is advancing rapidly. The global energy transition is happening with or without us, and Australia must be part of it.

I commend the Minister for Climate Change and Energy for her tireless work on the Safeguard Mechanism reforms. These reforms will ensure our biggest emitters reduce their pollution while maintaining competitiveness and protecting jobs.

The renewable energy transformation will require significant investment in transmission infrastructure, skills training, and community engagement. Our government is committed to working with industry, unions, and communities to ensure this transition is orderly and fair.

The science is clear. The economics are compelling. The time for action is now. I urge all members of this House to support our renewable energy agenda for the benefit of all Australians.""",
        "word_count": 234
    },
    {
        "speech_id": "hansard_20240315_002",
        "title": "Housing Affordability Crisis",
        "speaker": "Hon. Julie Collins MP",
        "party": "Labor",
        "chamber": "House of Representatives",
        "state": "TAS",
        "date": date(2024, 3, 15),
        "hansard_reference": "HR_2024_03_15_002",
        "full_text": """Mr Speaker, housing affordability has become the defining challenge for a generation of Australians. Young people, families, and low-income earners are being locked out of the housing market at an alarming rate.

Our government's Housing Australia Future Fund represents a $10 billion investment to build 30,000 new social and affordable homes over five years. This is the largest investment in social housing in more than a decade.

But we need to do more. That's why we're also implementing the Help to Buy scheme, which will help up to 40,000 home buyers with smaller deposits purchase their first home. The Commonwealth will take an equity stake of up to 40% in new homes and 30% in existing homes.

We're also working with state and territory governments to improve planning processes and increase housing supply. Nimbyism and restrictive zoning have contributed to this crisis. We need bold reforms to unlock land for development.

The National Housing Accord brings together governments, investors, and the construction sector with a target of building one million new homes over five years. This requires unprecedented cooperation and coordination.

Every Australian deserves a safe, affordable place to call home. Our government is committed to turning this aspiration into reality through concrete policy action and sustained investment.""",
        "word_count": 203
    },
    {
        "speech_id": "hansard_20240315_003",
        "title": "Infrastructure Investment and Regional Development",
        "speaker": "Senator Bridget McKenzie",
        "party": "National",
        "chamber": "Senate",
        "state": "VIC",
        "date": date(2024, 3, 15),
        "hansard_reference": "SEN_2024_03_15_001",
        "full_text": """Mr President, infrastructure investment is the lifeblood of regional Australia. Roads, rail, telecommunications, and water infrastructure are not just economic enablers—they determine the quality of life for millions of regional Australians.

The Nationals have always championed infrastructure projects that connect our regions to markets, services, and opportunities. The Inland Rail project will revolutionize freight movement along the eastern seaboard, taking thousands of trucks off our highways and reducing transport costs for farmers and businesses.

Regional roads funding must be prioritized. Too many regional roads are in appalling condition, creating safety hazards and increasing transport costs. The government must commit to a long-term regional roads package that addresses the infrastructure deficit.

Telecommunications infrastructure is equally critical. The mobile black spot program has delivered coverage to previously unserviced areas, but much more needs to be done. Every regional community deserves reliable mobile and internet connectivity.

Water infrastructure investment is essential for agricultural productivity and drought resilience. Dams, pipelines, and irrigation modernization unlock economic potential and support thriving regional communities.

I call on the government to work constructively with the Coalition to deliver the infrastructure regional Australia desperately needs. Partisan politics should not stand in the way of nation-building infrastructure.""",
        "word_count": 194
    }
]


async def populate_database():
    """Populate database with sample speeches using LangChain."""
    
    print("\n" + "="*80)
    print("POPULATING CLOUD SQL DATABASE WITH SAMPLE SPEECHES")
    print("="*80)
    
    # Initialize services
    print("\n📦 Initializing services...")
    embedding_service = EmbeddingService(
        project_id="skai-fastmcp-cloudrun",
        location="us-central1",
        model_name="text-embedding-005",
        output_dimensionality=768
    )
    
    vector_store = VectorStoreService(
        project_id="skai-fastmcp-cloudrun",
        region="us-central1",
        instance="hansard-db-v2",
        database="hansard",
        embedding_service=embedding_service,
        table_name="speech_chunks"
    )
    
    print("✅ Services initialized")
    print(f"   - Embedding model: text-embedding-005 (768-dim)")
    print(f"   - Database: hansard-db-v2/hansard")
    print(f"   - Authentication: IAM (666924716777-compute@developer)")
    
    # Process each speech
    total_chunks = 0
    for i, speech in enumerate(SAMPLE_SPEECHES, 1):
        print(f"\n📄 Processing speech {i}/{len(SAMPLE_SPEECHES)}: {speech['title']}")
        print(f"   Speaker: {speech['speaker']} ({speech['party']})")
        print(f"   Date: {speech['date']}")
        print(f"   Word count: {speech['word_count']}")
        
        # Chunk the speech text
        chunks = chunk_text(
            text=speech['full_text'],
            chunk_size=500,
            chunk_overlap=50
        )
        print(f"   ✓ Created {len(chunks)} chunks")
        
        # Prepare metadata for each chunk
        metadatas = []
        for idx, chunk in enumerate(chunks):
            metadata = {
                "speech_id": speech['speech_id'],
                "chunk_index": idx,
                "chunk_size": len(chunk),
                "speaker": speech['speaker'],
                "party": speech['party'],
                "chamber": speech['chamber'],
                "state": speech['state'],
                "date": speech['date'],
                "hansard_reference": speech['hansard_reference']
            }
            metadatas.append(metadata)
        
        # Add chunks to vector store (generates embeddings automatically)
        print(f"   🔄 Generating embeddings and storing in database...")
        try:
            chunk_ids = await vector_store.add_chunks(
                texts=chunks,
                metadatas=metadatas,
                speech_id=speech['speech_id']
            )
            print(f"   ✅ Stored {len(chunk_ids)} chunks with embeddings")
            total_chunks += len(chunk_ids)
        except Exception as e:
            print(f"   ❌ Error storing chunks: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*80)
    print("DATABASE POPULATION COMPLETE")
    print("="*80)
    print(f"\n📊 Summary:")
    print(f"   - Total speeches ingested: {len(SAMPLE_SPEECHES)}")
    print(f"   - Total chunks created: {total_chunks}")
    print(f"   - Embeddings generated: {total_chunks} (768-dimensional vectors)")
    print(f"\n✅ Database is ready for semantic search!")
    print(f"\n📝 Tables created:")
    print(f"   - speech_chunks (with HNSW vector index)")
    print(f"   - LangChain metadata tables")
    print("\n🔍 You can now test the search tool via MCP Inspector")


if __name__ == "__main__":
    asyncio.run(populate_database())
