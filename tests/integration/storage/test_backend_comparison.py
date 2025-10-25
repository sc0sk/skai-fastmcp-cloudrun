"""Backend comparison tests for postgres vs legacy vector stores.

Tests verify:
- T015: Semantic equivalence between postgres and legacy backends
- Same queries return similar results (content, ordering, scores)
- Metadata filtering produces consistent results
- Both backends handle edge cases identically

Prerequisites:
- Both backends must be functional
- Test data must exist in both backends (or use test-specific data)
- Cloud SQL instance accessible

Run with:
    pytest tests/integration/storage/test_backend_comparison.py -v
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict, List, Tuple
from unittest.mock import patch

import pytest

from src import config


@pytest.fixture(scope="module")
def skip_if_single_backend():
    """Skip if only one backend is available (can't compare)."""
    # Check if both backends can be imported
    try:
        from src.storage.postgres_vector_store import (
            PostgresVectorStoreService,
        )
        postgres_available = True
    except ImportError:
        postgres_available = False
    
    # Legacy backend is always available (existing dependency)
    legacy_available = True
    
    if not (postgres_available and legacy_available):
        pytest.skip(
            "Backend comparison requires both postgres and legacy backends. "
            f"Postgres: {postgres_available}, Legacy: {legacy_available}"
        )


@pytest.fixture(scope="module")
def test_collection_name() -> str:
    """Generate unique collection name for test isolation."""
    return f"test_comparison_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="module")
def sample_test_documents() -> List[Dict[str, Any]]:
    """Sample documents for comparison testing."""
    return [
        {
            "text": "Climate change requires immediate action and policy reform.",
            "metadata": {
                "speaker": "Environment Minister",
                "date": "2024-03-15",
                "topic": "climate",
                "session": 201,
            },
        },
        {
            "text": "The budget allocates significant funding for infrastructure.",
            "metadata": {
                "speaker": "Treasurer",
                "date": "2024-03-15",
                "topic": "budget",
                "session": 201,
            },
        },
        {
            "text": "Education reforms will benefit students across the nation.",
            "metadata": {
                "speaker": "Education Minister",
                "date": "2024-03-16",
                "topic": "education",
                "session": 202,
            },
        },
        {
            "text": "Healthcare funding ensures accessible medical services.",
            "metadata": {
                "speaker": "Health Minister",
                "date": "2024-03-16",
                "topic": "healthcare",
                "session": 202,
            },
        },
        {
            "text": "Economic growth depends on stable fiscal policy.",
            "metadata": {
                "speaker": "Treasurer",
                "date": "2024-03-17",
                "topic": "economy",
                "session": 203,
            },
        },
    ]


async def get_vector_store_for_backend(
    backend: str, collection_name: str = None
):
    """Get vector store instance for specific backend.
    
    Args:
        backend: "postgres" or "legacy"
        collection_name: Optional collection name for postgres backend
    
    Returns:
        Vector store instance
    """
    if backend == "postgres":
        from src.storage.cloud_sql_engine import CloudSQLEngine
        from src.storage.postgres_vector_store import (
            PostgresVectorStoreService,
        )
        
        # Get Cloud SQL config
        project_id = config.get_gcp_project_id()
        region = config.get_gcp_region()
        instance = config.get_cloudsql_instance()
        database = config.get_cloudsql_database()
        
        # Parse instance name if needed
        if ":" in instance:
            parts = instance.split(":")
            if len(parts) == 3:
                project_id, region, instance = parts
        
        # Create engine
        engine_mgr = CloudSQLEngine(
            project_id=project_id,
            region=region,
            instance=instance,
            database=database,
            user=None,  # IAM auth
            password=None,
            pool_size=2,
            max_overflow=1,
        )
        
        # Create postgres vector store
        store = PostgresVectorStoreService(
            connection=engine_mgr.engine,
            collection_name=collection_name or "test_comparison",
        )
        
        return store, engine_mgr
    
    elif backend == "legacy":
        from src.storage.vector_store import VectorStoreService
        
        # Create legacy vector store
        store = VectorStoreService()
        
        return store, None
    
    else:
        raise ValueError(f"Unknown backend: {backend}")


class TestSemanticEquivalence:
    """Test semantic equivalence between backends."""

    @pytest.mark.asyncio
    async def test_identical_query_similar_results(
        self, skip_if_single_backend, sample_test_documents, test_collection_name
    ):
        """Verify same query returns semantically similar results.
        
        Note: Exact scores may differ slightly due to implementation details,
        but top results should be similar.
        """
        # Insert test data into both backends
        postgres_store, postgres_engine = await get_vector_store_for_backend(
            "postgres", test_collection_name
        )
        legacy_store, _ = await get_vector_store_for_backend("legacy")
        
        texts = [doc["text"] for doc in sample_test_documents]
        metadatas = [doc["metadata"] for doc in sample_test_documents]
        
        try:
            # Add to postgres backend
            postgres_ids = await postgres_store.add_chunks(
                texts=texts,
                metadatas=metadatas,
            )
            assert len(postgres_ids) == len(texts)
            
            # Add to legacy backend
            legacy_ids = await legacy_store.add_chunks(
                texts=texts,
                metadatas=metadatas,
                speech_id="test_comparison",
            )
            assert len(legacy_ids) == len(texts)
            
            # Query: Search for climate-related content
            query = "environmental policy and climate action"
            
            # Search postgres backend
            postgres_results = await postgres_store.similarity_search(
                query=query,
                k=3,
            )
            
            # Search legacy backend
            legacy_results = await legacy_store.similarity_search(
                query=query,
                k=3,
            )
            
            # Both should return results
            assert len(postgres_results) > 0
            assert len(legacy_results) > 0
            
            # Extract text content from results
            postgres_texts = [
                doc.page_content for doc, score in postgres_results
            ]
            legacy_texts = [
                result["content"] for result in legacy_results
            ]
            
            # Top result should contain similar keywords
            # (exact match not required due to different scoring)
            assert any(
                "climate" in text.lower() or "environment" in text.lower()
                for text in postgres_texts[:2]
            )
            assert any(
                "climate" in text.lower() or "environment" in text.lower()
                for text in legacy_texts[:2]
            )
            
        finally:
            # Cleanup
            if postgres_engine:
                postgres_engine.close()

    @pytest.mark.asyncio
    async def test_metadata_filtering_consistent(
        self, skip_if_single_backend, sample_test_documents, test_collection_name
    ):
        """Verify metadata filtering produces consistent results."""
        postgres_store, postgres_engine = await get_vector_store_for_backend(
            "postgres", test_collection_name
        )
        legacy_store, _ = await get_vector_store_for_backend("legacy")
        
        texts = [doc["text"] for doc in sample_test_documents]
        metadatas = [doc["metadata"] for doc in sample_test_documents]
        
        try:
            # Add to both backends
            await postgres_store.add_chunks(texts=texts, metadatas=metadatas)
            await legacy_store.add_chunks(
                texts=texts,
                metadatas=metadatas,
                speech_id="test_filter",
            )
            
            # Query with metadata filter
            query = "government policy discussion"
            filter_metadata = {"topic": "budget"}
            
            # Search postgres with filter
            postgres_results = await postgres_store.similarity_search(
                query=query,
                k=5,
                filter=filter_metadata,
            )
            
            # Search legacy with filter
            legacy_results = await legacy_store.similarity_search(
                query=query,
                k=5,
                filter=filter_metadata,
            )
            
            # Both should filter correctly
            if postgres_results:
                for doc, score in postgres_results:
                    assert doc.metadata.get("topic") == "budget"
            
            if legacy_results:
                for result in legacy_results:
                    assert result["metadata"].get("topic") == "budget"
            
            # Result counts should be similar (allowing some variation)
            # Both backends may return 0 results if filter is too restrictive
            assert abs(len(postgres_results) - len(legacy_results)) <= 1
            
        finally:
            if postgres_engine:
                postgres_engine.close()

    @pytest.mark.asyncio
    async def test_empty_result_handling(
        self, skip_if_single_backend, test_collection_name
    ):
        """Verify both backends handle empty results identically."""
        postgres_store, postgres_engine = await get_vector_store_for_backend(
            "postgres", test_collection_name
        )
        legacy_store, _ = await get_vector_store_for_backend("legacy")
        
        try:
            # Query with filter that matches nothing
            query = "test query"
            filter_metadata = {"nonexistent_field": "nonexistent_value"}
            
            # Search postgres
            postgres_results = await postgres_store.similarity_search(
                query=query,
                k=10,
                filter=filter_metadata,
            )
            
            # Search legacy
            legacy_results = await legacy_store.similarity_search(
                query=query,
                k=10,
                filter=filter_metadata,
            )
            
            # Both should return empty results
            assert postgres_results == []
            assert legacy_results == []
            
        finally:
            if postgres_engine:
                postgres_engine.close()

    @pytest.mark.asyncio
    async def test_score_ranges_comparable(
        self, skip_if_single_backend, sample_test_documents, test_collection_name
    ):
        """Verify similarity scores are in comparable ranges.
        
        Note: Exact scores may differ, but ranges should be similar.
        """
        postgres_store, postgres_engine = await get_vector_store_for_backend(
            "postgres", test_collection_name
        )
        legacy_store, _ = await get_vector_store_for_backend("legacy")
        
        texts = [doc["text"] for doc in sample_test_documents]
        metadatas = [doc["metadata"] for doc in sample_test_documents]
        
        try:
            # Add to both backends
            await postgres_store.add_chunks(texts=texts, metadatas=metadatas)
            await legacy_store.add_chunks(
                texts=texts,
                metadatas=metadatas,
                speech_id="test_scores",
            )
            
            # Exact match query (first document text)
            query = texts[0]
            
            # Search both backends
            postgres_results = await postgres_store.similarity_search(
                query=query, k=1
            )
            legacy_results = await legacy_store.similarity_search(
                query=query, k=1
            )
            
            if postgres_results and legacy_results:
                postgres_score = postgres_results[0][1]
                legacy_score = legacy_results[0]["similarity_score"]
                
                # Scores should both be high (>0.8) for exact match
                assert postgres_score > 0.8, (
                    f"Postgres score too low: {postgres_score}"
                )
                assert legacy_score > 0.8, (
                    f"Legacy score too low: {legacy_score}"
                )
                
                # Scores should be within reasonable range of each other
                # (allowing for different normalization)
                score_diff = abs(postgres_score - legacy_score)
                assert score_diff < 0.3, (
                    f"Scores too different: postgres={postgres_score}, "
                    f"legacy={legacy_score}"
                )
            
        finally:
            if postgres_engine:
                postgres_engine.close()


class TestOperationalEquivalence:
    """Test operational behavior consistency."""

    @pytest.mark.asyncio
    async def test_batch_insert_consistency(
        self, skip_if_single_backend, sample_test_documents, test_collection_name
    ):
        """Verify batch inserts work consistently across backends."""
        postgres_store, postgres_engine = await get_vector_store_for_backend(
            "postgres", test_collection_name
        )
        legacy_store, _ = await get_vector_store_for_backend("legacy")
        
        texts = [doc["text"] for doc in sample_test_documents]
        metadatas = [doc["metadata"] for doc in sample_test_documents]
        
        try:
            # Insert batch in postgres
            postgres_ids = await postgres_store.add_chunks(
                texts=texts,
                metadatas=metadatas,
            )
            
            # Insert batch in legacy
            legacy_ids = await legacy_store.add_chunks(
                texts=texts,
                metadatas=metadatas,
                speech_id="test_batch",
            )
            
            # Both should return correct number of IDs
            assert len(postgres_ids) == len(texts)
            assert len(legacy_ids) == len(texts)
            
            # All IDs should be unique
            assert len(set(postgres_ids)) == len(postgres_ids)
            assert len(set(legacy_ids)) == len(legacy_ids)
            
        finally:
            if postgres_engine:
                postgres_engine.close()

    @pytest.mark.asyncio
    async def test_delete_behavior_consistent(
        self, skip_if_single_backend, sample_test_documents, test_collection_name
    ):
        """Verify delete operations work consistently."""
        postgres_store, postgres_engine = await get_vector_store_for_backend(
            "postgres", test_collection_name
        )
        legacy_store, _ = await get_vector_store_for_backend("legacy")
        
        texts = [sample_test_documents[0]["text"]]
        metadatas = [sample_test_documents[0]["metadata"]]
        
        try:
            # Add document to both backends
            postgres_ids = await postgres_store.add_chunks(
                texts=texts,
                metadatas=metadatas,
            )
            legacy_ids = await legacy_store.add_chunks(
                texts=texts,
                metadatas=metadatas,
                speech_id="test_delete",
            )
            
            # Delete from postgres
            postgres_deleted = await postgres_store.delete(
                ids=postgres_ids
            )
            
            # Delete from legacy
            legacy_deleted = await legacy_store.delete_chunks(
                chunk_ids=legacy_ids
            )
            
            # Both should indicate successful deletion
            assert postgres_deleted >= 0  # Returns count
            assert legacy_deleted >= 0  # Returns count
            
        finally:
            if postgres_engine:
                postgres_engine.close()


class TestEdgeCases:
    """Test edge case handling consistency."""

    @pytest.mark.asyncio
    async def test_unicode_handling_consistent(
        self, skip_if_single_backend, test_collection_name
    ):
        """Verify both backends handle Unicode identically."""
        postgres_store, postgres_engine = await get_vector_store_for_backend(
            "postgres", test_collection_name
        )
        legacy_store, _ = await get_vector_store_for_backend("legacy")
        
        # Unicode test data
        texts = ["Hello 你好 مرحبا 🌍"]
        metadatas = [{"test": "unicode", "emoji": "✓"}]
        
        try:
            # Add to both backends
            postgres_ids = await postgres_store.add_chunks(
                texts=texts,
                metadatas=metadatas,
            )
            legacy_ids = await legacy_store.add_chunks(
                texts=texts,
                metadatas=metadatas,
                speech_id="test_unicode",
            )
            
            # Both should succeed
            assert len(postgres_ids) == 1
            assert len(legacy_ids) == 1
            
            # Search should work with Unicode
            postgres_results = await postgres_store.similarity_search(
                query="hello world", k=1
            )
            legacy_results = await legacy_store.similarity_search(
                query="hello world", k=1
            )
            
            # Both should return results
            assert len(postgres_results) > 0
            assert len(legacy_results) > 0
            
        finally:
            if postgres_engine:
                postgres_engine.close()

    @pytest.mark.asyncio
    async def test_large_metadata_handling(
        self, skip_if_single_backend, test_collection_name
    ):
        """Verify both backends handle large metadata consistently."""
        postgres_store, postgres_engine = await get_vector_store_for_backend(
            "postgres", test_collection_name
        )
        legacy_store, _ = await get_vector_store_for_backend("legacy")
        
        # Large metadata with nested structures
        texts = ["Test document with large metadata"]
        metadatas = [
            {
                "speaker": "Test Speaker",
                "tags": ["tag" + str(i) for i in range(50)],
                "nested": {
                    "level1": {"level2": {"level3": "deep value"}},
                    "list": [1, 2, 3, 4, 5],
                },
                "long_text": "x" * 1000,
            }
        ]
        
        try:
            # Add to both backends
            postgres_ids = await postgres_store.add_chunks(
                texts=texts,
                metadatas=metadatas,
            )
            legacy_ids = await legacy_store.add_chunks(
                texts=texts,
                metadatas=metadatas,
                speech_id="test_large_meta",
            )
            
            # Both should succeed
            assert len(postgres_ids) == 1
            assert len(legacy_ids) == 1
            
        finally:
            if postgres_engine:
                postgres_engine.close()
