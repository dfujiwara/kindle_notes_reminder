"""
Content chunking utilities for splitting text into manageable chunks.

This module provides functions to split long text content into smaller chunks
while preserving paragraph boundaries and maintaining readability.
"""

import hashlib
from dataclasses import dataclass


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata."""

    content: str
    content_hash: str
    chunk_order: int


def chunk_text_by_paragraphs(text: str, max_chunk_size: int = 1000) -> list[TextChunk]:
    """
    Split text into chunks by paragraph boundaries.

    Splits text on double newlines (paragraph separators) and combines small
    paragraphs up to max_chunk_size. If a single paragraph exceeds max_chunk_size,
    it will be split into multiple chunks.

    Args:
        text: The text content to chunk
        max_chunk_size: Maximum size for each chunk in characters (default: 1000)

    Returns:
        List of TextChunk objects with content, hash, and order
    """
    if not text.strip():
        return []

    # Split by double newlines (paragraph separators)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    # Process paragraphs into chunks
    chunks = _process_paragraphs(paragraphs, max_chunk_size)

    # Convert to TextChunk objects with hashes
    return [
        TextChunk(
            content=chunk,
            content_hash=hashlib.sha256(chunk.encode("utf-8")).hexdigest(),
            chunk_order=i,
        )
        for i, chunk in enumerate(chunks)
    ]


def _process_paragraphs(paragraphs: list[str], max_chunk_size: int) -> list[str]:
    """
    Process paragraphs into chunks based on max_chunk_size.

    Combines small paragraphs up to max_chunk_size and splits large paragraphs
    when necessary.

    Args:
        paragraphs: List of paragraph strings
        max_chunk_size: Maximum size for each chunk

    Returns:
        List of text chunks as strings
    """
    chunks: list[str] = []
    current_chunk = ""
    paragraph_delimiter = "\n\n"
    for paragraph in paragraphs:
        # If single paragraph exceeds max size, split it
        if len(paragraph) > max_chunk_size:
            # Save any accumulated content first
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""

            # Split the large paragraph into sentences or by max size
            chunks.extend(_split_large_paragraph(paragraph, max_chunk_size))
        # If adding this paragraph would exceed max size
        elif (
            current_chunk
            and len(current_chunk) + len(paragraph) + len(paragraph_delimiter)
            > max_chunk_size
        ):
            # Save current chunk and start new one
            chunks.append(current_chunk.strip())
            current_chunk = paragraph
        else:
            # Add paragraph to current chunk
            if current_chunk:
                current_chunk += paragraph_delimiter + paragraph
            else:
                current_chunk = paragraph

    # Don't forget the last chunk
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def _split_into_sentences(paragraph: str) -> list[str]:
    sentences: list[str] = []
    for delimiter in [". ", "! ", "? "]:
        parts = paragraph.split(delimiter)
        if len(parts) > 1:
            # Reconstruct sentences with delimiter
            for _, part in enumerate(parts[:-1]):
                sentences.append(part + delimiter.rstrip())
            # Add the last part
            if parts[-1]:
                sentences.append(parts[-1])
            break
    return sentences


def _split_large_paragraph(paragraph: str, max_chunk_size: int) -> list[str]:
    """
    Split a large paragraph that exceeds max_chunk_size.

    Tries to split on sentence boundaries (. ! ?) first, falls back to
    character-based splitting if sentences are also too long.

    Args:
        paragraph: The paragraph to split
        max_chunk_size: Maximum size for each chunk

    Returns:
        List of chunk strings
    """
    # Try to split on sentence boundaries
    sentences: list[str] = _split_into_sentences(paragraph)

    # If no sentence delimiters found, treat as single sentence
    if not sentences:
        sentences = [paragraph]

    # Now combine sentences into chunks
    chunks: list[str] = []
    current_chunk = ""
    sentence_delimiter = " "

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # If single sentence exceeds max size, split by character
        if len(sentence) > max_chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""

            # Split by max_chunk_size
            for i in range(0, len(sentence), max_chunk_size):
                chunks.append(sentence[i : i + max_chunk_size])
        # If adding sentence would exceed max size
        elif (
            current_chunk
            and len(current_chunk) + len(sentence) + len(sentence_delimiter)
            > max_chunk_size
        ):
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            if current_chunk:
                current_chunk += sentence_delimiter + sentence
            else:
                current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks
