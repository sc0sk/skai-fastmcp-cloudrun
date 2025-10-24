#!/usr/bin/env python3
"""Check if hansard_speeches table has been populated."""

import asyncio
import asyncpg
from google.cloud.sql.connector import Connector

async def check_population():
    """Check record count in hansard_speeches table."""
    print("🔌 Connecting to Cloud SQL...")
    
    loop = asyncio.get_running_loop()
    connector = Connector(loop=loop)
    
    try:
        conn = await connector.connect_async(
            "skai-fastmcp-cloudrun:us-central1:hansard-db-v2",
            "asyncpg",
            user="postgresql",
            password=r"tq(#C?Yf/JA}pK\c",
            db="hansard",
        )
        
        try:
            # Count total records
            count = await conn.fetchval("SELECT COUNT(*) FROM hansard_speeches")
            
            print(f"\n📊 Database Status:")
            print(f"   Total records in hansard_speeches: {count}")
            
            if count > 0:
                # Get sample records
                rows = await conn.fetch(
                    "SELECT speaker, date, LEFT(content, 100) as content_preview FROM hansard_speeches LIMIT 3"
                )
                print(f"\n📝 Sample records:")
                for row in rows:
                    print(f"   - {row['speaker']} ({row['date']}): {row['content_preview']}...")
                print(f"\n✅ Database has been populated with {count} records!")
            else:
                print("\n⚠️  Database is empty - needs to be populated")
                
        finally:
            await conn.close()
            
    finally:
        await connector.close_async()

if __name__ == "__main__":
    asyncio.run(check_population())
