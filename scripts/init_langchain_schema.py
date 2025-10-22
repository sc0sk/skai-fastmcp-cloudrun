#!/usr/bin/env python3
"""Initialize LangChain-compatible vector store table with custom metadata columns.

This follows LangChain best practices:
- Uses default LangChain schema (id, content, embedding, langchain_metadata JSONB)
- Adds custom columns for frequently-filtered fields (speaker, party, chamber, date, speech_type)
- Stores complex nested metadata in langchain_metadata JSONB column
"""

import asyncio
import os
import sys
from pathlib import Path
from sqlalchemy import Column, String, Date, Text

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain_google_cloud_sql_pg import PostgresEngine


async def init_schema():
    """Initialize vector store table with custom metadata columns."""
    print("🔌 Connecting to Cloud SQL...")

    engine = await PostgresEngine.afrom_instance(
        project_id=os.getenv("GCP_PROJECT_ID", "skai-fastmcp-cloudrun"),
        region=os.getenv("GCP_REGION", "us-central1"),
        instance=os.getenv("CLOUDSQL_INSTANCE", "hansard-db-v2"),
        database=os.getenv("CLOUDSQL_DATABASE", "hansard"),
    )

    print("📊 Creating hansard_speeches table with custom metadata columns...")

    # Define custom metadata columns for frequently-filtered fields
    # These enable efficient SQL filtering without parsing JSONB
    metadata_columns = [
        Column("speaker", String(200)),  # Normalized speaker name
        Column("party", String(100)),  # Political party
        Column("chamber", String(50)),  # House of Representatives or Senate
        Column("date", Date),  # Speech date (enables date range queries)
        Column("speech_type", String(100)),  # maiden-speech, debate, question, etc.
        Column("electorate", String(100)),  # Electoral division (House only)
        Column("speaker_id", String(20)),  # Unique speaker identifier
        Column("utterance_id", String(100)),  # Unique utterance identifier
        Column("debate", Text),  # Debate topic
    ]

    # Initialize table (drops existing if present for fresh start)
    await engine.ainit_vectorstore_table(
        table_name="hansard_speeches",
        vector_size=768,  # text-embedding-005 output dimension
        metadata_columns=metadata_columns,
        overwrite_existing=True,  # Drop and recreate
    )

    print("✅ Schema initialized successfully!")
    print("\nTable structure:")
    print("  - id (UUID, primary key) - LangChain document ID")
    print("  - content (TEXT) - Speech text chunk")
    print("  - embedding (VECTOR(768)) - Vertex AI embedding")
    print("  - langchain_metadata (JSONB) - Complex nested metadata")
    print("\nCustom metadata columns:")
    for col in metadata_columns:
        print(f"  - {col.name} ({col.type}) - Indexed for efficient filtering")

    await engine.close()


if __name__ == "__main__":
    asyncio.run(init_schema())
