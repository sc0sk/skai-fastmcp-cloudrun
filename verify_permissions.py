#!/usr/bin/env python3
"""Verify IAM service account has permissions on speeches table."""

import asyncio
from google.cloud.sql.connector import Connector
import os

async def verify():
    """Connect as IAM service account and test SELECT."""

    instance_connection_name = "skai-fastmcp-cloudrun:us-central1:hansard-db-v2"
    database = "hansard"
    service_account = "hansard-mcp-local-dev@skai-fastmcp-cloudrun.iam.gserviceaccount.com"

    print(f"🔗 Connecting as IAM service account {service_account}...")

    loop = asyncio.get_running_loop()
    async with Connector(loop=loop) as connector:
        conn = await connector.connect_async(
            instance_connection_name,
            "pg8000",
            user=service_account,
            db=database,
            enable_iam_auth=True
        )

        print(f"✅ Connected to database {database}")

        # Try SELECT on speeches table
        print("\n🔍 Testing SELECT on speeches table...")
        try:
            result = await conn.run(lambda conn: conn.execute("SELECT COUNT(*) FROM speeches"))
            print(f"✅ SELECT works! Row count: {result[0][0]}")
        except Exception as e:
            print(f"❌ SELECT failed: {e}")

        # Try INSERT test
        print("\n🔍 Testing INSERT on speeches table...")
        try:
            await conn.run(lambda conn: conn.execute("BEGIN"))
            await conn.run(lambda conn: conn.execute("""
                INSERT INTO speeches (title, full_text, speaker, party, chamber, electorate, state, date, hansard_reference, word_count, content_hash)
                VALUES ('test', 'test', 'test', 'test', 'REPS', 'test', 'VIC', '2024-01-01', 'test', 1, 'test')
            """))
            await conn.run(lambda conn: conn.execute("ROLLBACK"))
            print(f"✅ INSERT works!")
        except Exception as e:
            print(f"❌ INSERT failed: {e}")
            await conn.run(lambda conn: conn.execute("ROLLBACK"))

        await conn.close()

    print("\n✅ Verification complete!")


if __name__ == "__main__":
    asyncio.run(verify())
