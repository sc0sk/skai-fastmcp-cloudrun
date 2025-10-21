"""
Health check endpoints for Cloud Run deployment.

Provides:
- /health: Liveness probe (basic server responsiveness)
- /ready: Readiness probe (database/Redis connectivity checks)
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def check_database() -> Dict[str, Any]:
    """Check Cloud SQL PostgreSQL connectivity."""
    try:
        from src.storage.vector_store import get_default_vector_store

        vector_store = await get_default_vector_store()
        # Simple connectivity check - vector store initialization validates connection
        return {"status": "healthy", "latency_ms": 0}  # Placeholder for actual latency
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_redis() -> Dict[str, Any]:
    """Check Redis connectivity (if configured)."""
    redis_host = os.getenv("REDIS_HOST")
    if not redis_host:
        # Redis not configured (development mode)
        return {"status": "healthy", "note": "in-memory storage (development mode)"}

    try:
        import redis.asyncio as aioredis

        redis_client = await aioredis.from_url(
            f"redis://{redis_host}:{os.getenv('REDIS_PORT', 6379)}",
            decode_responses=True,
        )
        await redis_client.ping()
        await redis_client.aclose()
        return {"status": "healthy", "latency_ms": 0}  # Placeholder for actual latency
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_embeddings() -> Dict[str, Any]:
    """Check Vertex AI Embeddings availability."""
    try:
        from src.storage.embeddings import get_default_embeddings

        embeddings = get_default_embeddings()
        # If initialization succeeds, model is available
        return {"status": "healthy", "model": "text-embedding-005"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def health_check() -> tuple[int, str]:
    """
    Liveness probe - basic server responsiveness.

    Returns:
        (status_code, body) tuple
    """
    return (200, "OK")


async def readiness_check() -> tuple[int, str]:
    """
    Readiness probe - verify all dependencies are healthy.

    Returns:
        (status_code, body) tuple with JSON response
    """
    try:
        # Run all checks in parallel
        db_check, redis_check, embeddings_check = await asyncio.gather(
            check_database(), check_redis(), check_embeddings(), return_exceptions=True
        )

        # Determine overall status
        checks = {
            "database": db_check if not isinstance(db_check, Exception) else {"status": "unhealthy", "error": str(db_check)},
            "redis": redis_check if not isinstance(redis_check, Exception) else {"status": "unhealthy", "error": str(redis_check)},
            "embeddings": embeddings_check if not isinstance(embeddings_check, Exception) else {"status": "unhealthy", "error": str(embeddings_check)},
        }

        # Check if any component is unhealthy
        is_healthy = all(check.get("status") == "healthy" for check in checks.values())

        response = {
            "status": "healthy" if is_healthy else "unhealthy",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        if not is_healthy:
            errors = [
                f"{name}: {check.get('error', 'unknown error')}"
                for name, check in checks.items()
                if check.get("status") != "healthy"
            ]
            response["error"] = "; ".join(errors)
            return (503, json.dumps(response, indent=2))

        return (200, json.dumps(response, indent=2))

    except Exception as e:
        error_response = {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        return (503, json.dumps(error_response, indent=2))


if __name__ == "__main__":
    # Simple CLI test
    import argparse

    parser = argparse.ArgumentParser(description="Health check endpoints")
    parser.add_argument("endpoint", choices=["health", "ready"], help="Endpoint to check")
    args = parser.parse_args()

    if args.endpoint == "health":
        status_code, body = asyncio.run(health_check())
    else:
        status_code, body = asyncio.run(readiness_check())

    print(f"Status: {status_code}")
    print(body)
    sys.exit(0 if status_code == 200 else 1)
