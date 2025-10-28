
























"""Metadata store for speech records using Cloud SQL PostgreSQL."""

from __future__ import annotations

import asyncio
import os
from datetime import date
from typing import Any, Callable, Dict, List, Optional, TypeVar

from dotenv import load_dotenv
from fastmcp import Context
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from src import config
from src.models.speech import SpeechMetadata
from .cloud_sql_engine import CloudSQLEngine

load_dotenv()

METADATA_TABLE_NAME = config.METADATA_TABLE_NAME

T = TypeVar("T")


class MetadataStore:
    """Service for managing speech metadata in PostgreSQL speeches table."""

    def __init__(
        self,
        project_id: Optional[str] = None,
        region: Optional[str] = None,
        instance: Optional[str] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        self.region = region or os.getenv("GCP_REGION", "us-central1")
        self.instance = instance or os.getenv("CLOUDSQL_INSTANCE")
        self.database = database or os.getenv("CLOUDSQL_DATABASE", "hansard")
        # Read user/password from parameters or environment
        self.user = user or os.getenv("CLOUDSQL_USER") or None

        password_env = os.getenv("DATABASE_PASSWORD")
        self.password = (
            password if password is not None else password_env or None
        )

        # Allow explicit override to force IAM DB authentication.
        # When USE_IAM_AUTH is truthy (1/true/yes), we clear user/password
        # so CloudSQLEngine will use the IAM token flow instead of
        # password authentication. This helps when a local `.env` still
        # contains legacy CLOUDSQL_USER or DATABASE_PASSWORD values.
        use_iam_env = os.getenv("USE_IAM_AUTH", "").strip().lower()
        if use_iam_env in ("1", "true", "yes"):
            self.user = None
            self.password = None

        self._engine_manager: Optional[CloudSQLEngine] = None

    def _ensure_engine(self) -> Engine:
        if self._engine_manager is None:
            self._engine_manager = CloudSQLEngine(
                project_id=self.project_id or "",
                region=self.region,
                instance=self.instance or "",
                database=self.database,
                user=self.user,
                password=self.password,
            )
        return self._engine_manager.engine

    async def _run_in_connection(self, fn: Callable[[Connection], T]) -> T:
        def _work() -> T:
            engine = self._ensure_engine()
            with engine.begin() as conn:
                return fn(conn)

        return await asyncio.to_thread(_work)

    async def add_speech(
        self, speech: SpeechMetadata, ctx: Optional[Context] = None
    ) -> str:
        if ctx:
            await ctx.report_progress(90, 100)

        def _insert(conn: Connection) -> str:
            existing = conn.execute(
                text(
                    "SELECT speech_id FROM "
                    f"{METADATA_TABLE_NAME} "
                    "WHERE content_hash = :hash"
                ),
                {"hash": speech.content_hash},
            ).scalar()

            if existing:
                raise ValueError(
                    "Duplicate speech detected (content_hash: "
                    f"{speech.content_hash})"
                )

            inserted_id = conn.execute(
                text(
                    f"""
                    INSERT INTO {METADATA_TABLE_NAME} (
                        title, full_text, speaker, party, chamber,
                        electorate, state, date, hansard_reference,
                        word_count, content_hash, topic_tags
                    ) VALUES (
                        :title, :full_text, :speaker, :party, :chamber,
                        :electorate, :state, :date, :hansard_reference,
                        :word_count, :content_hash, :topic_tags
                    )
                    RETURNING speech_id
                    """
                ),
                {
                    "title": speech.title,
                    "full_text": speech.full_text,
                    "speaker": speech.speaker,
                    "party": speech.party,
                    "chamber": speech.chamber,
                    "electorate": speech.electorate,
                    "state": speech.state,
                    "date": speech.date,
                    "hansard_reference": speech.hansard_reference,
                    "word_count": speech.word_count,
                    "content_hash": speech.content_hash,
                    "topic_tags": speech.topic_tags or [],
                },
            ).scalar_one()

            return str(inserted_id)

        speech_id = await self._run_in_connection(_insert)

        if ctx:
            await ctx.report_progress(100, 100)

        return speech_id

    async def get_speech(self, speech_id: str) -> Optional[SpeechMetadata]:
        def _fetch(conn: Connection) -> Optional[SpeechMetadata]:
            row = conn.execute(
                text(
                    f"SELECT * FROM {METADATA_TABLE_NAME} "
                    "WHERE speech_id = :id"
                ),
                {"id": speech_id},
            ).mappings().first()

            if not row:
                return None

            return SpeechMetadata(
                speech_id=speech_id,
                title=row["title"],
                full_text=row["full_text"],
                speaker=row["speaker"],
                party=row["party"],
                chamber=row["chamber"],
                electorate=row["electorate"],
                state=row["state"],
                date=row["date"],
                hansard_reference=row.get("hansard_reference") or "",
                topic_tags=row.get("topic_tags") or [],
                source_url=row.get("source_file"),
            )

        return await self._run_in_connection(_fetch)

    async def search_speeches(
        self,
        speaker: Optional[str] = None,
        party: Optional[str] = None,
        chamber: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        conditions: List[str] = []
        params: Dict[str, Any] = {}

        if speaker:
            conditions.append("speaker ILIKE :speaker")
            params["speaker"] = f"%{speaker}%"

        if party:
            conditions.append("party = :party")
            params["party"] = party

        if chamber:
            conditions.append("chamber = :chamber")
            params["chamber"] = chamber

        if date_from:
            conditions.append("date >= :date_from")
            params["date_from"] = date_from

        if date_to:
            conditions.append("date <= :date_to")
            params["date_to"] = date_to

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        def _search(conn: Connection) -> List[Dict[str, Any]]:
            result = conn.execute(
                text(
                                  f"""
                                  SELECT speech_id,
                                      title,
                                      speaker,
                                      party,
                                      chamber,
                                      electorate,
                                      state,
                                      date,
                                      hansard_reference,
                                      word_count
                                        FROM speeches
                                        WHERE {where_clause}
                                        ORDER BY date DESC
                                        LIMIT :limit
                                        """
                ),
                {**params, "limit": limit},
            )
            return [dict(row) for row in result.mappings().all()]

        return await self._run_in_connection(_search)

    async def delete_speech(self, speech_id: str) -> bool:
        def _delete(conn: Connection) -> bool:
            result = conn.execute(
                text(
                    f"DELETE FROM {METADATA_TABLE_NAME} "
                    "WHERE speech_id = :id"
                ),
                {"id": speech_id},
            )
            return result.rowcount > 0

        return await self._run_in_connection(_delete)

    async def get_stats(self) -> Dict[str, Any]:
        def _stats(conn: Connection) -> Dict[str, Any]:
            speech_count = conn.execute(
                text(f"SELECT COUNT(*) FROM {METADATA_TABLE_NAME}")
            ).scalar_one()

            unique_speakers = conn.execute(
                text(
                    "SELECT COUNT(DISTINCT speaker) FROM "
                    f"{METADATA_TABLE_NAME}"
                )
            ).scalar_one()

            date_range = conn.execute(
                text(
                    "SELECT MIN(date) AS earliest, MAX(date) AS latest FROM "
                    f"{METADATA_TABLE_NAME}"
                )
            ).mappings().first()

            party_rows = conn.execute(
                text(
                    f"""
                    SELECT party, COUNT(*) AS count
                    FROM {METADATA_TABLE_NAME}
                    GROUP BY party
                    ORDER BY count DESC
                    """
                )
            ).mappings().all()

            earliest = (
                date_range["earliest"].isoformat()
                if date_range and date_range["earliest"]
                else None
            )
            latest = (
                date_range["latest"].isoformat()
                if date_range and date_range["latest"]
                else None
            )

            return {
                "speech_count": speech_count,
                "unique_speakers": unique_speakers,
                "earliest_date": earliest,
                "latest_date": latest,
                "party_breakdown": {
                    row["party"]: row["count"] for row in party_rows
                },
            }

        return await self._run_in_connection(_stats)

    async def speech_exists_by_content_hash(self, content_hash: str) -> bool:
        def _exists(conn: Connection) -> bool:
            return bool(
                conn.execute(
                    text(
                        "SELECT EXISTS(SELECT 1 FROM "
                        f"{METADATA_TABLE_NAME} "
                        "WHERE content_hash = :hash)"
                    ),
                    {"hash": content_hash},
                ).scalar()
            )

        return await self._run_in_connection(_exists)

    async def get_speech_id_by_content_hash(
        self, content_hash: str
    ) -> Optional[str]:
        """Return speech_id for a given content hash if it exists."""

        def _fetch(conn: Connection) -> Optional[str]:
            return conn.execute(
                text(
                    "SELECT speech_id FROM "
                    f"{METADATA_TABLE_NAME} "
                    "WHERE content_hash = :hash"
                ),
                {"hash": content_hash},
            ).scalar()

        result = await self._run_in_connection(_fetch)
        return str(result) if result is not None else None

    async def check_speech_exists(self, speech_id: str) -> bool:
        def _exists(conn: Connection) -> bool:
            return bool(
                conn.execute(
                    text(
                        "SELECT EXISTS(SELECT 1 FROM "
                        f"{METADATA_TABLE_NAME} "
                        "WHERE speech_id = :id)"
                    ),
                    {"id": speech_id},
                ).scalar()
            )

        return await self._run_in_connection(_exists)

    async def store_speech(
        self,
        speech_id: str,
        speaker: str,
        party: str,
        chamber: str,
        date: Any,
        title: str,
        full_text: str,
        state: Optional[str] = None,
        hansard_reference: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> str:
        """Store a speech in the metadata store.

        Args:
            speech_id: Unique speech identifier
            speaker: Speaker name
            party: Political party
            chamber: Chamber (REPS/SENATE)
            date: Speech date
            title: Speech title
            full_text: Full speech text
            state: Optional state
            hansard_reference: Optional Hansard reference
            ctx: Optional FastMCP context
        """
        word_count = len(full_text.split())

        def _upsert(conn: Connection) -> None:
            conn.execute(
                text(
                    f"""
                    INSERT INTO {METADATA_TABLE_NAME} (
                        speech_id, title, full_text, speaker, party, chamber,
                        state, date, hansard_reference, word_count
                    ) VALUES (
                        :speech_id, :title, :full_text, :speaker, :party,
                        :chamber, :state, :date, :hansard_reference,
                        :word_count
                    )
                    ON CONFLICT (speech_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        full_text = EXCLUDED.full_text,
                        speaker = EXCLUDED.speaker,
                        party = EXCLUDED.party,
                        chamber = EXCLUDED.chamber,
                        state = EXCLUDED.state,
                        date = EXCLUDED.date,
                        hansard_reference = EXCLUDED.hansard_reference,
                        word_count = EXCLUDED.word_count,
                        updated_at = CURRENT_TIMESTAMP
                    """
                ),
                {
                    "speech_id": speech_id,
                    "title": title,
                    "full_text": full_text,
                    "speaker": speaker,
                    "party": party,
                    "chamber": chamber,
                    "state": state,
                    "date": date,
                    "hansard_reference": hansard_reference,
                    "word_count": word_count,
                },
            )

        await self._run_in_connection(_upsert)

        if ctx:
            await ctx.report_progress(50, 100)

        return speech_id

    async def close(self) -> None:
        if self._engine_manager:
            self._engine_manager.close()
            self._engine_manager = None


_default_metadata_store: Optional[MetadataStore] = None


async def get_default_metadata_store() -> MetadataStore:
    global _default_metadata_store
    if _default_metadata_store is None:
        _default_metadata_store = MetadataStore()
    return _default_metadata_store
