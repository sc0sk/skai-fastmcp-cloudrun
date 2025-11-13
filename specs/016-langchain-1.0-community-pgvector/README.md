# Feature 015: Upgrade to LangChain 1.0 with Community PGVector

**Status**: Planning  
**Created**: 2025-10-25  
**Priority**: High  
**Dependencies**: None (replaces Feature 014)

## Overview

Upgrade to LangChain 1.0+ by replacing the blocking `langchain-google-cloud-sql-pg` dependency with `langchain-community` PGVector. The langchain-google packages (langchain-google-vertexai, langchain-google-genai, langchain-google-community) already support LangChain 1.0, so only the vector store needs replacement.

## Problem Statement

- Current blocker: `langchain-google-cloud-sql-pg` v0.14.1 requires `langchain-core<1.0.0`
- Need to upgrade to LangChain 1.0+ for modern features and ecosystem compatibility
- Want to maintain Cloud SQL PostgreSQL with pgvector for vector storage
- Must preserve existing functionality: IAM auth, async APIs, metadata filtering

## Solution

Replace `langchain-google-cloud-sql-pg` with `langchain-community.vectorstores.PGVector` while using `google-cloud-sql-connector` for Cloud SQL connectivity. This unblocks LangChain 1.0 upgrade while maintaining all required functionality.

### Key Benefits

1. **Unblocks LangChain 1.0**: All langchain-google packages support 1.0, only vector store wrapper was blocking
2. **Standard LangChain patterns**: Uses official langchain-community PGVector implementation
3. **Maintains Cloud SQL**: Cloud SQL Python Connector provides IAM auth and connection management
4. **Preserves functionality**: Async wrappers, metadata filtering, and embedding integration maintained
5. **Future-proof**: Not dependent on third-party wrapper for LangChain compatibility

## Technical Approach

### Architecture

```
Application Layer (async)
    ↓
VectorStoreService (async wrapper via asyncio.to_thread)
    ↓
langchain-community PGVector (sync)
    ↓
SQLAlchemy Engine
    ↓
google-cloud-sql-connector (IAM auth)
    ↓
Cloud SQL PostgreSQL + pgvector
```

### Dependencies

**Add:**
- `langchain>=1.0.0` (core framework)
- `langchain-community>=0.3.0` (PGVector implementation)
- `langchain-google-vertexai>=2.0.0` (embeddings - already 1.0 compatible)
- `langchain-google-genai>=2.0.0` (optional - already 1.0 compatible)
- `sqlalchemy>=2.0.0` (database engine)
- `pg8000>=1.30.0` (PostgreSQL driver)
- `pgvector>=0.3.0` (vector type support)
- `google-cloud-sql-connector>=1.11.0` (Cloud SQL IAM auth)

**Remove:**
- `langchain-google-cloud-sql-pg` (blocks at <1.0.0)

### Implementation Plan

#### Phase 1: Foundation (Days 1-2)

1. **Update dependencies**
   - Add LangChain 1.0+ packages to `pyproject.toml`
   - Remove `langchain-google-cloud-sql-pg`
   - Run `uv lock` and verify no conflicts
   
2. **Create Cloud SQL engine factory**
   - File: `src/storage/cloud_sql_engine.py`
   - Function: `create_cloud_sql_engine()`
   - Support IAM auth and password auth
   - Use Cloud SQL Python Connector
   - Return SQLAlchemy engine

3. **Add feature flag**
   - Environment variable: `VECTOR_BACKEND=community|legacy`
   - Default: `community` (new implementation)
   - Config: `src/config.py`

#### Phase 2: Vector Store Adapter (Days 3-4)

4. **Create PGVector adapter**
   - File: `src/storage/community_vector_store.py`
   - Class: `CommunityVectorStoreAdapter`
   - Wrap `langchain-community.vectorstores.PGVector`
   - Provide async methods via `asyncio.to_thread`
   
5. **Update VectorStoreService**
   - File: `src/storage/vector_store.py`
   - Add backend selection based on `VECTOR_BACKEND`
   - Preserve public async API
   - Use `VertexAIEmbeddings` (LangChain 1.0 compatible)

6. **Schema migration script**
   - File: `scripts/migrate_to_pgvector_schema.py`
   - Migrate from custom table to PGVector standard tables
   - Tables: `langchain_pg_collection`, `langchain_pg_embedding`
   - Use `collection_name='hansard'`
   - Preserve chunk IDs and metadata

#### Phase 3: Testing & Validation (Day 5)

7. **Unit tests**
   - Test async wrappers
   - Test metadata filtering
   - Mock database operations
   
8. **Integration tests**
   - Test against dev Cloud SQL instance
   - Verify IAM auth works
   - Test add/search/delete operations
   - Compare results with legacy backend

9. **Data migration**
   - Run migration script on dev database
   - Validate record counts match
   - Spot-check search results for parity

#### Phase 4: Deployment (Day 6)

10. **Deploy to staging**
    - Deploy with `VECTOR_BACKEND=community`
    - Run E2E tests (ingest + search)
    - Performance baseline

11. **Production rollout**
    - Deploy with feature flag
    - Monitor for errors
    - Gradual rollout if needed

12. **Cleanup**
    - Remove legacy backend code
    - Remove `VECTOR_BACKEND` flag
    - Update documentation

## File Changes

### New Files

- `specs/015-langchain-1.0-community-pgvector/README.md` (this file)
- `specs/015-langchain-1.0-community-pgvector/IMPLEMENTATION.md` (detailed steps)
- `src/storage/cloud_sql_engine.py` (SQLAlchemy engine factory)
- `src/storage/community_vector_store.py` (PGVector adapter)
- `scripts/migrate_to_pgvector_schema.py` (data migration)
- `tests/unit/storage/test_community_vector_store.py` (unit tests)
- `tests/integration/storage/test_pgvector_integration.py` (integration tests)

### Modified Files

- `pyproject.toml` (dependencies)
- `src/config.py` (add `VECTOR_BACKEND` config)
- `src/storage/vector_store.py` (add backend selection)
- `.github/copilot-instructions.md` (update tech stack)

### Removed Files (after cleanup)

- None initially (keep legacy code during transition)
- After validation: remove legacy backend code from `vector_store.py`

## Configuration

### Environment Variables

```bash
# Vector store backend selection (during migration)
VECTOR_BACKEND=community  # or 'legacy' for rollback

# Existing Cloud SQL variables (unchanged)
DB_NAME=hansard-db-v2
DB_USER=hansard-mcp-service@...
INSTANCE_CONNECTION_NAME=project:region:instance

# PGVector collection name
PGVECTOR_COLLECTION=hansard
```

### Cloud SQL Connection

```python
from google.cloud.sql.connector import Connector
from sqlalchemy import create_engine

connector = Connector()

def getconn():
    return connector.connect(
        instance_connection_name,
        "pg8000",
        user=db_user,
        db=db_name,
        enable_iam_auth=True,
    )

engine = create_engine(
    "postgresql+pg8000://",
    creator=getconn,
)
```

## Migration Strategy

### Data Migration

1. **Create PGVector tables** (automatic on first use)
2. **ETL script** to copy data from existing table:
   ```sql
   -- Read from existing table
   SELECT chunk_id, chunk_text, embedding, metadata 
   FROM hansard_speeches;
   
   -- Insert via PGVector API
   vector_store.add_texts(
       texts=[chunk_text],
       metadatas=[metadata],
       ids=[chunk_id]
   )
   ```
3. **Validation**: Compare counts, spot-check search results

### Rollback Plan

- Set `VECTOR_BACKEND=legacy` to revert instantly
- Keep legacy code until production validated
- Legacy backend can read old table structure

## Testing Strategy

### Unit Tests

- Mock database connections
- Test async wrappers
- Test metadata filtering
- Test error handling

### Integration Tests

- Test against dev Cloud SQL
- Verify IAM authentication
- Test CRUD operations
- Test metadata filters
- Performance benchmarks

### E2E Tests

- Ingest test documents
- Search with various queries
- Verify metadata filtering
- Compare with baseline results

## Success Criteria

- [ ] All dependencies upgraded to LangChain 1.0+
- [ ] All existing tests pass with new backend
- [ ] Search results match legacy backend (spot checks)
- [ ] IAM authentication works with Cloud SQL
- [ ] Async API preserved
- [ ] Metadata filtering works correctly
- [ ] Data migration completed successfully
- [ ] Performance meets or exceeds baseline
- [ ] Documentation updated

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Schema incompatibility | High | Low | Feature flag allows instant rollback |
| Performance degradation | Medium | Low | Benchmark and tune; use connection pooling |
| Data migration errors | High | Low | Validate counts; spot-check results; dry-run first |
| Async wrapper overhead | Low | Medium | Use asyncio.to_thread; batch operations |
| Loss of custom features | Medium | Low | Standard PGVector features cover needs |

## Timeline

- **Day 1-2**: Dependencies + Cloud SQL engine + feature flag
- **Day 3-4**: PGVector adapter + VectorStoreService updates + migration script
- **Day 5**: Testing + data migration
- **Day 6**: Deployment + validation + cleanup

**Total: ~6 days** (1.5 sprints)

## References

- [LangChain 1.0 Release Notes](https://blog.langchain.dev/langchain-v0-1-0/)
- [langchain-community PGVector](https://python.langchain.com/docs/integrations/vectorstores/pgvector)
- [Cloud SQL Python Connector](https://github.com/GoogleCloudPlatform/cloud-sql-python-connector)
- [langchain-google-vertexai](https://github.com/langchain-ai/langchain-google) - LangChain 1.0 compatible
- Previous planning: `specs/014-update-langchain-1-0/` (superseded)

## Notes

- langchain-google packages (vertexai, genai, community) already support LangChain 1.0
- Only the vector store wrapper (langchain-google-cloud-sql-pg) was blocking
- This approach is cleaner than forking the wrapper
- Standard LangChain patterns are more maintainable long-term
- Feature flag provides safe rollback during transition
