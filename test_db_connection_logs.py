#!/usr/bin/env python3
"""Trigger database connection to generate CloudSQLEngine logs."""

import asyncio
import os

# Set Cloud Run environment
os.environ['USE_IAM_AUTH'] = 'true'
os.environ['K_SERVICE'] = 'test-cloud-run-validation'

# Trigger vector store initialization (which creates CloudSQLEngine connection)
async def test_connection():
    from src.storage.vector_store import get_default_vector_store

    print("Creating vector store (triggers CloudSQLEngine connection)...")
    service = await get_default_vector_store()

    # Get the vector store (triggers connection)
    store = await service._get_vector_store()

    # Get the engine to check IAM detection
    engine_manager = service._engine_manager

    print(f"\n✅ Connection successful!")
    print(f"   Detected IAM user: {engine_manager.detected_iam_user}")
    print(f"   Detection method: {engine_manager.detection_method}")
    print(f"   IAM valid: {engine_manager.iam_valid}")

    # Clean up
    await service.close()

if __name__ == "__main__":
    asyncio.run(test_connection())
