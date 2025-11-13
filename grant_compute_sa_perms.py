#!/usr/bin/env python3
"""
Grant database permissions to compute service account via Cloud SQL Proxy.
This script connects as postgres and grants the IAM service account full permissions.
"""
import os
import sys
from google.cloud.sql.connector import Connector
import pg8000

PROJECT_ID = "skai-fastmcp-cloudrun"
REGION = "us-central1"
INSTANCE = "hansard-db-v2"
DATABASE = "hansard"
INSTANCE_CONNECTION_NAME = f"{PROJECT_ID}:{REGION}:{INSTANCE}"

def main():
    print("=" * 60)
    print("GRANT PERMISSIONS TO COMPUTE SERVICE ACCOUNT")
    print("=" * 60)
    print()
    
    # Password for postgres user
    postgres_password = "efzDDQ1Mxb8VOOAUzJsEVsKdJxtBXTdF"
    
    print(f"Connecting to: {INSTANCE_CONNECTION_NAME}")
    print(f"Database: {DATABASE}")
    print(f"User: postgres")
    print()
    
    # Initialize Cloud SQL Python Connector
    connector = Connector()
    
    try:
        # Connect as postgres user
        conn = connector.connect(
            INSTANCE_CONNECTION_NAME,
            "pg8000",
            user="postgres",
            password=postgres_password,
            db=DATABASE,
        )
        
        cursor = conn.cursor()
        
        # Execute the permission grants
        commands = [
            ("Make postgres superuser", "ALTER USER postgres WITH SUPERUSER"),
            ("Transfer langchain_pg_collection", 'ALTER TABLE langchain_pg_collection OWNER TO "666924716777-compute@developer"'),
            ("Transfer langchain_pg_embedding", 'ALTER TABLE langchain_pg_embedding OWNER TO "666924716777-compute@developer"'),
            ("Grant table privileges", 'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "666924716777-compute@developer"'),
            ("Grant sequence privileges", 'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "666924716777-compute@developer"'),
            ("Set default table privileges", 'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO "666924716777-compute@developer"'),
            ("Set default sequence privileges", 'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO "666924716777-compute@developer"'),
            ("Remove postgres superuser", "ALTER USER postgres WITH NOSUPERUSER"),
        ]
        
        for description, sql in commands:
            print(f"⏳ {description}...")
            try:
                cursor.execute(sql)
                conn.commit()
                print(f"✅ {description}")
            except Exception as e:
                print(f"❌ {description}: {e}")
                conn.rollback()
        
        print()
        print("=" * 60)
        print("VERIFICATION")
        print("=" * 60)
        print()
        
        # Check table ownership
        print("Table ownership:")
        cursor.execute("SELECT tablename, tableowner FROM pg_tables WHERE schemaname = 'public'")
        for row in cursor.fetchall():
            print(f"  {row[0]:30} → {row[1]}")
        
        print()
        print("=" * 60)
        print("✅ COMPLETE!")
        print("=" * 60)
        print("ChatGPT searches should now work!")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)
    finally:
        connector.close()

if __name__ == "__main__":
    main()
