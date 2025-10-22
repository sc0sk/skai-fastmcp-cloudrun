#!/usr/bin/env python3
"""Create chunks and embeddings for existing speeches that don't have chunks yet."""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from storage.metadata_store import get_default_metadata_store
from storage.vector_store import get_default_vector_store
from langchain.text_splitter import RecursiveCharacterTextSplitter


async def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 150):
    """Split text into chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    return splitter.split_text(text)


async def main():
    """Chunk all speeches that don't have chunks yet."""
    print("=" * 80)
    print("Chunk Existing Speeches")
    print("=" * 80)
    print()

    # Initialize stores
    print("🔄 Initializing storage services...")
    metadata_store = await get_default_metadata_store()
    vector_store = await get_default_vector_store()
    print("✅ Storage services initialized")
    print()

    # Get all speeches
    conn = await metadata_store._get_connection()

    try:
        # Find speeches without chunks
        speeches_without_chunks = await conn.fetch("""
            SELECT s.speech_id, s.title, s.full_text, s.speaker, s.party,
                   s.chamber, s.state, s.date, s.hansard_reference
            FROM speeches s
            LEFT JOIN speech_chunks sc ON s.speech_id = sc.speech_id
            WHERE sc.speech_id IS NULL
            GROUP BY s.speech_id
        """)

        total = len(speeches_without_chunks)
        print(f"📊 Found {total} speeches without chunks")
        print()

        if total == 0:
            print("✅ All speeches already have chunks!")
            return

        # Process each speech
        success_count = 0
        chunk_count = 0

        for idx, speech in enumerate(speeches_without_chunks, 1):
            speech_id = speech['speech_id']
            title = speech['title']

            print(f"  Processing {idx}/{total}: {title[:60]}...")

            try:
                # Chunk the text
                chunks = await chunk_text(speech['full_text'])
                print(f"    📝 Split into {len(chunks)} chunks")

                # Prepare metadata for each chunk
                chunk_metadatas = []
                for chunk_idx, chunk in enumerate(chunks):
                    metadata = {
                        "speech_id": speech_id,
                        "chunk_index": chunk_idx,
                        "chunk_size": len(chunk),
                        "speaker": speech['speaker'],
                        "party": speech['party'],
                        "chamber": speech['chamber'],
                        "state": speech['state'],
                        "date": speech['date'],
                        "hansard_reference": speech['hansard_reference'],
                    }
                    chunk_metadatas.append(metadata)

                # Add chunks with embeddings to vector store
                chunk_ids = await vector_store.add_chunks(
                    texts=chunks,
                    metadatas=chunk_metadatas,
                    speech_id=speech_id,
                )
                print(f"    ✅ {len(chunk_ids)} chunks added with embeddings")

                success_count += 1
                chunk_count += len(chunk_ids)

            except Exception as e:
                print(f"    ❌ Error: {e}")
                import traceback
                traceback.print_exc()

        print()
        print("=" * 80)
        print("Chunking Complete")
        print("=" * 80)
        print(f"✅ Successfully chunked: {success_count}/{total} speeches")
        print(f"📊 Total chunks created: {chunk_count}")
        print("=" * 80)

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
