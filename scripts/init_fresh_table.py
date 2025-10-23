#!/usr/bin/env python3
"""Initialize a fresh hansard_speeches table with LangChain schema."""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain_google_cloud_sql_pg import PostgresEngine
from langchain_google_vertexai import VertexAIEmbeddings


async def main():
    """Initialize table."""
    print("=" * 80)
    print("Initialize Hansard Speeches Table")
    print("=" * 80)

    # Connect
    print("\n🔌 Connecting to Cloud SQL...")
    engine = await PostgresEngine.afrom_instance(
        project_id=os.getenv("GCP_PROJECT_ID", "skai-fastmcp-cloudrun"),
        region=os.getenv("GCP_REGION", "us-central1"),
        instance=os.getenv("CLOUDSQL_INSTANCE", "hansard-db-v2"),
        database=os.getenv("CLOUDSQL_DATABASE", "hansard"),
    )

    # Initialize table using LangChain's method
    print("\n📊 Creating table with LangChain schema...")
    await engine.ainit_vectorstore_table(
        table_name="hansard_speeches",
        vector_size=768,  # text-embedding-005 dimension
        overwrite_existing=True,  # Force fresh table
    )

    print("\n✅ Table created successfully!")
    print("   Table: hansard_speeches")
    print("   Columns: langchain_id, content, embedding, langchain_metadata")

    # Close
    await engine.close()
    print("\n🔌 Connection closed\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
