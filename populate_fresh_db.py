#!/usr/bin/env python3
"""
Populate fresh hansard_db_fresh with speeches using LangChain 1.0.
Includes: vector embeddings (Vertex AI), metadata (JSONB), full text.
"""

import os
import sys
import json
import uuid
from pathlib import Path
from typing import Optional

import frontmatter
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_vertexai import VertexAIEmbeddings
from sqlalchemy import text, create_engine
from google.cloud.sql.connector import Connector


# LangChain 1.0 text splitter config
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
MODEL_EMBEDDING_DIMENSION = 768


def get_db_engine():
    """Create SQLAlchemy engine with Cloud SQL connector."""
    connector = Connector()

    def getconn_fresh():
        return connector.connect(
            "skai-fastmcp-cloudrun:us-central1:hansard-db-v2",
            "pg8000",
            user=os.getenv("CLOUD_SQL_USER", "postgres"),
            db="hansard_db_fresh",
            enable_iam_auth=True,
        )

    return create_engine("postgresql+pg8000://", creator=getconn_fresh)


def create_collection(engine, collection_name: str = "hansard") -> str:
    """Create langchain_pg_collection and return collection_id."""
    collection_id = str(uuid.uuid4())

    sql = text("""
        INSERT INTO langchain_pg_collection (uuid, name, cmetadata)
        VALUES (:uuid, :name, :cmetadata)
        ON CONFLICT (name) DO UPDATE SET uuid = :uuid
        RETURNING uuid;
    """)

    with engine.connect() as conn:
        result = conn.execute(sql, {
            "uuid": collection_id,
            "name": collection_name,
            "cmetadata": json.dumps({"source": "hansard", "version": "1.0"})
        })
        conn.commit()
        return str(result.scalar())


def load_markdown_file(filepath: Path) -> Optional[dict]:
    """Load and parse markdown file with frontmatter."""
    try:
        with open(filepath, encoding="utf-8") as f:
            post = frontmatter.load(f)

        return {
            "metadata": post.metadata,
            "content": post.content,
            "filename": filepath.name,
        }
    except Exception as e:
        print(f"⚠️  Error loading {filepath}: {e}")
        return None


def chunk_document(
    content: str,
    metadata: dict,
    filename: str
) -> list[dict]:
    """Split document into chunks with metadata."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""]
    )

    chunks = splitter.split_text(content)

    chunked_docs = []
    for idx, chunk in enumerate(chunks):
        chunk_metadata = {
            **metadata,
            "filename": filename,
            "chunk_index": idx,
            "chunk_count": len(chunks),
            "char_count": len(chunk),
        }
        chunked_docs.append({
            "content": chunk,
            "metadata": chunk_metadata,
        })

    return chunked_docs


def generate_embeddings(documents: list[dict]) -> list[dict]:
    """Generate embeddings for documents using Vertex AI."""
    print("🧠 Initializing Vertex AI embeddings...")
    embeddings = VertexAIEmbeddings(
        project="skai-fastmcp-cloudrun",
        location="us-central1",
        model_name="text-embedding-004",
    )

    print(f"📝 Generating embeddings for {len(documents)} chunks...")
    texts = [doc["content"] for doc in documents]

    # Batch embed
    embedded_docs = []
    batch_size = 10
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        batch_vectors = embeddings.embed_documents(batch)

        for doc, vector in zip(documents[i : i + batch_size], batch_vectors):
            embedded_docs.append({
                "content": doc["content"],
                "metadata": doc["metadata"],
                "embedding": vector,
            })

        print(f"  ✓ Processed {min(i + batch_size, len(texts))}/{len(texts)}")

    return embedded_docs


def insert_embeddings(engine, collection_id: str, embedded_docs: list[dict]):
    """Insert embeddings into langchain_pg_embedding table."""
    print(f"💾 Inserting {len(embedded_docs)} embeddings...")

    sql = text("""
        INSERT INTO langchain_pg_embedding (id, collection_id, embedding, document, cmetadata)
        VALUES (:id, :collection_id, :embedding, :document, :cmetadata)
        ON CONFLICT (id) DO NOTHING;
    """)

    with engine.connect() as conn:
        for idx, doc in enumerate(embedded_docs):
            doc_id = f"{doc['metadata'].get('filename', 'doc')}_{idx}"

            conn.execute(sql, {
                "id": doc_id,
                "collection_id": collection_id,
                "embedding": doc["embedding"],  # pgvector auto-converts
                "document": doc["content"],
                "cmetadata": json.dumps(doc["metadata"])
            })

            if (idx + 1) % 50 == 0:
                print(f"  ✓ Inserted {idx + 1}/{len(embedded_docs)}")

        conn.commit()
        print(f"✅ All embeddings inserted")


def verify_population(engine):
    """Verify data was populated."""
    with engine.connect() as conn:
        # Count embeddings
        result = conn.execute(text("SELECT COUNT(*) FROM langchain_pg_embedding;"))
        count = result.scalar()
        print(f"📊 Total embeddings: {count}")

        # Sample embedding
        result = conn.execute(text("""
            SELECT id, document, char_length(document) as length
            FROM langchain_pg_embedding
            LIMIT 3;
        """))
        print("\n📋 Sample embeddings:")
        for row in result:
            print(f"  - {row[0]}: {row[1][:50]}... ({row[2]} chars)")


def main():
    """Main population flow."""
    print("\n" + "="*80)
    print("POPULATING hansard_db_fresh WITH SPEECHES")
    print("="*80)

    # Get markdown files
    data_dir = Path(__file__).parent / "data" / "hansard_converted"
    md_files = list(data_dir.glob("*.md"))[:10]  # Start with 10 files

    if not md_files:
        print(f"❌ No markdown files found in {data_dir}")
        sys.exit(1)

    print(f"\n📂 Found {len(md_files)} markdown files")

    # Connect to DB
    print("\n🔗 Connecting to database...")
    engine = get_db_engine()

    try:
        # Create collection
        print("\n📦 Creating collection...")
        collection_id = create_collection(engine)
        print(f"✅ Collection created: {collection_id}")

        # Load, chunk, and embed documents
        all_embedded_docs = []

        for i, filepath in enumerate(md_files):
            print(f"\n📄 [{i+1}/{len(md_files)}] Processing {filepath.name}...")

            # Load
            doc = load_markdown_file(filepath)
            if not doc:
                continue

            # Chunk
            chunks = chunk_document(
                doc["content"],
                doc["metadata"],
                doc["filename"]
            )
            print(f"  ✓ Split into {len(chunks)} chunks")

            # Embed (do per-file to manage memory)
            embedded = generate_embeddings(chunks)
            all_embedded_docs.extend(embedded)

        # Insert all embeddings
        print("\n💾 Inserting all embeddings...")
        insert_embeddings(engine, collection_id, all_embedded_docs)

        # Verify
        print("\n✅ Verification:")
        verify_population(engine)

        print("\n" + "="*80)
        print("✨ POPULATION COMPLETE!")
        print("="*80)

    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
