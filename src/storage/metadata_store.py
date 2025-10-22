"""Metadata store for speech records using Cloud SQL PostgreSQL."""

from typing import List, Optional, Dict, Any
from datetime import date, datetime
import os
import asyncio
import asyncpg
from contextlib import asynccontextmanager
from google.cloud.sql.connector import Connector
from dotenv import load_dotenv

from src.models.speech import SpeechMetadata

# Load environment variables
load_dotenv()


class MetadataStore:
    """Service for managing speech metadata in PostgreSQL speeches table."""

    def __init__(
        self,
        project_id: str = None,
        region: str = None,
        instance: str = None,
        database: str = None,
        user: str = None,
        password: str = None,
    ):
        """
        Initialize metadata store with Cloud SQL connection.

        Args:
            project_id: GCP project ID (defaults to GCP_PROJECT_ID env var)
            region: Cloud SQL region (defaults to GCP_REGION env var)
            instance: Cloud SQL instance name (defaults to CLOUDSQL_INSTANCE env var)
            database: Database name (defaults to CLOUDSQL_DATABASE env var)
            user: Database user (defaults to CLOUDSQL_USER env var)
            password: Database password (optional, uses IAM auth if None)

        Note:
            For production, use Cloud SQL IAM authentication (password=None)
        """
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        self.region = region or os.getenv("GCP_REGION", "us-central1")
        self.instance = instance or os.getenv("CLOUDSQL_INSTANCE")
        self.database = database or os.getenv("CLOUDSQL_DATABASE", "hansard")
        self.user = user or os.getenv("CLOUDSQL_USER")  # None for IAM auth
        self.password = password or os.getenv("DATABASE_PASSWORD")  # None for IAM auth

        # Connection pool (lazy init)
        self._pool: Optional[asyncpg.Pool] = None
        self._connector: Optional[Connector] = None

    async def _get_connection(self) -> asyncpg.Connection:
        """
        Get database connection using Cloud SQL Python Connector.

        Returns:
            asyncpg connection

        Note:
            Uses Cloud SQL Python Connector for local dev and production.
            Supports IAM authentication when password is None.
        """
        # Initialize Cloud SQL Python Connector if needed
        if self._connector is None:
            loop = asyncio.get_running_loop()
            self._connector = Connector(loop=loop)

        # Determine auth method (IAM if no password)
        use_iam_auth = self.password is None

        # Create connection
        conn = await self._connector.connect_async(
            f"{self.project_id}:{self.region}:{self.instance}",
            "asyncpg",
            user=self.user,
            db=self.database,
            enable_iam_auth=use_iam_auth,
            password=self.password if not use_iam_auth else None,
        )

        return conn

    async def _get_pool(self) -> asyncpg.Pool:
        """
        Get or create connection pool.

        Note: Currently using single connections via Cloud SQL Connector.
        TODO: Implement proper connection pooling with Cloud SQL Connector.
        """
        # For now, we'll use _get_connection() in methods instead of pooling
        # This is simpler and works with Cloud SQL Connector
        raise NotImplementedError("Use _get_connection() instead")

    async def add_speech(self, speech: SpeechMetadata) -> str:
        """
        Add speech metadata to database.

        Args:
            speech: SpeechMetadata instance

        Returns:
            Generated speech_id (UUID)

        Raises:
            ValueError: If speech with same content_hash already exists

        Example:
            >>> store = MetadataStore()
            >>> speech = SpeechMetadata(
            ...     title="Budget Speech",
            ...     full_text="Mr Speaker...",
            ...     speaker="Simon Kennedy",
            ...     party="Liberal",
            ...     chamber="House of Representatives",
            ...     electorate="Cook",
            ...     state="NSW",
            ...     date=date(2024, 6, 3),
            ...     hansard_reference="House Hansard, 3 June 2024"
            ... )
            >>> speech_id = await store.add_speech(speech)
        """
        conn = await self._get_connection()

        try:
            # Check for duplicate via content_hash
            existing = await conn.fetchval(
                "SELECT speech_id FROM speeches WHERE content_hash = $1",
                speech.content_hash,
            )

            if existing:
                raise ValueError(
                    f"Duplicate speech detected (content_hash: {speech.content_hash})"
                )

            # Insert new speech
            speech_id = await conn.fetchval(
                """
                INSERT INTO speeches (
                    title, full_text, speaker, party, chamber,
                    electorate, state, date, hansard_reference,
                    word_count, content_hash, topic_tags
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING speech_id
                """,
                speech.title,
                speech.full_text,
                speech.speaker,
                speech.party,
                speech.chamber,
                speech.electorate,
                speech.state,
                speech.date,
                speech.hansard_reference,
                speech.word_count,
                speech.content_hash,
                speech.topic_tags or [],
            )

            return str(speech_id)
        finally:
            await conn.close()

    async def get_speech(self, speech_id: str) -> Optional[SpeechMetadata]:
        """
        Retrieve speech by ID.

        Args:
            speech_id: UUID string

        Returns:
            SpeechMetadata instance or None if not found

        Example:
            >>> store = MetadataStore()
            >>> speech = await store.get_speech("speech-id-123")
            >>> speech.speaker
            'Simon Kennedy'
        """
        conn = await self._get_connection()

        try:
            row = await conn.fetchrow(
                "SELECT * FROM speeches WHERE speech_id = $1",
                speech_id,
            )

            if not row:
                return None

            # Convert asyncpg.Record to SpeechMetadata
            return SpeechMetadata(
                title=row["title"],
                full_text=row["full_text"],
                speaker=row["speaker"],
                party=row["party"],
                chamber=row["chamber"],
                electorate=row["electorate"],
                state=row["state"],
                date=row["date"],
                hansard_reference=row["hansard_reference"],
                topic_tags=row["topic_tags"],
            )
        finally:
            await conn.close()

    async def search_speeches(
        self,
        speaker: Optional[str] = None,
        party: Optional[str] = None,
        chamber: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Search speeches by metadata filters.

        Args:
            speaker: Filter by speaker name (partial match)
            party: Filter by party
            chamber: Filter by chamber
            date_from: Filter by date >= date_from
            date_to: Filter by date <= date_to
            limit: Max results to return (default: 50)

        Returns:
            List of speech metadata dicts

        Example:
            >>> store = MetadataStore()
            >>> speeches = await store.search_speeches(
            ...     party="Liberal",
            ...     chamber="House of Representatives",
            ...     date_from=date(2024, 1, 1)
            ... )
        """
        conn = await self._get_connection()

        # Build dynamic query
        conditions = []
        params = []
        param_idx = 1

        if speaker:
            conditions.append(f"speaker ILIKE ${param_idx}")
            params.append(f"%{speaker}%")
            param_idx += 1

        if party:
            conditions.append(f"party = ${param_idx}")
            params.append(party)
            param_idx += 1

        if chamber:
            conditions.append(f"chamber = ${param_idx}")
            params.append(chamber)
            param_idx += 1

        if date_from:
            conditions.append(f"date >= ${param_idx}")
            params.append(date_from)
            param_idx += 1

        if date_to:
            conditions.append(f"date <= ${param_idx}")
            params.append(date_to)
            param_idx += 1

        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        query = f"""
            SELECT speech_id, title, speaker, party, chamber,
                   electorate, state, date, hansard_reference, word_count
            FROM speeches
            WHERE {where_clause}
            ORDER BY date DESC
            LIMIT ${param_idx}
        """
        params.append(limit)

        try:
            rows = await conn.fetch(query, *params)

            # Convert to dicts
            return [dict(row) for row in rows]
        finally:
            await conn.close()

    async def delete_speech(self, speech_id: str) -> bool:
        """
        Delete speech by ID.

        Args:
            speech_id: UUID string

        Returns:
            True if deleted, False if not found

        Note:
            Should also delete associated chunks from speech_chunks table
        """
        conn = await self._get_connection()

        try:
            result = await conn.execute(
                "DELETE FROM speeches WHERE speech_id = $1",
                speech_id,
            )

            # Result format: "DELETE N" where N is row count
            deleted_count = int(result.split()[-1])
            return deleted_count > 0
        finally:
            await conn.close()

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dict with speech_count, unique_speakers, date_range, party_breakdown

        Example:
            >>> store = MetadataStore()
            >>> stats = await store.get_stats()
            >>> stats["speech_count"]
            65
        """
        conn = await self._get_connection()

        try:
            # Speech count
            speech_count = await conn.fetchval("SELECT COUNT(*) FROM speeches")

            # Unique speakers
            unique_speakers = await conn.fetchval(
                "SELECT COUNT(DISTINCT speaker) FROM speeches"
            )

            # Date range
            date_range = await conn.fetchrow(
                "SELECT MIN(date) as earliest, MAX(date) as latest FROM speeches"
            )

            # Party breakdown
            party_breakdown = await conn.fetch(
                """
                SELECT party, COUNT(*) as count
                FROM speeches
                GROUP BY party
                ORDER BY count DESC
                """
            )

            return {
                "speech_count": speech_count,
                "unique_speakers": unique_speakers,
                "earliest_date": date_range["earliest"].isoformat() if date_range["earliest"] else None,
                "latest_date": date_range["latest"].isoformat() if date_range["latest"] else None,
                "party_breakdown": {row["party"]: row["count"] for row in party_breakdown},
            }
        finally:
            await conn.close()

    async def close(self):
        """Close Cloud SQL connector."""
        if self._connector:
            await self._connector.close_async()
            self._connector = None


# Singleton instance with default configuration
_default_metadata_store: Optional[MetadataStore] = None


async def get_default_metadata_store() -> MetadataStore:
    """
    Get or create default metadata store instance.

    Returns:
        Singleton MetadataStore instance

    Example:
        >>> from src.storage.metadata_store import get_default_metadata_store
        >>> store = await get_default_metadata_store()
        >>> stats = await store.get_stats()
    """
    global _default_metadata_store
    if _default_metadata_store is None:
        _default_metadata_store = MetadataStore()
    return _default_metadata_store
