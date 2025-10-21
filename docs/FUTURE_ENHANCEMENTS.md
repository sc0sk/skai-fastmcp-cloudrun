# Future Enhancements

## Embedding Model Upgrades

### gemini-embedding-001 @ 1536 Dimensions

**Status**: Deferred to v2
**Priority**: Medium
**Effort**: 2-3 days

**Rationale**:
- Current: text-embedding-005 @ 768 dims (working, production-ready)
- Upgrade: gemini-embedding-001 @ 1536 dims (2x better quality, still within pgvector HNSW limit)

**Benefits**:
1. Higher quality semantic search (1536 vs 768 dimensions)
2. Better recall on complex parliamentary language
3. Still well within pgvector HNSW limit (2000 dimensions max)

**Challenges Encountered (Oct 2025)**:
- LangChain's `VertexAIEmbeddings` doesn't support `dimensions` parameter in async methods
- `aembed_documents()` and `aembed_query()` don't accept dimensionality configuration
- Only sync `embed()` method supports dimensions, but PostgresVectorStore doesn't use it

**Proposed Solution**:
1. Create custom `GeminiEmbeddingsWrapper` that uses native Vertex AI SDK
2. Implement sync `embed_documents()` and `embed_query()` methods
3. Configure with `output_dimensionality=1536`
4. Update database schema:
   ```sql
   ALTER TABLE speech_chunks
   ALTER COLUMN embedding TYPE vector(1536);

   DROP INDEX speech_chunks_embedding_idx;
   CREATE INDEX speech_chunks_embedding_idx
   ON speech_chunks
   USING hnsw (embedding vector_cosine_ops)
   WITH (m = 24, ef_construction = 100);
   ```
5. Re-ingest all speeches with new embeddings

**Implementation Reference**:
```python
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput

class GeminiEmbeddingsWrapper:
    """LangChain-compatible wrapper for gemini-embedding-001 @ 1536 dims."""

    def __init__(self, project_id, location, output_dimensionality=1536):
        self.model = TextEmbeddingModel.from_pretrained("gemini-embedding-001")
        self.output_dimensionality = output_dimensionality

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        inputs = [TextEmbeddingInput(text=t, task_type="RETRIEVAL_DOCUMENT") for t in texts]
        embeddings = self.model.get_embeddings(inputs, output_dimensionality=self.output_dimensionality)
        return [e.values for e in embeddings]

    def embed_query(self, text: str) -> List[float]:
        inputs = [TextEmbeddingInput(text=text, task_type="RETRIEVAL_QUERY")]
        embeddings = self.model.get_embeddings(inputs, output_dimensionality=self.output_dimensionality)
        return embeddings[0].values
```

**Cost Impact**:
- Storage: 2x (1536 vs 768 floats per vector)
- Search latency: ~10-20% slower
- API costs: Same (Vertex AI pricing is per character, not dimension)

**Testing Plan**:
1. Create test instance with 1536-dim schema
2. Ingest sample speeches (n=10)
3. Compare search quality vs 768-dim baseline
4. Benchmark query latency
5. Validate HNSW index performance

**Decision Criteria**:
- Proceed if search quality improvement > 15%
- Proceed if latency increase < 50ms (p95)
- Defer if LangChain adds native dimensionality support

---

## Other Enhancements

### Multi-language Support
- **Model**: text-multilingual-embedding-002 @ 768 dims
- **Use Case**: Non-English parliamentary transcripts
- **Effort**: 1 week

### AlloyDB Migration
- **Upgrade Path**: Cloud SQL → AlloyDB for >100K speeches
- **Benefits**: ScaNN index, better out-of-memory performance
- **Cost**: $200+/month vs $10-20/month current
- **Trigger**: Dataset exceeds 100K speeches or consistent OOM errors
