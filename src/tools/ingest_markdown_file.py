"""Tool for ingesting a single markdown file into Cloud SQL and PGVector."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

import yaml
from fastmcp import Context
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.tools import ArgsSchema, BaseTool
from pydantic import BaseModel, Field

from src import config
from src.models.speech import SpeechMetadata as Speech
from src.storage.metadata_store import MetadataStore
from src.storage.vector_store import get_default_vector_store


logger = logging.getLogger(__name__)


class IngestMarkdownFileInput(BaseModel):
    """Input schema for ingest_markdown_file tool."""

    file_path: str = Field(
        ...,
        description="Absolute path to the markdown file to ingest.",
        examples=["/path/to/file.md"],
    )
    collection_name: Optional[str] = Field(
        default=None,
        description=(
            "PGVector collection name override. Defaults to the "
            "PGVECTOR_COLLECTION environment variable."
        ),
    )


metadata_store = MetadataStore()


async def read_file_content(path: Path) -> str:
    """Read file contents on a worker thread."""

    return await asyncio.to_thread(path.read_text, encoding="utf-8")


def compute_file_hash(content: str) -> str:
    """Return SHA-256 hash of the provided content."""

    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _validate_path(file_path: str, validate: bool) -> Path:
    path = Path(file_path).expanduser()
    if not validate:
        return path
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")
    return path


async def ingest_markdown_file(
    file_path: str,
    collection_name: Optional[str] = None,
    *,
    request: Optional[Dict[str, Any]] = None,
    duplicate_policy: str = "skip",
    validate_path: bool = True,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """Ingest a markdown file into the metadata table and vector store."""

    # Normalize path and optional collection
    path = _validate_path(file_path, validate_path)
    target_collection = collection_name or config.get_pgvector_collection()

    try:
        content = await read_file_content(path)

        parts = content.split("---", 2)
        if len(parts) < 3:
            raise ValueError("Invalid markdown format: missing frontmatter")

        if content.lstrip().startswith("---"):
            metadata_str = parts[1]
            text_content = parts[2]
        else:
            metadata_str = parts[0]
            text_content = parts[2]
        raw_metadata: Any = yaml.safe_load(metadata_str) or {}
        if not isinstance(raw_metadata, dict):
            raise ValueError("Frontmatter must be a mapping of keys to values")
        metadata = dict(cast(Dict[str, Any], raw_metadata))

        chamber_value = metadata.get("chamber")
        if isinstance(chamber_value, str):
            chamber_normalized = chamber_value.strip().upper()
            chamber_map = {
                "REPS": "House of Representatives",
                "HOUSE OF REPRESENTATIVES": "House of Representatives",
                "SENATE": "Senate",
            }
            metadata["chamber"] = chamber_map.get(
                chamber_normalized,
                chamber_value,
            )

        if "electorate" not in metadata:
            raw_state = metadata.get("state")
            valid_state_codes = {
                "NSW",
                "VIC",
                "QLD",
                "WA",
                "SA",
                "TAS",
                "ACT",
                "NT",
            }
            if isinstance(raw_state, str):
                state_candidate = raw_state.strip()
                if state_candidate.upper() in valid_state_codes:
                    metadata["state"] = state_candidate.upper()
                else:
                    metadata.setdefault("electorate", state_candidate)
                    metadata["state"] = None

        topic_tags = metadata.get("topic_tags")
        if topic_tags is None:
            metadata["topic_tags"] = []
        elif isinstance(topic_tags, str):
            metadata["topic_tags"] = [
                tag.strip() for tag in topic_tags.split(",") if tag.strip()
            ]

        speech = Speech(**metadata, full_text=text_content)

        existing_id = await metadata_store.get_speech_id_by_content_hash(
            speech.content_hash
        )
        if existing_id:
            if duplicate_policy == "error":
                raise ValueError(
                    f"Speech already ingested with speech_id={existing_id}"
                )
            logger.info(
                "Skipping %s; already ingested as speech_id=%s",
                path,
                existing_id,
            )
            return {
                "status": "skipped",
                "file_path": str(path),
                "speech_id": existing_id,
            }

        # Note: speech.content_hash is computed from full_text only (not frontmatter)
        # This is intentional - we deduplicate based on speech content, not metadata
        speech_id = await metadata_store.add_speech(speech)

        # IMPORTANT: Remove speech_id from metadata before chunking
        # The markdown frontmatter may have a speech_id field, but we must use
        # the database-generated UUID instead to maintain referential integrity
        metadata_for_chunks = metadata.copy()
        metadata_for_chunks.pop("speech_id", None)

        chunk_size = config.get_chunk_size()
        chunk_overlap = config.get_chunk_overlap()
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        documents: List[Document] = splitter.create_documents(
            [text_content], metadatas=[metadata_for_chunks]
        )

        vector_store = await get_default_vector_store()
        texts_to_add = [doc.page_content for doc in documents]
        metadatas_to_add: List[Dict[str, Any]] = []
        for doc in documents:
            raw_doc_metadata = cast(
                Dict[str, Any], getattr(doc, "metadata", {}) or {}
            )
            doc_metadata: Dict[str, Any] = dict(raw_doc_metadata)
            doc_metadata.setdefault("speech_id", speech_id)
            doc_metadata.setdefault("collection", target_collection)
            metadatas_to_add.append(doc_metadata)

        await vector_store.add_chunks(
            texts=texts_to_add,
            metadatas=metadatas_to_add,
            speech_id=str(speech_id),
            ctx=ctx,
        )

        logger.info("Ingested %s as speech_id=%s", path, speech_id)
        return {
            "status": "success",
            "file_path": str(path),
            "speech_id": speech_id,
            "chunks_ingested": len(documents),
            "collection": target_collection,
        }

    except Exception as exc:  # pragma: no cover - diagnostic path
        logger.error("Failed to ingest %s: %s", path, exc, exc_info=True)
        return {
            "status": "error",
            "file_path": str(path),
            "error": str(exc),
        }


class IngestMarkdownFileTool(BaseTool):
    """LangChain tool wrapper around ingest_markdown_file."""

    name: str = "ingest_markdown_file"
    description: str = "Ingests a markdown file into Cloud SQL and PGVector."
    args_schema: ArgsSchema | None = IngestMarkdownFileInput

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        return asyncio.run(self.run_async(*args, **kwargs))

    async def _arun(self, *args: Any, **kwargs: Any) -> Any:
        return await self.run_async(*args, **kwargs)

    async def run_async(
        self,
        file_path: str,
        collection_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not file_path:
            return {"status": "error", "message": "File path cannot be empty."}
        return await ingest_markdown_file(
            file_path=file_path,
            collection_name=collection_name,
        )

