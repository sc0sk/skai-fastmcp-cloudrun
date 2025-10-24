"""Configuration constants for the MCP server."""

import os

# Database table names
VECTOR_TABLE_NAME = "hansard_speeches"  # LangChain PostgresVectorStore table with embeddings
METADATA_TABLE_NAME = "speeches"  # Metadata table for speech records

# Cloud SQL instance configuration
CLOUDSQL_INSTANCE_NAME = "hansard-db-v2"  # Cloud SQL instance name
CLOUDSQL_TIER = "db-f1-micro"  # Shared-core, 0.6 GB RAM (cost-effective)
CLOUDSQL_DATABASE_VERSION = "POSTGRES_15"  # PostgreSQL version
CLOUDSQL_PGVECTOR_VERSION = "0.8.0"  # pgvector extension version

# Service account configuration
DB_ADMIN_SERVICE_ACCOUNT = "hansard-db-admin@skai-fastmcp-cloudrun.iam"  # Full ownership
DB_READONLY_SERVICE_ACCOUNT = "hansard-db-readonly@skai-fastmcp-cloudrun.iam"  # Read-only

# Default environment configurations
DEFAULT_GCP_PROJECT_ID = "skai-fastmcp-cloudrun"
DEFAULT_GCP_REGION = "us-central1"
DEFAULT_CLOUDSQL_DATABASE = "hansard"
DEFAULT_VERTEX_AI_LOCATION = "us-central1"
DEFAULT_EMBEDDING_MODEL = "text-embedding-005"
DEFAULT_EMBEDDING_DIMENSIONS = 768

# Environment variable getters
def get_gcp_project_id() -> str:
    """Get GCP project ID from environment."""
    return os.getenv("GCP_PROJECT_ID")

def get_gcp_region() -> str:
    """Get GCP region from environment."""
    return os.getenv("GCP_REGION", DEFAULT_GCP_REGION)

def get_cloudsql_instance() -> str:
    """Get Cloud SQL instance name from environment."""
    return os.getenv("CLOUDSQL_INSTANCE")

def get_cloudsql_database() -> str:
    """Get Cloud SQL database name from environment."""
    return os.getenv("CLOUDSQL_DATABASE", DEFAULT_CLOUDSQL_DATABASE)

def get_cloudsql_user() -> str:
    """Get Cloud SQL user from environment (None for IAM auth)."""
    return os.getenv("CLOUDSQL_USER")

def get_database_password() -> str:
    """Get database password from environment (None for IAM auth)."""
    return os.getenv("DATABASE_PASSWORD")

def get_vertex_ai_location() -> str:
    """Get Vertex AI location from environment."""
    return os.getenv("VERTEX_AI_LOCATION", DEFAULT_VERTEX_AI_LOCATION)
