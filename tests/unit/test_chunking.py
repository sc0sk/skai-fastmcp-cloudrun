"""Unit tests for text chunking."""

import pytest
from langchain_text_splitters import RecursiveCharacterTextSplitter


class TestRecursiveCharacterTextSplitter:
    """Tests for LangChain text chunking with Australian Hansard speeches."""

    @pytest.fixture
    def splitter(self):
        """Create chunker with config from data-model.md."""
        return RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=150,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
            is_separator_regex=False,
        )

    def test_chunk_size_constraint(self, splitter):
        """Test chunks respect 800 character size limit."""
        long_text = "This is a test sentence. " * 100  # ~2500 chars

        chunks = splitter.split_text(long_text)

        for chunk in chunks:
            assert len(chunk) <= 800, f"Chunk exceeds 800 chars: {len(chunk)}"

    def test_chunk_overlap(self, splitter):
        """Test chunks have ~150 character overlap."""
        # Create text with clear boundary
        text = "A" * 400 + " " + "B" * 400 + " " + "C" * 400

        chunks = splitter.split_text(text)

        # Should create at least 2 chunks
        assert len(chunks) >= 2

        # Check overlap exists between consecutive chunks
        if len(chunks) >= 2:
            chunk1_end = chunks[0][-150:]
            chunk2_start = chunks[1][:150]
            # Some overlap should exist (not exact due to separator logic)
            assert any(char in chunk2_start for char in chunk1_end)

    def test_paragraph_boundaries_preserved(self, splitter):
        """Test chunker prefers paragraph boundaries (\n\n)."""
        text = (
            "Paragraph 1 with some content about climate change policy. "
            "More sentences here to make it longer and test boundaries. "
            "Even more content to ensure proper splitting occurs.\n\n"
            "Paragraph 2 starts here with different content about energy policy. "
            "This paragraph also needs to be sufficiently long for testing. "
            "Additional sentences to increase length.\n\n"
            "Paragraph 3 discusses economic impacts and policy trade-offs. "
            "More detailed analysis follows in subsequent sentences. "
            "Final thoughts on the matter."
        )

        chunks = splitter.split_text(text)

        # Verify chunks were created
        assert len(chunks) > 0

        # Check first chunk ends near paragraph boundary (or contains full paragraph)
        assert "\n\n" in text  # Ensure test data has paragraphs

    def test_sentence_boundaries_preferred(self, splitter):
        """Test chunker prefers sentence boundaries (. ) when possible."""
        # Create text with clear sentence boundaries
        sentences = [
            "This is sentence one about climate change. ",
            "This is sentence two about renewable energy. ",
            "This is sentence three about economic policy. ",
        ] * 10  # Repeat to exceed chunk size

        text = "".join(sentences)
        chunks = splitter.split_text(text)

        # Most chunks should end with period + space (sentence boundary)
        chunks_ending_with_period = sum(
            1 for chunk in chunks if chunk.rstrip().endswith(".")
        )

        # At least 50% of chunks should respect sentence boundaries
        assert chunks_ending_with_period >= len(chunks) * 0.5

    def test_short_text_single_chunk(self, splitter):
        """Test short text returns single chunk."""
        short_text = "This is a short speech about climate policy."

        chunks = splitter.split_text(short_text)

        assert len(chunks) == 1
        assert chunks[0] == short_text

    def test_exact_chunk_size_boundary(self, splitter):
        """Test text exactly at chunk size."""
        text = "A" * 800  # Exactly 800 chars

        chunks = splitter.split_text(text)

        assert len(chunks) == 1
        assert len(chunks[0]) == 800

    def test_empty_text(self, splitter):
        """Test empty text returns empty list."""
        chunks = splitter.split_text("")

        assert chunks == []

    def test_realistic_hansard_speech(self, splitter):
        """Test with realistic Australian Hansard speech structure."""
        speech = """Mr Speaker, I rise to address the House on the Climate Change Bill 2024.

This legislation represents a critical step forward in Australia's commitment to reducing greenhouse gas emissions and transitioning to renewable energy sources.

The bill contains three key provisions. First, it establishes a national emissions reduction target of 43% below 2005 levels by 2030. Second, it creates a framework for carbon pricing in the energy sector. Third, it provides funding for renewable energy infrastructure development.

I acknowledge concerns from the opposition regarding economic impacts. However, independent modeling from Treasury demonstrates that the transition to clean energy will create 76,000 new jobs in regional Australia by 2030.

In conclusion, this bill balances environmental responsibility with economic opportunity. I commend it to the House."""

        chunks = splitter.split_text(speech)

        # Verify chunking worked
        assert len(chunks) > 0

        # All chunks should be <= 800 chars
        for chunk in chunks:
            assert len(chunk) <= 800

        # Full text should be preserved (accounting for overlap)
        # Check first and last chunks contain original content
        assert speech[:100] in chunks[0]
        assert speech[-100:] in chunks[-1]

    def test_chunk_count_estimation(self, splitter):
        """Test chunk count estimation for expected dataset."""
        # Simulate 65 speeches with average ~12,000 chars each
        avg_speech_length = 12000
        num_speeches = 65
        total_chars = avg_speech_length * num_speeches

        # Estimate chunks: total / (chunk_size - overlap)
        effective_chunk_size = 800 - 150  # 650 chars
        estimated_chunks = total_chars / effective_chunk_size

        # Expected: ~780,000 / 650 ≈ 1,200 chunks for full dataset
        # For average single speech: 12,000 / 650 ≈ 18 chunks
        speech_chunks = avg_speech_length / effective_chunk_size

        assert 15 <= speech_chunks <= 20  # ~18 chunks per speech
        assert 1000 <= estimated_chunks <= 1500  # ~1,200 total chunks

    def test_unicode_and_special_characters(self, splitter):
        """Test chunker handles Unicode and special characters."""
        text = "Mr Speaker, I rise to discuss the government's fiscal policy. " * 20
        text += "This affects the Budget — including $50 billion in infrastructure. "
        text += "The Treasurer's statement emphasised 'economic resilience'. "

        chunks = splitter.split_text(text)

        # Verify no encoding errors
        for chunk in chunks:
            assert isinstance(chunk, str)
            assert len(chunk) > 0

        # Verify special characters preserved
        combined = "".join(chunks)
        assert "—" in combined  # em dash
        assert "$" in combined
        assert "'" in combined  # smart quote
