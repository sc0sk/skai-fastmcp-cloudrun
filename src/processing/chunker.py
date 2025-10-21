"""Text chunking service using LangChain RecursiveCharacterTextSplitter."""

from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List


class TextChunker:
    """Service for chunking speech text into semantic chunks."""

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
        separators: List[str] = None,
    ):
        """
        Initialize text chunker with configuration from data-model.md.

        Args:
            chunk_size: Target size of each chunk in characters (default: 800)
            chunk_overlap: Overlap between chunks to preserve context (default: 150)
            separators: List of separators to split on, in priority order
                       (default: ["\n\n"] - paragraphs only)
        """
        if separators is None:
            # Split on paragraphs first, then fallback to smaller units
            # Prioritize paragraph breaks to keep related content together
            separators = ["\n\n"]

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=separators,
            is_separator_regex=False,
        )

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into semantic chunks.

        Args:
            text: Full text to chunk

        Returns:
            List of text chunks (each ≤ chunk_size characters)

        Example:
            >>> chunker = TextChunker()
            >>> chunks = chunker.chunk_text("Long speech text...")
            >>> len(chunks[0]) <= 800
            True
        """
        if not text or not text.strip():
            return []

        return self.splitter.split_text(text)

    def chunk_with_metadata(self, text: str) -> List[dict]:
        """
        Split text into chunks with metadata (index, size).

        Args:
            text: Full text to chunk

        Returns:
            List of dicts with keys: chunk_text, chunk_index, chunk_size

        Example:
            >>> chunker = TextChunker()
            >>> chunks = chunker.chunk_with_metadata("Speech text...")
            >>> chunks[0]["chunk_index"]
            0
            >>> chunks[0]["chunk_size"] <= 800
            True
        """
        chunks = self.chunk_text(text)

        return [
            {"chunk_text": chunk, "chunk_index": idx, "chunk_size": len(chunk)}
            for idx, chunk in enumerate(chunks)
        ]

    def estimate_chunk_count(self, text: str) -> int:
        """
        Estimate number of chunks without actually chunking.

        Args:
            text: Full text

        Returns:
            Estimated chunk count

        Note:
            This is an approximation: total_chars / (chunk_size - chunk_overlap)
        """
        if not text or not text.strip():
            return 0

        effective_chunk_size = self.splitter._chunk_size - self.splitter._chunk_overlap
        return max(1, len(text) // effective_chunk_size)


# Singleton instance with default configuration (from data-model.md)
default_chunker = TextChunker(chunk_size=800, chunk_overlap=150)


def chunk_speech_text(text: str) -> List[str]:
    """
    Convenience function to chunk text with default configuration.

    Args:
        text: Full speech text

    Returns:
        List of text chunks

    Example:
        >>> from src.processing.chunker import chunk_speech_text
        >>> chunks = chunk_speech_text("Long parliamentary speech...")
        >>> all(len(chunk) <= 800 for chunk in chunks)
        True
    """
    return default_chunker.chunk_text(text)
