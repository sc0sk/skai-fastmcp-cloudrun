#!/usr/bin/env python3
"""Grant IAM user permissions to Cloud SQL database."""

import asyncio
import os
from google.cloud.sql.connector import Connector
import asyncpg


async def grant_permissions():
    """Grant database permissions to IAM service account."""

    # Cloud SQL connection parameters
    project_id = "skai-fastmcp-cloudrun"
    region = "us-central1"
    instance = "hansard-db"
    database = "hansard"
    iam_user = "666924716777-compute@developer"

    # Initialize Cloud SQL Python Connector
    connector = Connector()

    try:
        # Connect using Cloud SQL Connector with IAM auth
        conn = await connector.connect_async(
            f"{project_id}:{region}:{instance}",
            "asyncpg",
            user=iam_user,
            db=database,
            enable_iam_auth=True,
        )

        print(f"✅ Connected to Cloud SQL as {iam_user}")

        # Grant permissions
        await conn.execute(f'GRANT CONNECT ON DATABASE hansard TO "{iam_user}"')
        await conn.execute(f'GRANT USAGE ON SCHEMA public TO "{iam_user}"')
        await conn.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "{iam_user}"')
        await conn.execute(f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "{iam_user}"')
        await conn.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{iam_user}"')
        await conn.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO "{iam_user}"')

        print(f"✅ Granted all necessary permissions to {iam_user}")

        await conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        raise

    finally:
        await connector.close_async()


if __name__ == "__main__":
    asyncio.run(grant_permissions())
