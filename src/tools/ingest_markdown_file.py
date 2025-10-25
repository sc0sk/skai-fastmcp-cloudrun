"""Single markdown file ingestion tool with vector embeddings."""
from enum import Enum
from typing import Optional, Dict, Any
from pathlib import Path

from fastmcp import Context
from pydantic import BaseModel, Field
from langchain_text_splitters import RecursiveCharacterTextSplitter

from tools.ingestion_utils.markdown_parser import parse_markdown_file
from tools.ingestion_utils.path_validator import validate_file_path
from tools.ingestion_utils.auth import require_admin_role
from storage.metadata_store import MetadataStore
from storage.vector_store import VectorStoreService
from config import get_chunk_size, get_chunk_overlap


class DuplicatePolicy(str, Enum):
    """Policy for handling duplicate speech IDs."""
    SKIP = "skip"
    UPDATE = "update"
    ERROR = "error"


async def ingest_markdown_file(
    file_path: str,
    duplicate_policy: str = "skip",
    validate_path: bool = True,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """Ingest a single markdown file with YAML frontmatter.
    
    Args:
        file_path: Path to markdown file
        duplicate_policy: How to handle duplicates (skip/update/error)
        validate_path: Whether to validate file path security
        ctx: FastMCP context for auth
        
    Returns:
        Dict with status, speech_id, chunks_created, message
        
    Raises:
        PermissionError: If user is not admin
        FileNotFoundError: If file doesn't exist
        ValueError: If validation fails or duplicate with error policy
    """
    # 1. Authorize admin access
    if ctx:
        await require_admin_role(ctx)
    
    # 2. Validate file path
    validated_path = validate_file_path(file_path, validate_path)
    
    # 3. Parse markdown and extract metadata
    metadata, content = parse_markdown_file(str(validated_path))
    
    # 4. Check for duplicates
    metadata_store = MetadataStore()
    duplicate_exists = await metadata_store.check_speech_exists(metadata.speech_id)
    
    if duplicate_exists:
        if duplicate_policy == "skip":
            return {
                "status": "skipped",
                "speech_id": metadata.speech_id,
                "chunks_created": 0,
                "message": f"Speech {metadata.speech_id} already exists (skipped)"
            }
        elif duplicate_policy == "error":
            raise ValueError(f"Speech {metadata.speech_id} already exists")
        # else: update (continue with ingestion)
    
    # 5. Chunk text content
    chunk_size = get_chunk_size()
    chunk_overlap = get_chunk_overlap()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = text_splitter.split_text(content)
    
    # 6. Store in transaction (metadata + embeddings)
    try:
        # Store metadata
        await metadata_store.store_speech(
            speech_id=metadata.speech_id,
            speaker=metadata.speaker,
            party=metadata.party,
            chamber=metadata.chamber,
            date=metadata.date,
            title=metadata.title,
            text=content,
            state=metadata.state,
            hansard_reference=metadata.hansard_reference
        )
        
        # Generate embeddings and store vectors
        vector_store = VectorStoreService()

        # Create metadata for each chunk
        chunk_metadatas = [
            {
                "speech_id": metadata.speech_id,
                "speaker": metadata.speaker,
                "party": metadata.party,
                "chamber": metadata.chamber,
                "date": str(metadata.date),
                "chunk_index": i,
                "title": metadata.title
            }
            for i in range(len(chunks))
        ]

        chunk_ids = await vector_store.add_chunks(
            texts=chunks,
            metadatas=chunk_metadatas,
            speech_id=metadata.speech_id,
            ctx=ctx
        )
        chunk_count = len(chunk_ids)
        
        return {
            "status": "success",
            "speech_id": metadata.speech_id,
            "chunks_created": chunk_count,
            "message": f"Ingested {metadata.speech_id} with {chunk_count} chunks"
        }
        
    except Exception as e:
        # Transaction rollback happens automatically in storage layers
        raise Exception(f"Ingestion failed: {e}")
