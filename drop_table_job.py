#!/usr/bin/env python3
"""Drop langchain_vector_store table to allow recreation with correct schema."""

import asyncio
from google.cloud.sql.connector import Connector
import os

# Set environment variables
os.environ["GCP_PROJECT_ID"] = "skai-fastmcp-cloudrun"
os.environ["GCP_REGION"] = "us-central1"
os.environ["CLOUDSQL_INSTANCE"] = "hansard-db-v2"
os.environ["CLOUDSQL_DATABASE"] = "hansard"
os.environ["GCP_PROJECT_NUMBER"] = "666924716777"


async def main():
    """Drop the table."""
    print("🗑️  Dropping langchain_vector_store table...")

    # Use IAM auth with service account
    project_number = os.getenv("GCP_PROJECT_NUMBER", "666924716777")
    user = f"{project_number}-compute@developer.gserviceaccount.com"

    # Create connector in the same event loop
    loop = asyncio.get_running_loop()
    connector = Connector(loop=loop)

    try:
        conn = await connector.connect_async(
            "skai-fastmcp-cloudrun:us-central1:hansard-db-v2",
            "asyncpg",
            user=user,
            db="hansard",
            enable_iam_auth=True,
            password=None,
        )

        # Drop table
        await conn.execute("DROP TABLE IF EXISTS langchain_vector_store CASCADE")
        print("✅ Table dropped successfully!")

        await conn.close()
    finally:
        await connector.close_async()


if __name__ == "__main__":
    asyncio.run(main())
