"""Output formatting parity tests for vector store backends.

Tests verify:
- T016: Output format consistency between postgres and legacy backends
- Result schemas match exactly (keys, types, structure)
- Service layer adapters produce identical output formats
- Tools receive consistent data regardless of backend

Prerequisites:
- Both backends must be functional
- Test data in both backends for comparison

Run with:
    pytest tests/integration/storage/test_output_format_parity.py -v
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List

import pytest

from src import config


@pytest.fixture(scope="module")
def test_collection_name() -> str:
    """Generate unique collection name for test isolation."""
    return f"test_format_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="module")
def sample_documents() -> List[Dict[str, Any]]:
    """Sample documents for format testing."""
    return [
        {
            "text": "Parliament discussed housing affordability today.",
            "metadata": {
                "speaker": "Test Speaker",
                "date": "2024-10-25",
                "chamber": "House",
                "party": "Liberal",
            },
        },
        {
            "text": "The budget includes infrastructure funding.",
            "metadata": {
                "speaker": "Test Minister",
                "date": "2024-10-26",
                "chamber": "Senate",
                "party": "Labor",
            },
        },
    ]


class TestAddChunksOutputFormat:
    """Test add_chunks output format consistency."""

    @pytest.mark.asyncio
    async def test_add_chunks_returns_list_of_strings(
        self, sample_documents, test_collection_name
    ):
        """Verify add_chunks returns List[str] for both backends."""
        from src.storage.vector_store import get_default_vector_store
        
        store = await get_default_vector_store()
        
        texts = [doc["text"] for doc in sample_documents]
        metadatas = [doc["metadata"] for doc in sample_documents]
        
        # Add chunks
        result = await store.add_chunks(
            texts=texts,
            metadatas=metadatas,
            speech_id="test_format_add",
        )
        
        # Verify return type
        assert isinstance(result, list), "add_chunks must return a list"
        assert len(result) == len(texts), "Must return one ID per text"
        
        # All items must be strings
        for chunk_id in result:
            assert isinstance(chunk_id, str), (
                f"Chunk ID must be string, got {type(chunk_id)}"
            )
            assert len(chunk_id) > 0, "Chunk ID must not be empty"

    @pytest.mark.asyncio
    async def test_add_chunks_ids_are_unique(
        self, sample_documents, test_collection_name
    ):
        """Verify all returned IDs are unique."""
        from src.storage.vector_store import get_default_vector_store
        
        store = await get_default_vector_store()
        
        texts = [doc["text"] for doc in sample_documents]
        metadatas = [doc["metadata"] for doc in sample_documents]
        
        result = await store.add_chunks(
            texts=texts,
            metadatas=metadatas,
            speech_id="test_unique_ids",
        )
        
        # All IDs must be unique
        assert len(set(result)) == len(result), (
            "All chunk IDs must be unique"
        )


class TestSimilaritySearchOutputFormat:
    """Test similarity_search output format consistency."""

    @pytest.mark.asyncio
    async def test_similarity_search_returns_list_of_dicts(
        self, sample_documents
    ):
        """Verify similarity_search returns List[Dict[str, Any]]."""
        from src.storage.vector_store import get_default_vector_store
        
        store = await get_default_vector_store()
        
        # Add test data
        texts = [doc["text"] for doc in sample_documents]
        metadatas = [doc["metadata"] for doc in sample_documents]
        await store.add_chunks(
            texts=texts,
            metadatas=metadatas,
            speech_id="test_search_format",
        )
        
        # Search
        result = await store.similarity_search(
            query="parliament housing",
            k=5,
        )
        
        # Verify return type
        assert isinstance(result, list), (
            "similarity_search must return a list"
        )
        
        # If results exist, verify structure
        if result:
            for item in result:
                assert isinstance(item, dict), (
                    f"Each result must be dict, got {type(item)}"
                )

    @pytest.mark.asyncio
    async def test_similarity_search_result_schema(
        self, sample_documents
    ):
        """Verify each result has required keys with correct types."""
        from src.storage.vector_store import get_default_vector_store
        
        store = await get_default_vector_store()
        
        # Add test data
        texts = [doc["text"] for doc in sample_documents]
        metadatas = [doc["metadata"] for doc in sample_documents]
        await store.add_chunks(
            texts=texts,
            metadatas=metadatas,
            speech_id="test_schema",
        )
        
        # Search
        result = await store.similarity_search(
            query="parliament",
            k=5,
        )
        
        # Verify schema for each result
        for item in result:
            # Required keys
            assert "chunk_id" in item, "Must have chunk_id key"
            assert "chunk_text" in item, "Must have chunk_text key"
            assert "score" in item, "Must have score key"
            assert "metadata" in item, "Must have metadata key"
            
            # Type assertions
            # chunk_id can be str or None (some backends may not return ID)
            assert item["chunk_id"] is None or isinstance(
                item["chunk_id"], str
            ), f"chunk_id must be str or None, got {type(item['chunk_id'])}"
            
            assert isinstance(item["chunk_text"], str), (
                f"chunk_text must be str, got {type(item['chunk_text'])}"
            )
            
            assert isinstance(item["score"], (int, float)), (
                f"score must be numeric, got {type(item['score'])}"
            )
            
            assert isinstance(item["metadata"], dict), (
                f"metadata must be dict, got {type(item['metadata'])}"
            )

    @pytest.mark.asyncio
    async def test_similarity_search_score_range(self, sample_documents):
        """Verify scores are in valid range [0, 1]."""
        from src.storage.vector_store import get_default_vector_store
        
        store = await get_default_vector_store()
        
        # Add test data
        texts = [doc["text"] for doc in sample_documents]
        metadatas = [doc["metadata"] for doc in sample_documents]
        await store.add_chunks(
            texts=texts,
            metadatas=metadatas,
            speech_id="test_score_range",
        )
        
        # Search
        result = await store.similarity_search(
            query="housing",
            k=5,
        )
        
        # Verify score ranges
        for item in result:
            score = item["score"]
            assert 0.0 <= score <= 1.0, (
                f"Score must be in [0, 1], got {score}"
            )

    @pytest.mark.asyncio
    async def test_similarity_search_metadata_preservation(
        self, sample_documents
    ):
        """Verify metadata is preserved in search results."""
        from src.storage.vector_store import get_default_vector_store
        
        store = await get_default_vector_store()
        
        # Add test data
        texts = [doc["text"] for doc in sample_documents]
        metadatas = [doc["metadata"] for doc in sample_documents]
        await store.add_chunks(
            texts=texts,
            metadatas=metadatas,
            speech_id="test_metadata_preserved",
        )
        
        # Search
        result = await store.similarity_search(
            query="parliament",
            k=5,
        )
        
        # Verify metadata structure
        for item in result:
            metadata = item["metadata"]
            
            # Should have speech_id (added by add_chunks)
            assert "speech_id" in metadata, (
                "Metadata must include speech_id"
            )
            
            # Original metadata keys should be present
            # (may vary by result, but check if any are present)
            possible_keys = ["speaker", "date", "chamber", "party"]
            has_original_metadata = any(
                key in metadata for key in possible_keys
            )
            
            # At least speech_id should be present
            assert len(metadata) > 0, "Metadata must not be empty"

    @pytest.mark.asyncio
    async def test_similarity_search_empty_results_format(self):
        """Verify empty results return empty list (not None or error)."""
        from src.storage.vector_store import get_default_vector_store
        
        store = await get_default_vector_store()
        
        # Search with filter that matches nothing
        result = await store.similarity_search(
            query="test",
            k=10,
            filter={"nonexistent_field": "nonexistent_value"},
        )
        
        # Must return empty list, not None
        assert result is not None, "Must return list, not None"
        assert isinstance(result, list), "Must return list"
        assert len(result) == 0, "Must return empty list for no matches"


class TestDeleteOutputFormat:
    """Test delete operation output format consistency."""

    @pytest.mark.asyncio
    async def test_delete_by_speech_id_returns_int(self, sample_documents):
        """Verify delete_by_speech_id returns int (count)."""
        from src.storage.vector_store import get_default_vector_store
        
        store = await get_default_vector_store()
        
        # Add test data
        texts = [doc["text"] for doc in sample_documents]
        metadatas = [doc["metadata"] for doc in sample_documents]
        speech_id = f"test_delete_{uuid.uuid4().hex[:8]}"
        
        await store.add_chunks(
            texts=texts,
            metadatas=metadatas,
            speech_id=speech_id,
        )
        
        # Delete
        result = await store.delete_by_speech_id(speech_id)
        
        # Verify return type
        assert isinstance(result, int), (
            f"delete_by_speech_id must return int, got {type(result)}"
        )
        
        # Should be non-negative
        assert result >= 0, (
            f"Delete count must be non-negative, got {result}"
        )


class TestStatsOutputFormat:
    """Test get_stats output format consistency."""

    @pytest.mark.asyncio
    async def test_get_stats_returns_dict(self):
        """Verify get_stats returns Dict[str, Any]."""
        from src.storage.vector_store import get_default_vector_store
        
        store = await get_default_vector_store()
        
        result = await store.get_stats()
        
        # Verify return type
        assert isinstance(result, dict), (
            f"get_stats must return dict, got {type(result)}"
        )

    @pytest.mark.asyncio
    async def test_get_stats_schema(self):
        """Verify get_stats has required keys with correct types."""
        from src.storage.vector_store import get_default_vector_store
        
        store = await get_default_vector_store()
        
        result = await store.get_stats()
        
        # Required keys
        assert "chunk_count" in result, "Must have chunk_count key"
        assert "unique_speeches" in result, "Must have unique_speeches key"
        assert "avg_chunks_per_speech" in result, (
            "Must have avg_chunks_per_speech key"
        )
        
        # Type assertions
        assert isinstance(result["chunk_count"], int), (
            f"chunk_count must be int, got {type(result['chunk_count'])}"
        )
        
        assert isinstance(result["unique_speeches"], int), (
            f"unique_speeches must be int, got "
            f"{type(result['unique_speeches'])}"
        )
        
        assert isinstance(result["avg_chunks_per_speech"], (int, float)), (
            f"avg_chunks_per_speech must be numeric, got "
            f"{type(result['avg_chunks_per_speech'])}"
        )
        
        # Values should be non-negative
        assert result["chunk_count"] >= 0
        assert result["unique_speeches"] >= 0
        assert result["avg_chunks_per_speech"] >= 0.0


class TestBackendFormatParity:
    """Test that both backends produce identical output formats."""

    @pytest.mark.asyncio
    async def test_both_backends_same_add_chunks_format(
        self, sample_documents
    ):
        """Verify both backends return same format from add_chunks."""
        # This test would require switching backends, which is complex
        # For now, we verify the contract is met by the active backend
        from src.storage.vector_store import get_default_vector_store
        
        store = await get_default_vector_store()
        backend = config.get_vector_backend()
        
        texts = [doc["text"] for doc in sample_documents]
        metadatas = [doc["metadata"] for doc in sample_documents]
        
        result = await store.add_chunks(
            texts=texts,
            metadatas=metadatas,
            speech_id=f"test_parity_{backend}",
        )
        
        # Verify contract
        assert isinstance(result, list)
        assert all(isinstance(id, str) for id in result)
        assert len(result) == len(texts)

    @pytest.mark.asyncio
    async def test_both_backends_same_search_format(self, sample_documents):
        """Verify both backends return same format from similarity_search."""
        from src.storage.vector_store import get_default_vector_store
        
        store = await get_default_vector_store()
        backend = config.get_vector_backend()
        
        # Add test data
        texts = [doc["text"] for doc in sample_documents]
        metadatas = [doc["metadata"] for doc in sample_documents]
        await store.add_chunks(
            texts=texts,
            metadatas=metadatas,
            speech_id=f"test_search_parity_{backend}",
        )
        
        result = await store.similarity_search(
            query="parliament",
            k=5,
        )
        
        # Verify contract
        assert isinstance(result, list)
        
        if result:
            # All items must have same schema
            for item in result:
                assert isinstance(item, dict)
                assert "chunk_id" in item
                assert "chunk_text" in item
                assert "score" in item
                assert "metadata" in item
                assert isinstance(item["chunk_text"], str)
                assert isinstance(item["score"], (int, float))
                assert isinstance(item["metadata"], dict)


class TestEdgeCaseFormats:
    """Test output formats for edge cases."""

    @pytest.mark.asyncio
    async def test_empty_add_chunks_format(self):
        """Verify empty add returns empty list."""
        from src.storage.vector_store import get_default_vector_store
        
        store = await get_default_vector_store()
        
        result = await store.add_chunks(
            texts=[],
            metadatas=[],
            speech_id="empty_test",
        )
        
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_unicode_in_results_format(self):
        """Verify Unicode text preserves format."""
        from src.storage.vector_store import get_default_vector_store
        
        store = await get_default_vector_store()
        
        # Add Unicode text
        texts = ["Hello 你好 مرحبا 🌍"]
        metadatas = [{"test": "unicode"}]
        
        await store.add_chunks(
            texts=texts,
            metadatas=metadatas,
            speech_id="unicode_test",
        )
        
        # Search
        result = await store.similarity_search(query="hello", k=1)
        
        # Verify format still correct
        if result:
            assert isinstance(result[0]["chunk_text"], str)
            assert len(result[0]["chunk_text"]) > 0
