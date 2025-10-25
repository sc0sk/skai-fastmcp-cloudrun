"""Unit tests for retry logic in postgres_vector_store.

Tests verify:
- T011a: Transient errors trigger retry with exponential backoff
- T011b: 3 retry attempts with correct delays (1s, 2s, 4s)
- T011c: Final failure propagates after exhausting retries
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from psycopg import OperationalError as PsycopgOperationalError
from sqlalchemy.exc import OperationalError as SQLAlchemyOperationalError

from src.storage.postgres_vector_store import (
    PostgresVectorStoreService,
    with_retry,
)


class TestRetryDecorator:
    """Test retry decorator behavior in isolation."""

    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        """Successful operation should not trigger retries."""
        call_count = 0

        @with_retry(max_retries=3, base_delay=0.01)
        async def mock_operation():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await mock_operation()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_psycopg_error(self):
        """PsycopgOperationalError should trigger retry."""
        call_count = 0

        @with_retry(max_retries=3, base_delay=0.01)
        async def mock_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise PsycopgOperationalError("connection timeout")
            return "success"

        result = await mock_operation()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_on_sqlalchemy_error(self):
        """SQLAlchemyOperationalError should trigger retry."""
        call_count = 0

        @with_retry(max_retries=3, base_delay=0.01)
        async def mock_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise SQLAlchemyOperationalError(
                    "statement", "params", "orig", connection_invalidated=True
                )
            return "success"

        result = await mock_operation()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_exponential_backoff_delays(self):
        """Verify exponential backoff: 1s, 2s, 4s delays."""
        call_times = []

        @with_retry(max_retries=3, base_delay=1.0)
        async def mock_operation():
            call_times.append(asyncio.get_event_loop().time())
            if len(call_times) < 3:
                raise PsycopgOperationalError("transient error")
            return "success"

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await mock_operation()
            assert result == "success"
            assert len(call_times) == 3

            # Verify sleep called with exponential delays
            assert mock_sleep.call_count == 2
            delays = [call.args[0] for call in mock_sleep.call_args_list]
            assert delays == [1.0, 2.0]  # 1s, 2s (no sleep after 3rd attempt)

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self):
        """After 3 failed attempts, final exception should propagate."""
        call_count = 0

        @with_retry(max_retries=3, base_delay=0.01)
        async def mock_operation():
            nonlocal call_count
            call_count += 1
            raise PsycopgOperationalError("persistent error")

        with pytest.raises(PsycopgOperationalError, match="persistent error"):
            await mock_operation()

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_non_transient_error_no_retry(self):
        """Non-transient errors (e.g., ValueError) should not trigger retry."""
        call_count = 0

        @with_retry(max_retries=3, base_delay=0.01)
        async def mock_operation():
            nonlocal call_count
            call_count += 1
            raise ValueError("not a transient error")

        with pytest.raises(ValueError, match="not a transient error"):
            await mock_operation()

        assert call_count == 1  # No retries for non-transient errors


class TestPostgresVectorStoreRetry:
    """Test retry behavior in PostgresVectorStoreService methods."""

    @pytest.fixture
    def mock_store(self):
        """Mock PGVector store."""
        store = MagicMock()
        store.add_texts = MagicMock(return_value=["id1", "id2"])
        store.similarity_search_with_score = MagicMock(
            return_value=[("doc1", 0.9)]
        )
        store.delete = MagicMock(return_value=True)
        return store

    @pytest.fixture
    def service(self, mock_store):
        """Create service with mocked dependencies."""
        with patch(
            "src.storage.postgres_vector_store.PGVector",
            return_value=mock_store,
        ):
            with patch(
                "src.storage.postgres_vector_store."
                "LangChainEmbeddingsWrapper"
            ):
                service = PostgresVectorStoreService(
                    connection="postgresql+psycopg://test",
                    collection_name="test_collection",
                )
                service._store = mock_store
                return service

    @pytest.mark.asyncio
    async def test_add_chunks_retries_on_connection_error(
        self, service, mock_store
    ):
        """add_chunks should retry on transient connection errors."""
        call_count = 0

        def add_texts_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise PsycopgOperationalError("connection lost")
            return ["id1", "id2"]

        mock_store.add_texts = MagicMock(side_effect=add_texts_with_retry)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service.add_chunks(
                texts=["text1", "text2"],
                metadatas=[{"key": "val1"}, {"key": "val2"}],
            )

        assert result == ["id1", "id2"]
        assert call_count == 3
        assert mock_store.add_texts.call_count == 3

    @pytest.mark.asyncio
    async def test_similarity_search_retries_on_deadlock(
        self, service, mock_store
    ):
        """similarity_search should retry on deadlock errors."""
        call_count = 0

        def search_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise SQLAlchemyOperationalError(
                    "deadlock detected",
                    None,
                    None,
                    connection_invalidated=True,
                )
            return [("doc1", 0.9)]

        mock_store.similarity_search_with_score = MagicMock(
            side_effect=search_with_retry
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service.similarity_search(
                query="test query", k=5
            )

        assert result == [("doc1", 0.9)]
        assert call_count == 2
        assert mock_store.similarity_search_with_score.call_count == 2

    @pytest.mark.asyncio
    async def test_delete_retries_on_pool_exhaustion(
        self, service, mock_store
    ):
        """delete should retry on connection pool exhaustion."""
        call_count = 0

        def delete_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise SQLAlchemyOperationalError(
                    "connection pool exhausted", None, None
                )
            return True

        mock_store.delete = MagicMock(side_effect=delete_with_retry)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service.delete(ids=["id1", "id2"])

        assert result == 1  # Normalized to int
        assert call_count == 3
        assert mock_store.delete.call_count == 3

    @pytest.mark.asyncio
    async def test_final_failure_propagates(self, service, mock_store):
        """After exhausting retries, the final exception should propagate."""
        mock_store.add_texts = MagicMock(
            side_effect=PsycopgOperationalError(
                "persistent connection failure"
            )
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(
                PsycopgOperationalError,
                match="persistent connection failure",
            ):
                await service.add_chunks(
                    texts=["text1"],
                    metadatas=[{"key": "val"}],
                )

        # Should have attempted 3 times
        assert mock_store.add_texts.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_delays_measured(self, service, mock_store):
        """Verify actual delays: 1s, 2s, 4s between retry attempts."""
        call_count = 0

        def add_texts_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 4:  # Fail 3 times to see all delays
                raise PsycopgOperationalError("transient error")
            return ["id1"]

        mock_store.add_texts = MagicMock(side_effect=add_texts_with_retry)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await service.add_chunks(
                texts=["text1"],
                metadatas=[{"key": "val"}],
            )

            # Verify exponential backoff delays
            assert mock_sleep.call_count == 3
            delays = [call.args[0] for call in mock_sleep.call_args_list]
            assert delays == [1.0, 2.0, 4.0]  # Exponential: 1s, 2s, 4s

        assert result == ["id1"]
        assert call_count == 4  # 3 failures + 1 success
