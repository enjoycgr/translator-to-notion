"""
Semantic chunking service for long text translation.

Splits long text into manageable chunks based on semantic boundaries
(paragraphs, headings) while respecting token limits.
"""

import re
from typing import List, Tuple
from dataclasses import dataclass

import tiktoken


@dataclass
class Chunk:
    """A text chunk with metadata."""
    text: str
    index: int
    token_count: int
    start_line: int = 0
    end_line: int = 0


class ChunkingService:
    """
    Service for splitting long text into semantic chunks.

    Features:
    - Splits by paragraph and heading boundaries
    - Token-aware splitting using tiktoken
    - Overlap support for context continuity
    - Preserves markdown structure
    """

    def __init__(
        self,
        max_tokens: int = 8000,
        overlap_sentences: int = 2,
        model: str = "gpt-4",
    ):
        """
        Initialize the chunking service.

        Args:
            max_tokens: Maximum tokens per chunk.
            overlap_sentences: Number of sentences to overlap between chunks.
            model: Model name for tokenizer (tiktoken compatible).
        """
        self.max_tokens = max_tokens
        self.overlap_sentences = overlap_sentences

        # Initialize tokenizer
        try:
            self.encoder = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fall back to cl100k_base (used by GPT-4, Claude uses similar)
            self.encoder = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count tokens for.

        Returns:
            Number of tokens.
        """
        return len(self.encoder.encode(text))

    def needs_chunking(self, text: str) -> bool:
        """
        Check if text needs to be chunked.

        Args:
            text: Text to check.

        Returns:
            True if text exceeds max_tokens limit.
        """
        return self.count_tokens(text) > self.max_tokens

    def split_by_semantic(self, text: str) -> List[str]:
        """
        Split text by semantic boundaries.

        Attempts to split at:
        1. Headings (# markdown headings)
        2. Double newlines (paragraph boundaries)
        3. Single sentences if necessary

        Args:
            text: Text to split.

        Returns:
            List of text chunks.
        """
        if not self.needs_chunking(text):
            return [text]

        # First, split into paragraphs
        paragraphs = self._split_paragraphs(text)

        # Group paragraphs into chunks
        chunks = []
        current_chunk: List[str] = []
        current_tokens = 0
        overlap_buffer: List[str] = []

        for para in paragraphs:
            para_tokens = self.count_tokens(para)

            # If single paragraph exceeds limit, split it further
            if para_tokens > self.max_tokens:
                # Save current chunk if not empty
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    overlap_buffer = self._get_overlap_sentences(current_chunk)
                    current_chunk = list(overlap_buffer)
                    current_tokens = sum(self.count_tokens(p) for p in current_chunk)

                # Split the large paragraph
                sub_chunks = self._split_large_paragraph(para)
                for sub in sub_chunks[:-1]:
                    chunks.append(sub)
                # Keep the last sub-chunk for continuation
                current_chunk = [sub_chunks[-1]]
                current_tokens = self.count_tokens(sub_chunks[-1])
                continue

            # Check if adding this paragraph would exceed limit
            if current_tokens + para_tokens > self.max_tokens and current_chunk:
                # Save current chunk
                chunks.append("\n\n".join(current_chunk))

                # Start new chunk with overlap
                overlap_buffer = self._get_overlap_sentences(current_chunk)
                current_chunk = list(overlap_buffer)
                current_tokens = sum(self.count_tokens(p) for p in current_chunk)

            # Add paragraph to current chunk
            current_chunk.append(para)
            current_tokens += para_tokens

        # Don't forget the last chunk
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks

    def split_to_chunk_objects(self, text: str) -> List[Chunk]:
        """
        Split text and return Chunk objects with metadata.

        Args:
            text: Text to split.

        Returns:
            List of Chunk objects.
        """
        chunk_texts = self.split_by_semantic(text)

        chunks = []
        for i, chunk_text in enumerate(chunk_texts):
            chunks.append(Chunk(
                text=chunk_text,
                index=i,
                token_count=self.count_tokens(chunk_text),
            ))

        return chunks

    def _split_paragraphs(self, text: str) -> List[str]:
        """
        Split text into paragraphs.

        Splits on:
        - Double newlines
        - Markdown headings (keeps heading with following content)

        Args:
            text: Text to split.

        Returns:
            List of paragraphs.
        """
        # First, normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # Split on double newlines, but preserve heading groups
        # Use regex to split while keeping headings with their content
        parts = re.split(r'\n\s*\n', text)

        paragraphs = []
        current_section: List[str] = []

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Check if this is a heading
            if re.match(r'^#{1,6}\s+', part):
                # If we have accumulated content, save it
                if current_section:
                    paragraphs.append("\n\n".join(current_section))
                    current_section = []
                # Start new section with heading
                current_section.append(part)
            else:
                # Regular paragraph
                if current_section:
                    current_section.append(part)
                else:
                    paragraphs.append(part)

        # Don't forget remaining section
        if current_section:
            paragraphs.append("\n\n".join(current_section))

        return [p for p in paragraphs if p.strip()]

    def _split_large_paragraph(self, paragraph: str) -> List[str]:
        """
        Split a large paragraph that exceeds token limit.

        Args:
            paragraph: Large paragraph to split.

        Returns:
            List of smaller chunks.
        """
        # Try to split by sentences
        sentences = self._split_sentences(paragraph)

        if len(sentences) <= 1:
            # Can't split by sentences, split by character count
            return self._split_by_chars(paragraph)

        chunks = []
        current_chunk: List[str] = []
        current_tokens = 0

        for sentence in sentences:
            sent_tokens = self.count_tokens(sentence)

            if sent_tokens > self.max_tokens:
                # Even a single sentence is too long, split by chars
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_tokens = 0
                char_chunks = self._split_by_chars(sentence)
                chunks.extend(char_chunks[:-1])
                current_chunk = [char_chunks[-1]]
                current_tokens = self.count_tokens(char_chunks[-1])
                continue

            if current_tokens + sent_tokens > self.max_tokens and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_tokens = 0

            current_chunk.append(sentence)
            current_tokens += sent_tokens

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.

        Args:
            text: Text to split.

        Returns:
            List of sentences.
        """
        # Simple sentence splitting - handles English and Chinese
        # English: . ! ?
        # Chinese: 。！？
        pattern = r'(?<=[.!?。！？])\s+'
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip()]

    def _split_by_chars(self, text: str) -> List[str]:
        """
        Split text by character count when no other split is possible.

        Args:
            text: Text to split.

        Returns:
            List of text chunks.
        """
        # Estimate chars per token (roughly 4 for English, 1.5 for Chinese)
        # Use a conservative estimate
        chars_per_token = 3
        max_chars = self.max_tokens * chars_per_token

        chunks = []
        while text:
            if len(text) <= max_chars:
                chunks.append(text)
                break

            # Find a good split point
            split_point = max_chars

            # Try to split at whitespace
            last_space = text[:split_point].rfind(' ')
            if last_space > split_point // 2:
                split_point = last_space

            chunks.append(text[:split_point].strip())
            text = text[split_point:].strip()

        return chunks

    def _get_overlap_sentences(self, paragraphs: List[str]) -> List[str]:
        """
        Get sentences for overlap from the end of paragraphs.

        Args:
            paragraphs: List of paragraphs to get overlap from.

        Returns:
            List of overlap sentences (as paragraphs).
        """
        if not paragraphs or self.overlap_sentences <= 0:
            return []

        # Get the last paragraph and extract sentences
        last_para = paragraphs[-1]
        sentences = self._split_sentences(last_para)

        if len(sentences) <= self.overlap_sentences:
            return [last_para]

        # Return the last N sentences as a single paragraph
        overlap_text = " ".join(sentences[-self.overlap_sentences:])
        return [overlap_text]

    def estimate_chunks(self, text: str) -> Tuple[int, int]:
        """
        Estimate the number of chunks and total tokens.

        Args:
            text: Text to estimate.

        Returns:
            Tuple of (estimated_chunks, total_tokens).
        """
        total_tokens = self.count_tokens(text)

        if total_tokens <= self.max_tokens:
            return 1, total_tokens

        # Rough estimate considering overlap
        overlap_tokens = self.max_tokens * 0.1  # Assume 10% overlap
        effective_tokens_per_chunk = self.max_tokens - overlap_tokens
        estimated_chunks = max(1, int(total_tokens / effective_tokens_per_chunk) + 1)

        return estimated_chunks, total_tokens
