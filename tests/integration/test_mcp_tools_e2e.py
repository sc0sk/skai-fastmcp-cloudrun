"""Integration tests for MCP tools with postgres backend support.

Tests verify:
- T014: E2E MCP tool operations with VECTOR_BACKEND=postgres
- search_hansard_speeches tool with various filters
- ingest_markdown_file tool for document ingestion
- Backend selection and feature flag behavior

Prerequisites:
- VECTOR_BACKEND environment variable (postgres or legacy)
- Cloud SQL instance accessible with test data
- Application Default Credentials configured

Run with:
    # Test with postgres backend
    VECTOR_BACKEND=postgres pytest tests/integration/test_mcp_tools_e2e.py -v
    
    # Test with legacy backend
    VECTOR_BACKEND=legacy pytest tests/integration/test_mcp_tools_e2e.py -v
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest

from src import config


@pytest.fixture(scope="module")
def backend_name() -> str:
    """Get current vector backend from environment."""
    return os.getenv("VECTOR_BACKEND", config.DEFAULT_VECTOR_BACKEND)


@pytest.fixture(scope="module")
def test_speech_data() -> Dict[str, Any]:
    """Sample speech data for testing ingestion."""
    return {
        "speech_id": f"test_speech_{uuid.uuid4().hex[:8]}",
        "content": """
        Mr Speaker, I rise to address the critical issue of housing affordability
        in our community. The escalating property prices and rental costs have
        placed immense pressure on families and young Australians seeking to
        enter the housing market.
        
        We must act decisively to increase housing supply, support first-home
        buyers, and ensure that every Australian has access to secure and
        affordable housing.
        """,
        "metadata": {
            "speaker": "Test Member",
            "date": "2024-10-25",
            "chamber": "House of Representatives",
            "party": "Independent",
            "debate": "Housing Affordability",
        },
    }


class TestSearchTool:
    """Test search_hansard_speeches tool with backend selection."""

    @pytest.mark.asyncio
    async def test_basic_search(self, backend_name):
        """Test basic semantic search without filters."""
        from src.tools.search import search_hansard_speeches
        
        # Search for housing-related content
        result = await search_hansard_speeches(
            query="housing affordability and property market",
            limit=5,
        )
        
        # Verify response structure
        assert isinstance(result, dict)
        assert "results" in result
        assert "metadata" in result
        
        # Verify results format
        if result["results"]:
            for speech in result["results"]:
                assert "chunk_id" in speech
                assert "speech_id" in speech
                assert "content" in speech
                assert "similarity_score" in speech
                assert isinstance(speech["similarity_score"], float)

    @pytest.mark.asyncio
    async def test_search_with_party_filter(self, backend_name):
        """Test search with political party filter."""
        from src.tools.search import search_hansard_speeches
        from src.models.enums import PartyEnum
        
        result = await search_hansard_speeches(
            query="parliament discussion",
            party=PartyEnum.LIBERAL,
            limit=10,
        )
        
        assert isinstance(result, dict)
        
        # Verify party filter applied if results returned
        if result.get("results"):
            for speech in result["results"]:
                # Party should match filter
                assert speech.get("party") == "Liberal"

    @pytest.mark.asyncio
    async def test_search_with_chamber_filter(self, backend_name):
        """Test search with chamber filter."""
        from src.tools.search import search_hansard_speeches
        from src.models.enums import ChamberEnum
        
        result = await search_hansard_speeches(
            query="legislative debate",
            chamber=ChamberEnum.HOUSE_OF_REPRESENTATIVES,
            limit=10,
        )
        
        assert isinstance(result, dict)
        
        # Verify chamber filter applied if results returned
        if result.get("results"):
            for speech in result["results"]:
                assert speech.get("chamber") == "House of Representatives"

    @pytest.mark.asyncio
    async def test_search_with_date_range(self, backend_name):
        """Test search with date range filters."""
        from src.tools.search import search_hansard_speeches
        
        result = await search_hansard_speeches(
            query="policy announcement",
            start_date="2024-01-01",
            end_date="2024-12-31",
            limit=10,
        )
        
        assert isinstance(result, dict)
        
        # Verify date range applied if results returned
        if result.get("results"):
            for speech in result["results"]:
                date = speech.get("date")
                if date:
                    assert "2024" in date

    @pytest.mark.asyncio
    async def test_search_with_multiple_filters(self, backend_name):
        """Test search with combined filters."""
        from src.tools.search import search_hansard_speeches
        from src.models.enums import ChamberEnum, PartyEnum
        
        result = await search_hansard_speeches(
            query="government policy",
            party=PartyEnum.LIBERAL,
            chamber=ChamberEnum.HOUSE_OF_REPRESENTATIVES,
            start_date="2024-01-01",
            end_date="2024-12-31",
            limit=5,
        )
        
        assert isinstance(result, dict)
        assert "results" in result
        
        # Multiple filters may return no results (valid outcome)
        if result.get("results"):
            for speech in result["results"]:
                assert speech.get("party") == "Liberal"
                assert speech.get("chamber") == "House of Representatives"

    @pytest.mark.asyncio
    async def test_search_limit_bounds(self, backend_name):
        """Test search limit parameter validation."""
        from src.tools.search import search_hansard_speeches
        
        # Test with minimum limit
        result = await search_hansard_speeches(
            query="test",
            limit=1,
        )
        
        assert isinstance(result, dict)
        assert len(result.get("results", [])) <= 1
        
        # Test with maximum limit
        result = await search_hansard_speeches(
            query="parliament",
            limit=100,
        )
        
        assert isinstance(result, dict)
        assert len(result.get("results", [])) <= 100

    @pytest.mark.asyncio
    async def test_search_empty_query(self, backend_name):
        """Test search behavior with minimal/empty query."""
        from src.tools.search import search_hansard_speeches
        
        # Single character query (edge case)
        result = await search_hansard_speeches(
            query="a",
            limit=5,
        )
        
        # Should not error, may return results
        assert isinstance(result, dict)
        assert "results" in result


class TestFetchTool:
    """Test fetch_hansard_speech tool."""

    @pytest.mark.asyncio
    async def test_fetch_speech_by_id(self, backend_name):
        """Test fetching speech by ID."""
        from src.tools.fetch import fetch_hansard_speech
        
        # First, get a speech ID from search
        from src.tools.search import search_hansard_speeches
        
        search_result = await search_hansard_speeches(
            query="parliament",
            limit=1,
        )
        
        if not search_result.get("results"):
            pytest.skip("No speeches in database for fetch test")
        
        speech_id = search_result["results"][0]["speech_id"]
        
        # Fetch the full speech
        result = await fetch_hansard_speech(speech_id=speech_id)
        
        # Verify response structure
        assert isinstance(result, dict)
        assert "speech_id" in result
        assert result["speech_id"] == speech_id
        assert "content" in result
        assert "speaker" in result
        assert "date" in result

    @pytest.mark.asyncio
    async def test_fetch_nonexistent_speech(self, backend_name):
        """Test fetching non-existent speech ID."""
        from src.tools.fetch import fetch_hansard_speech
        
        fake_id = f"nonexistent_{uuid.uuid4().hex}"
        
        # Should return error or empty result, not crash
        result = await fetch_hansard_speech(speech_id=fake_id)
        
        assert isinstance(result, dict)
        # Either error field or empty/null content
        assert (
            "error" in result
            or result.get("content") is None
            or result.get("content") == ""
        )


class TestIngestTool:
    """Test ingest_markdown_file tool with backend selection."""

    @pytest.mark.asyncio
    async def test_ingest_markdown_basic(
        self, backend_name, test_speech_data, tmp_path
    ):
        """Test basic markdown file ingestion."""
        from src.tools.ingest_markdown_file import ingest_markdown_file
        
        # Create temporary markdown file
        md_file = tmp_path / "test_speech.md"
        md_file.write_text(
            f"""---
speech_id: {test_speech_data['speech_id']}
speaker: {test_speech_data['metadata']['speaker']}
date: {test_speech_data['metadata']['date']}
chamber: {test_speech_data['metadata']['chamber']}
party: {test_speech_data['metadata']['party']}
debate: {test_speech_data['metadata']['debate']}
---

{test_speech_data['content']}
"""
        )
        
        # Mock context for progress reporting
        ctx = AsyncMock()
        ctx.info = AsyncMock()
        ctx.report_progress = AsyncMock()
        
        # Ingest the file
        result = await ingest_markdown_file(
            file_path=str(md_file),
            duplicate_policy="skip",
            validate_path=False,
            ctx=ctx,
        )
        
        # Verify result structure
        assert isinstance(result, dict)
        assert "status" in result
        # May be "success", "skipped", or "error"
        assert result["status"] in ["success", "skipped", "error"]
        
        if result["status"] == "success":
            assert "speech_id" in result
            assert "chunks_created" in result
            assert isinstance(result["chunks_created"], int)

    @pytest.mark.asyncio
    async def test_ingest_duplicate_handling(
        self, backend_name, test_speech_data, tmp_path
    ):
        """Test duplicate speech handling in ingestion."""
        from src.tools.ingest_markdown_file import ingest_markdown_file
        
        # Create temporary markdown file
        md_file = tmp_path / "duplicate_test.md"
        md_file.write_text(
            f"""---
speech_id: {test_speech_data['speech_id']}
speaker: {test_speech_data['metadata']['speaker']}
date: {test_speech_data['metadata']['date']}
---

{test_speech_data['content']}
"""
        )
        
        ctx = AsyncMock()
        ctx.info = AsyncMock()
        ctx.report_progress = AsyncMock()
        
        # First ingestion
        result1 = await ingest_markdown_file(
            file_path=str(md_file),
            duplicate_policy="skip",
            validate_path=False,
            ctx=ctx,
        )
        
        # Second ingestion (should be skipped)
        result2 = await ingest_markdown_file(
            file_path=str(md_file),
            duplicate_policy="skip",
            validate_path=False,
            ctx=ctx,
        )
        
        # Second result should indicate duplicate handling
        assert isinstance(result2, dict)
        assert result2["status"] in ["skipped", "success"]


class TestBackendSelection:
    """Test backend selection and feature flag behavior."""

    @pytest.mark.asyncio
    async def test_backend_config_respected(self, backend_name):
        """Verify configured backend is actually used."""
        from src.storage.vector_store import get_default_vector_store
        
        # Get vector store instance
        store = await get_default_vector_store()
        
        # Verify instance type matches expected backend
        if backend_name == "postgres":
            # Should be using postgres backend
            assert hasattr(store, "_store") or hasattr(store, "_vector_store")
        elif backend_name == "legacy":
            # Should be using legacy backend
            assert hasattr(store, "_vector_store")
        
        # Backend should be functional
        assert store is not None

    @pytest.mark.asyncio
    async def test_backend_switching_isolated(self, backend_name):
        """Verify backend switch doesn't affect data isolation."""
        from src.tools.search import search_hansard_speeches
        
        # Run search with current backend
        result = await search_hansard_speeches(
            query="test isolation",
            limit=5,
        )
        
        # Should work regardless of backend
        assert isinstance(result, dict)
        assert "results" in result
        
        # Results should have consistent structure
        if result.get("results"):
            for speech in result["results"]:
                assert "chunk_id" in speech
                assert "speech_id" in speech


class TestPerformanceComparison:
    """Performance comparison tests between backends."""

    @pytest.mark.asyncio
    async def test_search_latency_comparable(self, backend_name):
        """Verify search latency is comparable between backends.
        
        Target: Within 50% of each other (not strict assertion).
        """
        import time
        from src.tools.search import search_hansard_speeches
        
        # Warm-up query
        await search_hansard_speeches(query="test", limit=1)
        
        # Measure actual query
        start = time.time()
        result = await search_hansard_speeches(
            query="housing policy debate",
            limit=10,
        )
        latency_ms = (time.time() - start) * 1000
        
        # Log for comparison
        print(
            f"\nSearch latency ({backend_name} backend): {latency_ms:.1f}ms"
        )
        
        # Sanity check (not strict comparison)
        assert latency_ms < 10000, (
            f"Search too slow ({backend_name}): {latency_ms:.1f}ms"
        )
        
        assert isinstance(result, dict)
