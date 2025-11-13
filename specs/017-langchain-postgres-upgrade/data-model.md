# Data Model: langchain-postgres Schema Adoption

## Target Tables (managed by langchain-postgres)

- `langchain_pg_collection`
  - uuid (PK)
  - name (UNIQUE)
  - cmetadata (JSONB)

- `langchain_pg_embedding`
  - uuid (PK)
  - collection_id (FK → langchain_pg_collection.uuid)
  - embedding (VECTOR[N])
  - document (TEXT)
  - cmetadata (JSONB)
  - custom_id (VARCHAR)

- `langchain_pg_embedding_collection`
  - embedding_id (FK)
  - collection_id (FK)
  - PRIMARY KEY (embedding_id, collection_id)

Indexes:
- IVFFlat on `embedding` with cosine ops (lists configurable)

## Source → Target Mapping

- Source table: `hansard_speeches` or `speech_chunks` (current)

| Source Column       | Target Column                            |
|---------------------|------------------------------------------|
| chunk_id            | langchain_pg_embedding.custom_id          |
| chunk_text          | langchain_pg_embedding.document           |
| embedding           | langchain_pg_embedding.embedding          |
| metadata (JSON/JSONB)| langchain_pg_embedding.cmetadata        |
| (derived)           | langchain_pg_collection.name = "hansard" |

## Constraints & Invariants

- custom_id maintained equal to original `chunk_id`
- All records assigned to the single collection `hansard` (configurable)
- Metadata must be valid JSON serializable (JSONB)
- Embedding dimensions must match the embeddings model used

## Migration Validation

- Record count parity between source and target
- Random sample spot-check (10 records): content + metadata equality
- Similarity search parity on a sample of queries

## Notes

- `langchain-postgres` manages table creation; migration script should ensure collection exists
- Consider ANALYZE after bulk insert to optimize query plans
