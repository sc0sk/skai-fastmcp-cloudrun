#!/usr/bin/env python3
"""Drop and recreate speeches table with TEXT speech_id, then re-ingest data."""

import asyncio
from sqlalchemy import text
from src.storage.metadata_store import get_default_metadata_store


async def recreate_table():
    """Drop and recreate speeches table with correct schema."""
    
    store = await get_default_metadata_store()
    
    def _recreate(conn):
        print("🗑️  Dropping speeches table...")
        # CASCADE will also drop the foreign key constraints
        conn.execute(text("DROP TABLE IF EXISTS speeches CASCADE"))
        print("✅ Table dropped")
        
        print("\n🔧 Creating speeches table with TEXT speech_id...")
        conn.execute(text("""
            CREATE TABLE speeches (
                speech_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                speaker TEXT NOT NULL,
                party TEXT,
                chamber TEXT,
                electorate TEXT,
                state TEXT,
                date DATE NOT NULL,
                hansard_reference TEXT,
                full_text TEXT NOT NULL,
                word_count INTEGER,
                content_hash TEXT UNIQUE,
                topic_tags TEXT[],
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))
        print("✅ Table created with TEXT speech_id")
        
        # Create indexes
        print("\n📊 Creating indexes...")
        conn.execute(text(
            "CREATE INDEX speeches_speaker_idx ON speeches(speaker)"
        ))
        conn.execute(text(
            "CREATE INDEX speeches_date_idx ON speeches(date)"
        ))
        conn.execute(text(
            "CREATE INDEX speeches_party_idx ON speeches(party)"
        ))
        conn.execute(text(
            "CREATE INDEX speeches_chamber_idx ON speeches(chamber)"
        ))
        print("✅ Indexes created")
        
        # Verify
        result = conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'speeches' 
            AND column_name = 'speech_id'
        """))
        row = result.fetchone()
        if row:
            print(f"\n✅ Verified: {row[0]} is {row[1]}")
    
    await store._run_in_connection(_recreate)
    print("\n✅ Table recreation complete!")


if __name__ == "__main__":
    asyncio.run(recreate_table())
