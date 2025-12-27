"""Helper functions for building API response models."""

from src.repositories.models import (
    BookResponse,
    BookSource,
    ContentItemResponse,
    ContentWithRelatedItemsResponse,
    NoteContent,
    NoteRead,
    NoteResponse,
    NoteWithRelatedNotesResponse,
    URLChunkContent,
    URLChunkRead,
    URLResponse,
    URLSource,
)


def build_note_response(note: NoteRead) -> NoteResponse:
    """Build a NoteResponse from a NoteRead model."""
    return NoteResponse(
        id=note.id,
        content=note.content,
        created_at=note.created_at,
    )


def build_note_with_related_notes_response(
    book: BookResponse,
    note: NoteRead,
    related_notes: list[NoteRead],
) -> NoteWithRelatedNotesResponse:
    """Build metadata response with book, note, and related notes."""
    return NoteWithRelatedNotesResponse(
        book=book,
        note=build_note_response(note),
        related_notes=[build_note_response(n) for n in related_notes],
    )


# Unified Response Builders (for /random endpoint)


def build_source_response_from_book(book: BookResponse) -> BookSource:
    """Build a BookSource from a BookResponse."""
    return BookSource(
        id=book.id,
        title=book.title,
        type="book",
        author=book.author,
        created_at=book.created_at,
    )


def build_source_response_from_url(url: URLResponse) -> URLSource:
    """Build a URLSource from a URLResponse."""
    return URLSource(
        id=url.id,
        title=url.title,
        type="url",
        url=url.url,
        created_at=url.created_at,
    )


def build_content_item_from_note(note: NoteRead) -> NoteContent:
    """Build a NoteContent from a NoteRead."""
    return NoteContent(
        id=note.id,
        content_type="note",
        content=note.content,
        created_at=note.created_at,
    )


def build_content_item_from_chunk(chunk: URLChunkRead) -> URLChunkContent:
    """Build a URLChunkContent from a URLChunkRead."""
    return URLChunkContent(
        id=chunk.id,
        content_type="url_chunk",
        content=chunk.content,
        is_summary=chunk.is_summary,
        chunk_order=chunk.chunk_order,
        created_at=chunk.created_at,
    )


def build_unified_response_for_note(
    book: BookResponse,
    note: NoteRead,
    related_notes: list[NoteRead],
) -> ContentWithRelatedItemsResponse:
    """Build unified response for a note with related notes."""
    return ContentWithRelatedItemsResponse(
        source=build_source_response_from_book(book),
        content=build_content_item_from_note(note),
        related_items=[build_content_item_from_note(n) for n in related_notes],
    )


def build_unified_response_for_chunk(
    url: URLResponse,
    chunk: URLChunkRead,
    related_chunks: list[URLChunkRead],
) -> ContentWithRelatedItemsResponse:
    """Build unified response for a URL chunk with related chunks."""
    return ContentWithRelatedItemsResponse(
        source=build_source_response_from_url(url),
        content=build_content_item_from_chunk(chunk),
        related_items=[build_content_item_from_chunk(c) for c in related_chunks],
    )
