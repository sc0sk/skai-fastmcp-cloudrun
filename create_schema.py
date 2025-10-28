import asyncio
import os
import sys

# Add src directory to Python path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from storage.metadata_store import MetadataStore
from config import METADATA_TABLE_NAME

async def main():
    """Create the speeches table in the database."""
    print("Initializing metadata store to create schema...")
    
    # Use environment variables for connection details
    store = MetadataStore(
        project_id=os.getenv("GCP_PROJECT_ID"),
        region=os.getenv("GCP_REGION"),
        instance=os.getenv("CLOUDSQL_INSTANCE"),
        database=os.getenv("CLOUDSQL_DATABASE"),
        user=None,  # Use IAM auth
        password=None, # Use IAM auth
    )
    
    # The table name is now sourced from config
    table_name = METADATA_TABLE_NAME
    
    # SQL to create the table
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        speech_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        title TEXT,
        full_text TEXT,
        speaker VARCHAR(255),
        party VARCHAR(100),
        chamber VARCHAR(50),
        electorate VARCHAR(100),
        state VARCHAR(50),
        date DATE,
        hansard_reference VARCHAR(255),
        word_count INTEGER,
        content_hash VARCHAR(64) UNIQUE,
        topic_tags TEXT[],
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    conn = None
    try:
        # Get a connection and execute the CREATE TABLE statement
        conn = await store._get_connection()
        await conn.execute(create_table_sql)
        print(f"Successfully created or verified table '{table_name}' in database '{store.database}'.")
        
        # Optional: Add an index for faster lookups on content_hash
        await conn.execute(f"CREATE INDEX IF NOT EXISTS idx_content_hash ON {table_name} (content_hash);")
        print("Successfully created or verified index on 'content_hash'.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            await conn.close()
        if store._connector:
            await store._connector.close_async()

if __name__ == "__main__":
    # Set PYTHONPATH to include the 'src' directory
    # This allows the script to find the 'src' modules
    if 'src' not in os.environ.get('PYTHONPATH', ''):
        os.environ['PYTHONPATH'] = f"{os.getcwd()}/src:{os.environ.get('PYTHONPATH', '')}"

    asyncio.run(main())
