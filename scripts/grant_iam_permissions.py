#!/usr/bin/env python3
"""Grant database permissions to IAM user for Cloud SQL."""

import asyncio
import asyncpg
from google.cloud.sql.connector import Connector

async def grant_permissions():
    """Grant database-level permissions to IAM service account."""
    print("🔌 Connecting to Cloud SQL as postgresql user...")

    # Initialize Connector inside async context
    loop = asyncio.get_running_loop()
    connector = Connector(loop=loop)

    try:
        # Connect with the correct credentials
        conn: asyncpg.Connection = await connector.connect_async(
            "skai-fastmcp-cloudrun:us-central1:hansard-db-v2",
            "asyncpg",
            user="postgresql",
            password=r"tq(#C?Yf/JA}pK\c",
            db="hansard",
        )
        
        try:
            print("📊 Granting permissions to 666924716777-compute@developer...")
            
            # Grant USAGE on schema
            await conn.execute('GRANT USAGE ON SCHEMA public TO "666924716777-compute@developer";')
            print("✓ Granted USAGE on schema public")
            
            # Grant SELECT, INSERT, UPDATE on hansard_speeches table
            await conn.execute('GRANT SELECT, INSERT, UPDATE ON TABLE hansard_speeches TO "666924716777-compute@developer";')
            print("✓ Granted SELECT, INSERT, UPDATE on hansard_speeches")
            
            # Grant USAGE on sequences
            await conn.execute('GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO "666924716777-compute@developer";')
            print("✓ Granted USAGE on all sequences")
            
            # Change table owner
            await conn.execute('ALTER TABLE hansard_speeches OWNER TO "666924716777-compute@developer";')
            print("✓ Changed hansard_speeches owner to 666924716777-compute@developer")
            
            print("\n✅ All permissions granted successfully!")
            
        finally:
            await conn.close()
            
    finally:
        await connector.close_async()
        print("🔌 Closed connection")

if __name__ == "__main__":
    asyncio.run(grant_permissions())
