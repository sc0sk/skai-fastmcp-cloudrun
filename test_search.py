#!/usr/bin/env python3
"""Quick test script to verify search functionality."""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_search():
    """Test the search functionality directly."""
    from src.storage.vector_store import VectorStoreService
    from src.storage.embeddings import EmbeddingService

    # Initialize services
    embedding_service = EmbeddingService()
    vector_store = VectorStoreService(
        embedding_service=embedding_service,
    )

    # Test search
    print("Testing search for 'climate change'...")
    try:
        results = await vector_store.similarity_search(
            query="climate change",
            k=3,
        )
        print(f"\nFound {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"\n--- Result {i} ---")
            print(f"Chunk: {result['chunk_text'][:200]}...")
            print(f"Speaker: {result['metadata'].get('speaker')}")
            print(f"Date: {result['metadata'].get('date')}")
            print(f"Score: {result['score']:.4f}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await vector_store.close()

if __name__ == "__main__":
    asyncio.run(test_search())
