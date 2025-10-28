#!/usr/bin/env python3
"""Grant ALTER table permissions to IAM user scott.coleman@aph.gov.au."""

import asyncio
import os
from sqlalchemy import text, create_engine
from google.cloud.sql.connector import Connector
from google.cloud import secretmanager


async def grant_alter_permissions():
    """Connect as postgres using Secret Manager and grant ALTER permissions."""
    
    # Get postgres password from Secret Manager
    project_id = "skai-hansard"
    secret_id = "postgres-password"
    version_id = "latest"
    
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    
    print(f"📦 Retrieving postgres password from Secret Manager...")
    try:
        response = client.access_secret_version(request={"name": name})
        postgres_password = response.payload.data.decode("UTF-8")
        print("✅ Password retrieved")
    except Exception as e:
        print(f"❌ Failed to retrieve secret: {e}")
        print("💡 Create the secret with: gcloud secrets create postgres-password --data-file=- <<< 'YOUR_PASSWORD'")
        return
    
    instance_connection_name = "skai-hansard:australia-southeast1:hansard-db-v2"
    iam_user = "scott.coleman@aph.gov.au"
    
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
            print(f"🔧 Granting ALTER permissions to {iam_user}...")
            
            # Grant ALTER permission on speeches table
            conn.execute(text(
                f'GRANT ALTER ON TABLE speeches TO "{iam_user}"'
            ))
            print("✅ ALTER permission granted!")
            
            # Now alter the column as IAM user would do it
            print("🔧 Altering speech_id column from UUID to TEXT...")
            conn.execute(text(
                "ALTER TABLE speeches ALTER COLUMN speech_id TYPE TEXT"
            ))
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
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        engine.dispose()
        connector.close()


if __name__ == "__main__":
    asyncio.run(grant_alter_permissions())
