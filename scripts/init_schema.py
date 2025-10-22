#!/usr/bin/env python3
"""Initialize database schema using metadata store connection."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from storage.metadata_store import get_default_metadata_store

async def main():
    """Initialize schema."""
    print("=" * 80)
    print("Initializing Hansard Database Schema")
    print("=" * 80)
    print()

    # Get metadata store (uses environment variables)
    metadata_store = await get_default_metadata_store()

    # Read SQL file
    sql_file = Path(__file__).parent / "init_hansard_db_v2.sql"
    if not sql_file.exists():
        sql_file = Path(__file__).parent.parent / "init_hansard_db_v2.sql"
    with open(sql_file, 'r') as f:
        content = f.read()

    # Parse SQL statements (skip comments and psql commands)
    lines = []
    for line in content.split('\n'):
        line = line.strip()
        if line and not line.startswith('--') and not line.startswith('\\'):
            lines.append(line)

    sql = ' '.join(lines)
    commands = [cmd.strip() for cmd in sql.split(';') if cmd.strip()]

    # Execute each command
    print(f"Executing {len(commands)} SQL commands...")
    conn = await metadata_store._get_connection()

    for idx, cmd in enumerate(commands, 1):
        try:
            await conn.execute(cmd)
            preview = cmd[:70].replace('\n', ' ')
            print(f"  ✅ [{idx}/{len(commands)}] {preview}...")
        except Exception as e:
            preview = cmd[:70].replace('\n', ' ')
            print(f"  ⚠️  [{idx}/{len(commands)}] {preview}... - {e}")

    # Verify
    result = await conn.fetch("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name IN ('speeches', 'speech_chunks')
        ORDER BY table_name
    """)

    print()
    print("=" * 80)
    if len(result) == 2:
        print("✅ Schema initialized successfully!")
        print(f"   - speeches table: ✓")
        print(f"   - speech_chunks table: ✓")
    else:
        print("⚠️  Warning: Some tables may not have been created")
        for row in result:
            print(f"   - {row['table_name']}")

    await conn.close()
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
