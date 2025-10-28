#!/usr/bin/env python3
"""Alter speeches table speech_id column from UUID to TEXT."""

import asyncio
import os
from sqlalchemy import text, create_engine
from google.cloud.sql.connector import Connector

async def alter_column():
    """Connect as postgres user and alter the column type."""
    
    # Get postgres password from environment or prompt
    postgres_password = os.getenv('POSTGRES_PASSWORD')
    if not postgres_password:
        import getpass
        postgres_password = getpass.getpass('Enter postgres password: ')
    
    instance_connection_name = "skai-hansard:australia-southeast1:hansard-db-v2"
    
    connector = Connector()
    
    def getconn():
        conn = connector.connect(
            instance_connection_name,
            "pg8000",
            user="postgres",
            password=postgres_password,
            db="hansard",
        )
        return conn
    
    engine = create_engine(
        "postgresql+pg8000://",
        creator=getconn,
    )
    
    try:
        with engine.begin() as conn:
            print("🔧 Altering speech_id column from UUID to TEXT...")
            conn.execute(text("ALTER TABLE speeches ALTER COLUMN speech_id TYPE TEXT"))
            print("✅ Column altered successfully!")
            
            # Verify
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'speeches' 
                AND column_name = 'speech_id'
            """))
            row = result.fetchone()
            if row:
                print(f"✅ Verified: {row[0]} is now {row[1]}")
    finally:
        engine.dispose()
        connector.close()

if __name__ == "__main__":
    asyncio.run(alter_column())
