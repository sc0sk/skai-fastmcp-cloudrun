"""Service for interacting with the metadata database."""

import os
from typing import Optional

import asyncpg
from dotenv import load_dotenv

from google.cloud.sql.connector import Connector

from models.speech import SpeechMetadata as Speech

load_dotenv()


class MetadataService:
    """Service for interacting with the metadata database."""

    def __init__(
        self,
        project_id: str,
        region: str,
        instance_connection_name: str,
        db_user: str,
        db_pass: Optional[str] = None,
        db_name: str = "hansard",
    ):
        self.project_id = project_id
        self.region = region
        self.instance_connection_name = instance_connection_name
        self.db_user = db_user
        self.db_pass = db_pass
        self.db_name = db_name
        self.connector = Connector()

    async def get_db_connection(self) -> asyncpg.Connection:
        """Gets a database connection."""
        conn: asyncpg.Connection = await self.connector.connect_async(
            f"{self.project_id}:{self.region}:{self.instance_connection_name}",
            "asyncpg",
            user=self.db_user,
            password=self.db_pass,
            db=self.db_name,
        )
        return conn

    async def get_speech_by_hash(self, content_hash: str) -> Optional[Speech]:
        """Gets a speech by its content hash."""
        conn = await self.get_db_connection()
        try:
            row = await conn.fetchrow(
                "SELECT * FROM speeches WHERE content_hash = $1", content_hash
            )
            return Speech(**row) if row else None
        finally:
            await conn.close()

    async def add_speech(self, speech: Speech, conn: asyncpg.Connection) -> int:
        """Adds a speech to the database."""
        # This is a simplified version. A real implementation would handle
        # conflicts and other potential issues.
        row = await conn.fetchrow(
            """
            INSERT INTO speeches (speech_id, title, full_text, speaker, party, chamber, electorate, state, date, hansard_reference, topic_tags, source_url, word_count, content_hash)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            RETURNING speech_id
            """,
            speech.speech_id,
            speech.title,
            speech.full_text,
            speech.speaker,
            speech.party,
            speech.chamber,
            speech.electorate,
            speech.state,
            speech.date,
            speech.hansard_reference,
            speech.topic_tags,
            speech.source_url,
            speech.word_count,
            speech.content_hash,
        )
        return row["speech_id"]
