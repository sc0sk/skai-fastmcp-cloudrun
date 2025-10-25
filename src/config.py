"""Configuration constants for the MCP server."""

import os

# Database table names
# LangChain PostgresVectorStore table with embeddings
VECTOR_TABLE_NAME = "hansard_speeches"
METADATA_TABLE_NAME = "speeches"  # Metadata table for speech records

# Cloud SQL instance configuration
CLOUDSQL_INSTANCE_NAME = "hansard-db-v2"  # Cloud SQL instance name
CLOUDSQL_TIER = "db-f1-micro"  # Shared-core, 0.6 GB RAM (cost-effective)
CLOUDSQL_DATABASE_VERSION = "POSTGRES_15"  # PostgreSQL version
CLOUDSQL_PGVECTOR_VERSION = "0.8.0"  # pgvector extension version

# Service account configuration
# Full ownership
DB_ADMIN_SERVICE_ACCOUNT = "hansard-db-admin@skai-fastmcp-cloudrun.iam"
# Read-only
DB_READONLY_SERVICE_ACCOUNT = "hansard-db-readonly@skai-fastmcp-cloudrun.iam"

# Default environment configurations
DEFAULT_GCP_PROJECT_ID = "skai-fastmcp-cloudrun"
DEFAULT_GCP_REGION = "us-central1"
DEFAULT_CLOUDSQL_DATABASE = "hansard"
DEFAULT_VERTEX_AI_LOCATION = "us-central1"
DEFAULT_EMBEDDING_MODEL = "text-embedding-005"
DEFAULT_EMBEDDING_DIMENSIONS = 768

# Vector backend selection (feature-flagged rollout)
# options: "legacy" (google wrapper), "postgres" (langchain-postgres)
DEFAULT_VECTOR_BACKEND = "legacy"
DEFAULT_PGVECTOR_COLLECTION = "hansard"

# Environment variable getters


def get_gcp_project_id() -> str | None:
    """Get GCP project ID from environment."""
    return os.getenv("GCP_PROJECT_ID")



def get_gcp_region() -> str:
    """Get GCP region from environment."""
    return os.getenv("GCP_REGION", DEFAULT_GCP_REGION)



def get_cloudsql_instance() -> str | None:
    """Get Cloud SQL instance name from environment."""
    return os.getenv("CLOUDSQL_INSTANCE")



def get_cloudsql_database() -> str:
    """Get Cloud SQL database name from environment."""
    return os.getenv("CLOUDSQL_DATABASE", DEFAULT_CLOUDSQL_DATABASE)



def get_cloudsql_user() -> str | None:
    """Get Cloud SQL user from environment (None for IAM auth)."""
    return os.getenv("CLOUDSQL_USER")



def get_database_password() -> str | None:
    """Get database password from environment (None for IAM auth)."""
    return os.getenv("DATABASE_PASSWORD")



def get_vertex_ai_location() -> str:
    """Get Vertex AI location from environment."""
    return os.getenv("VERTEX_AI_LOCATION", DEFAULT_VERTEX_AI_LOCATION)



def get_vector_backend() -> str:
    """Get vector backend selection from environment.

    Returns:
        "legacy" or "postgres"
    """
    return os.getenv("VECTOR_BACKEND", DEFAULT_VECTOR_BACKEND)



def get_pgvector_collection() -> str:
    """Get PGVector collection name from environment.

    The dedicated langchain-postgres backend uses collections to scope data.
    """
    return os.getenv("PGVECTOR_COLLECTION", DEFAULT_PGVECTOR_COLLECTION)

# Ingestion configuration
DEFAULT_ADMIN_ROLE_CLAIM = "role"
DEFAULT_ADMIN_ROLE_VALUE = "admin"
DEFAULT_INGESTION_BASE_DIR = "/data/hansard"
DEFAULT_DUPLICATE_POLICY = "skip"
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 100
DEFAULT_EMBEDDING_BATCH_SIZE = 250



def get_admin_role_claim() -> str:
    """Get admin role claim name from environment."""
    return os.getenv("ADMIN_ROLE_CLAIM", DEFAULT_ADMIN_ROLE_CLAIM)



def get_admin_role_value() -> str:
    """Get required admin role value from environment."""
    return os.getenv("ADMIN_ROLE_VALUE", DEFAULT_ADMIN_ROLE_VALUE)



def get_ingestion_base_dir() -> str:
    """Get ingestion base directory from environment."""
    return os.getenv("INGESTION_BASE_DIR", DEFAULT_INGESTION_BASE_DIR)



def get_duplicate_policy() -> str:
    """Get duplicate handling policy from environment."""
    return os.getenv("DUPLICATE_POLICY", DEFAULT_DUPLICATE_POLICY)



def get_chunk_size() -> int:
    """Get text chunk size from environment."""
    return int(os.getenv("CHUNK_SIZE", str(DEFAULT_CHUNK_SIZE)))



def get_chunk_overlap() -> int:
    """Get chunk overlap size from environment."""
    return int(os.getenv("CHUNK_OVERLAP", str(DEFAULT_CHUNK_OVERLAP)))



def get_embedding_batch_size() -> int:
    """Get embedding batch size from environment."""
    default_str = str(DEFAULT_EMBEDDING_BATCH_SIZE)
    return int(os.getenv("EMBEDDING_BATCH_SIZE", default_str))
