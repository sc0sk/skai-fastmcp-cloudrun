# Implementation Guide: LangChain 1.0 with Community PGVector

**Feature**: 015-langchain-1.0-community-pgvector  
**Status**: Ready to implement  
**Last Updated**: 2025-10-25

## Prerequisites

- Python 3.11+
- Access to Cloud SQL PostgreSQL instance
- IAM permissions for Cloud SQL
- Development database for testing

## Step-by-Step Implementation

### Phase 1: Foundation

#### Step 1.1: Update Dependencies

**File**: `pyproject.toml`

```toml
[project]
dependencies = [
    # LangChain 1.0+ core
    "langchain>=1.0.0,<2.0.0",
    "langchain-community>=0.3.0,<0.4.0",
    
    # Google integrations (all support LangChain 1.0)
    "langchain-google-vertexai>=2.0.0,<3.0.0",
    "langchain-google-genai>=2.0.0,<3.0.0",
    
    # Database and vector support
    "sqlalchemy>=2.0.0,<3.0.0",
    "pg8000>=1.30.0,<2.0.0",
    "pgvector>=0.3.0,<0.4.0",
    
    # Cloud SQL connectivity
    "google-cloud-sql-connector>=1.11.0,<2.0.0",
    
    # Remove: langchain-google-cloud-sql-pg (blocks at <1.0)
]
```

**Commands**:
```bash
# Update dependencies
uv sync

# Verify installation
uv run python -c "import langchain; print(f'LangChain version: {langchain.__version__}')"
uv run python -c "from langchain_community.vectorstores import PGVector; print('PGVector imported successfully')"
uv run python -c "from langchain_google_vertexai import VertexAIEmbeddings; print('VertexAI embeddings imported successfully')"
```

#### Step 1.2: Add Configuration

**File**: `src/config.py`

```python
from pydantic_settings import BaseSettings
from typing import Literal

class Config(BaseSettings):
    # Existing config...
    
    # Vector store backend selection
    vector_backend: Literal["community", "legacy"] = "community"
    
    # PGVector configuration
    pgvector_collection: str = "hansard"
    
    # Cloud SQL configuration (existing)
    db_name: str
    db_user: str
    instance_connection_name: str
    
    # Optional: database password (if not using IAM)
    db_password: str | None = None
    use_iam_auth: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False

config = Config()
```

#### Step 1.3: Create Cloud SQL Engine Factory

**File**: `src/storage/cloud_sql_engine.py`

```python
"""Cloud SQL SQLAlchemy engine factory with IAM authentication."""

import logging
from typing import Optional
from sqlalchemy import create_engine, Engine
from sqlalchemy.pool import NullPool
from google.cloud.sql.connector import Connector
import pg8000

logger = logging.getLogger(__name__)


def create_cloud_sql_engine(
    instance_connection_name: str,
    database: str,
    user: str,
    password: Optional[str] = None,
    enable_iam_auth: bool = True,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_timeout: int = 30,
) -> Engine:
    """
    Create a SQLAlchemy engine for Cloud SQL PostgreSQL.
    
    Args:
        instance_connection_name: Format 'project:region:instance'
        database: Database name
        user: Database user (email for IAM auth)
        password: Database password (None for IAM auth)
        enable_iam_auth: Use IAM authentication
        pool_size: Connection pool size
        max_overflow: Maximum overflow connections
        pool_timeout: Pool timeout in seconds
    
    Returns:
        SQLAlchemy engine connected to Cloud SQL
    
    Example:
        >>> engine = create_cloud_sql_engine(
        ...     instance_connection_name="my-project:us-central1:my-instance",
        ...     database="hansard-db-v2",
        ...     user="service-account@project.iam",
        ...     enable_iam_auth=True,
        ... )
    """
    connector = Connector()
    
    def getconn() -> pg8000.dbapi.Connection:
        """Create a connection to Cloud SQL."""
        conn_kwargs = {
            "user": user,
            "db": database,
        }
        
        if enable_iam_auth:
            conn_kwargs["enable_iam_auth"] = True
            logger.info(f"Connecting to Cloud SQL with IAM auth: {instance_connection_name}")
        else:
            if not password:
                raise ValueError("Password required when IAM auth is disabled")
            conn_kwargs["password"] = password
            logger.info(f"Connecting to Cloud SQL with password auth: {instance_connection_name}")
        
        return connector.connect(
            instance_connection_name,
            "pg8000",
            **conn_kwargs,
        )
    
    # Create SQLAlchemy engine
    engine = create_engine(
        "postgresql+pg8000://",
        creator=getconn,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_pre_ping=True,  # Verify connections before using
        echo=False,  # Set to True for SQL debugging
    )
    
    logger.info(f"Created Cloud SQL engine for {database}")
    return engine


def create_cloud_sql_engine_from_config(config) -> Engine:
    """
    Create Cloud SQL engine from application config.
    
    Args:
        config: Application configuration object
    
    Returns:
        SQLAlchemy engine
    """
    return create_cloud_sql_engine(
        instance_connection_name=config.instance_connection_name,
        database=config.db_name,
        user=config.db_user,
        password=config.db_password,
        enable_iam_auth=config.use_iam_auth,
    )
```

### Phase 2: Vector Store Adapter

#### Step 2.1: Create PGVector Adapter

**File**: `src/storage/community_vector_store.py`

```python
"""Community PGVector adapter with async support."""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import Engine
from langchain_community.vectorstores import PGVector
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class CommunityVectorStoreAdapter:
    """
    Async wrapper for langchain-community PGVector.
    
    Provides async API compatibility with VectorStoreService
    by running sync PGVector operations in thread pool.
    """
    
    def __init__(
        self,
        embeddings: Embeddings,
        engine: Engine,
        collection_name: str = "hansard",
        distance_strategy: str = "cosine",
    ):
        """
        Initialize PGVector adapter.
        
        Args:
            embeddings: LangChain embeddings model
            engine: SQLAlchemy engine
            collection_name: Name of the collection
            distance_strategy: Distance strategy ('cosine', 'euclidean', 'inner_product')
        """
        self.embeddings = embeddings
        self.engine = engine
        self.collection_name = collection_name
        self.distance_strategy = distance_strategy
        
        # Connection string from engine
        connection_string = str(engine.url).replace(
            "postgresql+pg8000://",
            "postgresql://"
        )
        
        # Initialize PGVector store
        self.vector_store = PGVector(
            collection_name=collection_name,
            connection_string=connection_string,
            embeddings=embeddings,
            distance_strategy=distance_strategy,
            engine=engine,
        )
        
        logger.info(
            f"Initialized PGVector adapter: collection={collection_name}, "
            f"strategy={distance_strategy}"
        )
    
    async def aadd_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Add texts to vector store (async).
        
        Args:
            texts: List of text chunks
            metadatas: Optional list of metadata dicts
            ids: Optional list of IDs
        
        Returns:
            List of inserted IDs
        """
        logger.debug(f"Adding {len(texts)} texts to PGVector")
        
        # Run sync operation in thread pool
        return await asyncio.to_thread(
            self.vector_store.add_texts,
            texts=texts,
            metadatas=metadatas,
            ids=ids,
        )
    
    async def asimilarity_search_with_score(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Document, float]]:
        """
        Search for similar documents (async).
        
        Args:
            query: Search query
            k: Number of results
            filter: Optional metadata filter
        
        Returns:
            List of (Document, score) tuples
        """
        logger.debug(f"Searching PGVector: query={query[:50]}..., k={k}, filter={filter}")
        
        # Run sync operation in thread pool
        return await asyncio.to_thread(
            self.vector_store.similarity_search_with_score,
            query=query,
            k=k,
            filter=filter,
        )
    
    async def adelete(
        self,
        ids: Optional[List[str]] = None,
        filter: Optional[Dict[str, Any]] = None,
    ) -> Optional[bool]:
        """
        Delete documents (async).
        
        Args:
            ids: Optional list of IDs to delete
            filter: Optional metadata filter
        
        Returns:
            Success boolean
        """
        if not ids and not filter:
            raise ValueError("Must provide either ids or filter for deletion")
        
        logger.debug(f"Deleting from PGVector: ids={ids}, filter={filter}")
        
        # Run sync operation in thread pool
        return await asyncio.to_thread(
            self.vector_store.delete,
            ids=ids,
            filter=filter,
        )
    
    async def adelete_by_metadata(
        self,
        filter: Dict[str, Any],
    ) -> int:
        """
        Delete documents by metadata filter (async).
        
        Args:
            filter: Metadata filter dict
        
        Returns:
            Number of documents deleted
        """
        logger.debug(f"Deleting by metadata: filter={filter}")
        
        # PGVector delete returns None/bool, so we query first to count
        # Search to get matching docs
        results = await asyncio.to_thread(
            self.vector_store.similarity_search,
            query="",  # Dummy query
            k=10000,  # Large number to get all matches
            filter=filter,
        )
        
        if not results:
            return 0
        
        # Extract IDs
        ids = [doc.metadata.get("id") for doc in results if "id" in doc.metadata]
        
        if ids:
            await self.adelete(ids=ids)
        
        return len(ids)
```

#### Step 2.2: Update VectorStoreService

**File**: `src/storage/vector_store.py`

Add backend selection logic:

```python
"""Vector store service with backend selection."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_core.documents import Document

from src.config import config
from src.storage.cloud_sql_engine import create_cloud_sql_engine_from_config
from src.storage.community_vector_store import CommunityVectorStoreAdapter

logger = logging.getLogger(__name__)


class VectorStoreService:
    """Vector store service with pluggable backends."""
    
    def __init__(self):
        """Initialize vector store with configured backend."""
        self.backend = config.vector_backend
        self._vector_store = None
        self._embeddings = None
        
        logger.info(f"Initializing VectorStoreService with backend: {self.backend}")
    
    def _get_embeddings(self) -> VertexAIEmbeddings:
        """Get embeddings model (cached)."""
        if self._embeddings is None:
            self._embeddings = VertexAIEmbeddings(
                model_name=config.embedding_model,
                project=config.gcp_project,
                location=config.gcp_location,
            )
            logger.info(f"Initialized VertexAIEmbeddings: {config.embedding_model}")
        
        return self._embeddings
    
    def _get_vector_store(self):
        """Get vector store instance (cached)."""
        if self._vector_store is not None:
            return self._vector_store
        
        embeddings = self._get_embeddings()
        
        if self.backend == "community":
            # Use community PGVector with Cloud SQL engine
            logger.info("Creating community PGVector backend")
            engine = create_cloud_sql_engine_from_config(config)
            self._vector_store = CommunityVectorStoreAdapter(
                embeddings=embeddings,
                engine=engine,
                collection_name=config.pgvector_collection,
            )
        
        elif self.backend == "legacy":
            # Use legacy langchain-google-cloud-sql-pg (if still installed)
            logger.info("Creating legacy Cloud SQL PG backend")
            from langchain_google_cloud_sql_pg import PostgresVectorStore
            # ... legacy initialization code ...
            raise NotImplementedError("Legacy backend for fallback only")
        
        else:
            raise ValueError(f"Unknown vector backend: {self.backend}")
        
        return self._vector_store
    
    async def add_chunks(
        self,
        chunks: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Add document chunks to vector store.
        
        Args:
            chunks: List of chunk dicts with 'text' and 'metadata'
        
        Returns:
            List of chunk IDs
        """
        vector_store = self._get_vector_store()
        
        texts = [chunk["text"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]
        ids = [chunk.get("id") for chunk in chunks]
        
        return await vector_store.aadd_texts(
            texts=texts,
            metadatas=metadatas,
            ids=ids,
        )
    
    async def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Document, float]]:
        """
        Search for similar documents.
        
        Args:
            query: Search query
            k: Number of results
            filter: Optional metadata filter
        
        Returns:
            List of (Document, score) tuples
        """
        vector_store = self._get_vector_store()
        
        return await vector_store.asimilarity_search_with_score(
            query=query,
            k=k,
            filter=filter,
        )
    
    async def delete_by_speech_id(
        self,
        speech_id: str,
    ) -> int:
        """
        Delete all chunks for a speech.
        
        Args:
            speech_id: Speech ID to delete
        
        Returns:
            Number of chunks deleted
        """
        vector_store = self._get_vector_store()
        
        return await vector_store.adelete_by_metadata(
            filter={"speech_id": speech_id}
        )


# Global instance
vector_store_service = VectorStoreService()
```

### Phase 3: Data Migration

#### Step 3.1: Create Migration Script

**File**: `scripts/migrate_to_pgvector_schema.py`

```python
"""
Migrate data from legacy table to PGVector standard schema.

Usage:
    python scripts/migrate_to_pgvector_schema.py --dry-run
    python scripts/migrate_to_pgvector_schema.py --execute
"""

import asyncio
import argparse
import logging
from typing import List, Dict, Any
from sqlalchemy import text, select
from tqdm import tqdm

from src.config import config
from src.storage.cloud_sql_engine import create_cloud_sql_engine_from_config
from src.storage.vector_store import vector_store_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fetch_legacy_data(engine, batch_size: int = 100) -> List[Dict[str, Any]]:
    """Fetch data from legacy table."""
    logger.info("Fetching data from legacy table: hansard_speeches")
    
    query = text("""
        SELECT 
            chunk_id,
            chunk_text,
            embedding,
            metadata
        FROM hansard_speeches
        ORDER BY chunk_id
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query)
        rows = result.fetchall()
    
    logger.info(f"Fetched {len(rows)} rows from legacy table")
    
    chunks = []
    for row in rows:
        chunks.append({
            "id": row.chunk_id,
            "text": row.chunk_text,
            "metadata": row.metadata or {},
        })
    
    return chunks


async def migrate_data(dry_run: bool = True, batch_size: int = 100):
    """Migrate data to PGVector schema."""
    logger.info(f"Starting migration (dry_run={dry_run})")
    
    # Create engine for reading legacy data
    engine = create_cloud_sql_engine_from_config(config)
    
    # Fetch legacy data
    chunks = await fetch_legacy_data(engine, batch_size)
    
    if not chunks:
        logger.warning("No data found in legacy table")
        return
    
    logger.info(f"Total chunks to migrate: {len(chunks)}")
    
    if dry_run:
        logger.info("DRY RUN - No data will be written")
        logger.info(f"Sample chunk: {chunks[0]}")
        return
    
    # Migrate in batches
    logger.info("Migrating data to PGVector...")
    
    for i in tqdm(range(0, len(chunks), batch_size), desc="Migrating batches"):
        batch = chunks[i:i + batch_size]
        
        try:
            ids = await vector_store_service.add_chunks(batch)
            logger.debug(f"Migrated batch {i//batch_size + 1}: {len(ids)} chunks")
        except Exception as e:
            logger.error(f"Error migrating batch {i//batch_size + 1}: {e}")
            raise
    
    logger.info(f"Migration complete: {len(chunks)} chunks migrated")
    
    # Validation
    logger.info("Validating migration...")
    await validate_migration(engine, len(chunks))


async def validate_migration(engine, expected_count: int):
    """Validate migration was successful."""
    query = text("""
        SELECT COUNT(*) as count
        FROM langchain_pg_embedding
        WHERE collection_id = (
            SELECT uuid 
            FROM langchain_pg_collection 
            WHERE name = :collection_name
        )
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {"collection_name": config.pgvector_collection})
        row = result.fetchone()
        actual_count = row.count if row else 0
    
    logger.info(f"Validation: Expected {expected_count}, Found {actual_count}")
    
    if actual_count == expected_count:
        logger.info("✅ Validation passed")
    else:
        logger.error(f"❌ Validation failed: count mismatch")
        raise ValueError(f"Migration validation failed: {actual_count} != {expected_count}")


def main():
    parser = argparse.ArgumentParser(description="Migrate to PGVector schema")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migration without writing data",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute migration (writes data)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for migration (default: 100)",
    )
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.execute:
        parser.error("Must specify either --dry-run or --execute")
    
    asyncio.run(migrate_data(
        dry_run=args.dry_run,
        batch_size=args.batch_size,
    ))


if __name__ == "__main__":
    main()
```

### Phase 4: Testing

#### Step 4.1: Unit Tests

**File**: `tests/unit/storage/test_community_vector_store.py`

```python
"""Unit tests for community vector store adapter."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.storage.community_vector_store import CommunityVectorStoreAdapter


@pytest.fixture
def mock_embeddings():
    """Mock embeddings model."""
    embeddings = Mock()
    embeddings.embed_query = Mock(return_value=[0.1] * 768)
    embeddings.embed_documents = Mock(return_value=[[0.1] * 768])
    return embeddings


@pytest.fixture
def mock_engine():
    """Mock SQLAlchemy engine."""
    engine = Mock()
    engine.url = "postgresql+pg8000://user@host/db"
    return engine


@pytest.mark.asyncio
async def test_add_texts(mock_embeddings, mock_engine):
    """Test adding texts to vector store."""
    with patch("src.storage.community_vector_store.PGVector") as mock_pgvector:
        # Setup mock
        mock_store = Mock()
        mock_store.add_texts = Mock(return_value=["id1", "id2"])
        mock_pgvector.return_value = mock_store
        
        # Create adapter
        adapter = CommunityVectorStoreAdapter(
            embeddings=mock_embeddings,
            engine=mock_engine,
            collection_name="test",
        )
        
        # Test
        ids = await adapter.aadd_texts(
            texts=["text1", "text2"],
            metadatas=[{"key": "value1"}, {"key": "value2"}],
        )
        
        assert ids == ["id1", "id2"]
        mock_store.add_texts.assert_called_once()


@pytest.mark.asyncio
async def test_similarity_search(mock_embeddings, mock_engine):
    """Test similarity search."""
    with patch("src.storage.community_vector_store.PGVector") as mock_pgvector:
        # Setup mock
        from langchain_core.documents import Document
        mock_store = Mock()
        mock_store.similarity_search_with_score = Mock(return_value=[
            (Document(page_content="text1", metadata={"id": "1"}), 0.9),
            (Document(page_content="text2", metadata={"id": "2"}), 0.8),
        ])
        mock_pgvector.return_value = mock_store
        
        # Create adapter
        adapter = CommunityVectorStoreAdapter(
            embeddings=mock_embeddings,
            engine=mock_engine,
            collection_name="test",
        )
        
        # Test
        results = await adapter.asimilarity_search_with_score(
            query="test query",
            k=2,
            filter={"speech_id": "speech1"},
        )
        
        assert len(results) == 2
        assert results[0][1] == 0.9
        mock_store.similarity_search_with_score.assert_called_once()
```

#### Step 4.2: Integration Tests

**File**: `tests/integration/storage/test_pgvector_integration.py`

```python
"""Integration tests for PGVector with Cloud SQL."""

import pytest
import os
from src.storage.vector_store import VectorStoreService
from src.config import config

# Skip if not in integration test environment
pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION_TESTS"),
    reason="Integration tests only run with RUN_INTEGRATION_TESTS=1",
)


@pytest.fixture
async def vector_service():
    """Create vector store service."""
    # Ensure using community backend
    config.vector_backend = "community"
    service = VectorStoreService()
    yield service


@pytest.mark.asyncio
async def test_add_and_search(vector_service):
    """Test adding and searching documents."""
    # Add test chunks
    chunks = [
        {
            "id": "test1",
            "text": "This is a test document about climate change.",
            "metadata": {"speech_id": "speech1", "type": "test"},
        },
        {
            "id": "test2",
            "text": "Another document discussing renewable energy.",
            "metadata": {"speech_id": "speech1", "type": "test"},
        },
    ]
    
    ids = await vector_service.add_chunks(chunks)
    assert len(ids) == 2
    
    # Search
    results = await vector_service.similarity_search(
        query="climate change",
        k=2,
        filter={"type": "test"},
    )
    
    assert len(results) > 0
    assert results[0][1] > 0.5  # Should have decent score
    
    # Cleanup
    deleted = await vector_service.delete_by_speech_id("speech1")
    assert deleted == 2
```

## Deployment

### Step 5.1: Deploy to Staging

```bash
# Build and deploy
gcloud builds submit --config cloudbuild.yaml

# Set environment variable
gcloud run services update hansard-mcp-service \
    --set-env-vars VECTOR_BACKEND=community \
    --region us-central1

# Run migration
python scripts/migrate_to_pgvector_schema.py --execute

# Test deployment
curl https://hansard-mcp-service-xxx.run.app/health
```

### Step 5.2: Production Rollout

```bash
# Deploy with feature flag (community backend)
gcloud run deploy hansard-mcp-service \
    --image gcr.io/PROJECT/hansard-mcp-service:TAG \
    --set-env-vars VECTOR_BACKEND=community

# Monitor logs
gcloud logging read "resource.type=cloud_run_revision" --limit 100

# If issues, rollback
gcloud run services update hansard-mcp-service \
    --set-env-vars VECTOR_BACKEND=legacy
```

## Validation Checklist

- [ ] Dependencies updated and locked
- [ ] Cloud SQL engine creates connections successfully
- [ ] IAM authentication works
- [ ] PGVector adapter passes unit tests
- [ ] Integration tests pass with dev database
- [ ] Data migration script runs successfully (dry-run)
- [ ] Data migration executed and validated
- [ ] Search results match baseline
- [ ] Performance meets requirements
- [ ] Staging deployment successful
- [ ] Production deployment successful
- [ ] Documentation updated

## Troubleshooting

### Issue: Connection Errors

**Symptom**: `Error connecting to Cloud SQL`

**Solution**:
- Verify `INSTANCE_CONNECTION_NAME` is correct
- Check IAM permissions for service account
- Ensure Cloud SQL Admin API is enabled
- Test with `gcloud sql connect`

### Issue: Embedding Errors

**Symptom**: `Error generating embeddings`

**Solution**:
- Verify Vertex AI API is enabled
- Check service account has Vertex AI permissions
- Confirm model name is correct: `text-embedding-005`

### Issue: Migration Fails

**Symptom**: `Migration validation failed`

**Solution**:
- Check legacy table exists and has data
- Verify PGVector tables were created
- Check for constraint violations in data
- Review migration logs for specific errors

### Issue: Slow Performance

**Symptom**: Search taking too long

**Solution**:
- Check connection pool settings
- Verify pgvector indexes are created
- Consider increasing pool size
- Profile with `EXPLAIN ANALYZE`

## Next Steps

After successful deployment:

1. Monitor for 24-48 hours
2. Compare performance metrics with baseline
3. Remove legacy backend code
4. Remove `VECTOR_BACKEND` feature flag
5. Update all documentation
6. Close Feature 015

## References

- [SQLAlchemy Engine Configuration](https://docs.sqlalchemy.org/en/20/core/engines.html)
- [Cloud SQL Python Connector](https://github.com/GoogleCloudPlatform/cloud-sql-python-connector)
- [LangChain PGVector](https://python.langchain.com/docs/integrations/vectorstores/pgvector)
- [pgvector Extension](https://github.com/pgvector/pgvector)
