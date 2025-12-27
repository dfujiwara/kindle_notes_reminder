"""
Tests for unified response builders in response_builders.py

These tests verify that builder functions correctly map domain models
to unified response models using discriminated unions.
"""

from datetime import datetime, timezone
from ..repositories.models import (
    BookResponse,
    NoteRead,
    URLResponse,
    URLChunkRead,
    BookSource,
    URLSource,
    NoteContent,
    URLChunkContent,
    ContentWithRelatedItemsResponse,
)
from .response_builders import (
    build_source_response_from_book,
    build_source_response_from_url,
    build_content_item_from_note,
    build_content_item_from_chunk,
    build_unified_response_for_note,
    build_unified_response_for_chunk,
)


# Test Data Fixtures
def create_book_response(
    id: int = 1,
    title: str = "Test Book",
    author: str = "Test Author",
    created_at: datetime | None = None,
) -> BookResponse:
    """Helper to create test BookResponse."""
    if created_at is None:
        created_at = datetime.now(timezone.utc)
    return BookResponse(id=id, title=title, author=author, created_at=created_at)


def create_note_read(
    id: int = 1,
    content: str = "Test note content",
    created_at: datetime | None = None,
) -> NoteRead:
    """Helper to create test NoteRead."""
    if created_at is None:
        created_at = datetime.now(timezone.utc)
    return NoteRead(
        id=id,
        content=content,
        content_hash=f"hash_{id}",
        book_id=1,
        embedding=None,
        created_at=created_at,
    )


def create_url_response(
    id: int = 1,
    url: str = "https://example.com",
    title: str = "Example",
    created_at: datetime | None = None,
) -> URLResponse:
    """Helper to create test URLResponse."""
    if created_at is None:
        created_at = datetime.now(timezone.utc)
    fetched_at = datetime.now(timezone.utc)
    return URLResponse(
        id=id,
        url=url,
        title=title,
        fetched_at=fetched_at,
        created_at=created_at,
    )


def create_url_chunk_read(
    id: int = 1,
    content: str = "Test chunk content",
    chunk_order: int = 0,
    is_summary: bool = False,
    created_at: datetime | None = None,
) -> URLChunkRead:
    """Helper to create test URLChunkRead."""
    if created_at is None:
        created_at = datetime.now(timezone.utc)
    return URLChunkRead(
        id=id,
        content=content,
        content_hash=f"hash_{id}",
        url_id=1,
        chunk_order=chunk_order,
        is_summary=is_summary,
        embedding=None,
        created_at=created_at,
    )


# Tests for Source Response Builders


def test_build_source_response_from_book():
    """Test conversion of BookResponse to BookSource."""
    created_at = datetime.now(timezone.utc)
    book = create_book_response(
        id=42,
        title="My Book",
        author="Jane Doe",
        created_at=created_at,
    )

    result = build_source_response_from_book(book)

    assert isinstance(result, BookSource)
    assert result.id == 42
    assert result.title == "My Book"
    assert result.author == "Jane Doe"
    assert result.type == "book"
    assert result.created_at == created_at


def test_build_source_response_from_url():
    """Test conversion of URLResponse to URLSource."""
    created_at = datetime.now(timezone.utc)
    url = create_url_response(
        id=99,
        url="https://test.com/article",
        title="Test Article",
        created_at=created_at,
    )

    result = build_source_response_from_url(url)

    assert isinstance(result, URLSource)
    assert result.id == 99
    assert result.title == "Test Article"
    assert result.url == "https://test.com/article"
    assert result.type == "url"
    assert result.created_at == created_at


# Tests for Content Item Builders


def test_build_content_item_from_note():
    """Test conversion of NoteRead to NoteContent."""
    created_at = datetime.now(timezone.utc)
    note = create_note_read(
        id=7,
        content="This is a highlight from a book.",
        created_at=created_at,
    )

    result = build_content_item_from_note(note)

    assert isinstance(result, NoteContent)
    assert result.id == 7
    assert result.content == "This is a highlight from a book."
    assert result.content_type == "note"
    assert result.created_at == created_at


def test_build_content_item_from_chunk():
    """Test conversion of URLChunkRead to URLChunkContent."""
    created_at = datetime.now(timezone.utc)
    chunk = create_url_chunk_read(
        id=55,
        content="This is a chunk of text from a URL.",
        chunk_order=3,
        is_summary=False,
        created_at=created_at,
    )

    result = build_content_item_from_chunk(chunk)

    assert isinstance(result, URLChunkContent)
    assert result.id == 55
    assert result.content == "This is a chunk of text from a URL."
    assert result.content_type == "url_chunk"
    assert result.chunk_order == 3
    assert result.is_summary is False
    assert result.created_at == created_at


def test_build_content_item_from_chunk_summary():
    """Test conversion of URLChunkRead summary to URLChunkContent."""
    created_at = datetime.now(timezone.utc)
    summary_chunk = create_url_chunk_read(
        id=66,
        content="Summary of the URL content.",
        chunk_order=0,
        is_summary=True,
        created_at=created_at,
    )

    result = build_content_item_from_chunk(summary_chunk)

    assert isinstance(result, URLChunkContent)
    assert result.id == 66
    assert result.is_summary is True
    assert result.chunk_order == 0
    assert result.content == "Summary of the URL content."


# Tests for Unified Response Builders


def test_build_unified_response_for_note():
    """Test building unified response for a note with related notes."""
    created_at = datetime.now(timezone.utc)
    book = create_book_response(
        id=1,
        title="The Pragmatic Programmer",
        author="Hunt & Thomas",
        created_at=created_at,
    )
    note = create_note_read(
        id=10,
        content="Always invest in code readability.",
        created_at=created_at,
    )
    related_note_1 = create_note_read(
        id=11,
        content="Good naming saves debugging time.",
        created_at=created_at,
    )
    related_note_2 = create_note_read(
        id=12,
        content="Comments should explain why, not what.",
        created_at=created_at,
    )

    result = build_unified_response_for_note(
        book, note, [related_note_1, related_note_2]
    )

    assert isinstance(result, ContentWithRelatedItemsResponse)

    # Check source
    assert isinstance(result.source, BookSource)
    assert result.source.id == 1
    assert result.source.title == "The Pragmatic Programmer"
    assert result.source.author == "Hunt & Thomas"
    assert result.source.type == "book"

    # Check main content
    assert isinstance(result.content, NoteContent)
    assert result.content.id == 10
    assert result.content.content == "Always invest in code readability."
    assert result.content.content_type == "note"

    # Check related items
    assert len(result.related_items) == 2
    assert all(isinstance(item, NoteContent) for item in result.related_items)
    assert result.related_items[0].id == 11
    assert result.related_items[1].id == 12


def test_build_unified_response_for_note_no_related():
    """Test building unified response for a note with no related notes."""
    created_at = datetime.now(timezone.utc)
    book = create_book_response(created_at=created_at)
    note = create_note_read(created_at=created_at)

    result = build_unified_response_for_note(book, note, [])

    assert isinstance(result.source, BookSource)
    assert isinstance(result.content, NoteContent)
    assert result.related_items == []


def test_build_unified_response_for_chunk():
    """Test building unified response for a URL chunk with related chunks."""
    created_at = datetime.now(timezone.utc)
    url = create_url_response(
        id=5,
        url="https://example.com/guide",
        title="Complete Guide",
        created_at=created_at,
    )
    chunk = create_url_chunk_read(
        id=50,
        content="Introduction to the topic.",
        chunk_order=0,
        is_summary=True,
        created_at=created_at,
    )
    related_chunk_1 = create_url_chunk_read(
        id=51,
        content="First section details.",
        chunk_order=1,
        is_summary=False,
        created_at=created_at,
    )
    related_chunk_2 = create_url_chunk_read(
        id=52,
        content="Second section details.",
        chunk_order=2,
        is_summary=False,
        created_at=created_at,
    )

    result = build_unified_response_for_chunk(
        url, chunk, [related_chunk_1, related_chunk_2]
    )

    assert isinstance(result, ContentWithRelatedItemsResponse)

    # Check source
    assert isinstance(result.source, URLSource)
    assert result.source.id == 5
    assert result.source.url == "https://example.com/guide"
    assert result.source.title == "Complete Guide"
    assert result.source.type == "url"

    # Check main content
    assert isinstance(result.content, URLChunkContent)
    assert result.content.id == 50
    assert result.content.is_summary is True
    assert result.content.chunk_order == 0
    assert result.content.content_type == "url_chunk"

    # Check related items
    assert len(result.related_items) == 2
    assert all(isinstance(item, URLChunkContent) for item in result.related_items)
    assert result.related_items[0].chunk_order == 1
    assert result.related_items[1].chunk_order == 2


def test_build_unified_response_for_chunk_no_related():
    """Test building unified response for a URL chunk with no related chunks."""
    created_at = datetime.now(timezone.utc)
    url = create_url_response(created_at=created_at)
    chunk = create_url_chunk_read(created_at=created_at)

    result = build_unified_response_for_chunk(url, chunk, [])

    assert isinstance(result.source, URLSource)
    assert isinstance(result.content, URLChunkContent)
    assert result.related_items == []


# Type discrimination tests


def test_unified_response_type_discrimination():
    """Test that unified responses can be correctly discriminated by type."""
    created_at = datetime.now(timezone.utc)
    book = create_book_response(created_at=created_at)
    note = create_note_read(created_at=created_at)

    note_response = build_unified_response_for_note(book, note, [])

    # Source should be BookSource (has author field)
    assert isinstance(note_response.source, BookSource)
    assert hasattr(note_response.source, "author")
    assert note_response.source.type == "book"

    # Content should be NoteContent (no is_summary field)
    assert isinstance(note_response.content, NoteContent)
    assert not hasattr(note_response.content, "is_summary")
    assert note_response.content.content_type == "note"

    # Now test chunk response
    url = create_url_response(created_at=created_at)
    chunk = create_url_chunk_read(created_at=created_at)
    chunk_response = build_unified_response_for_chunk(url, chunk, [])

    # Source should be URLSource (has url field, no author)
    assert isinstance(chunk_response.source, URLSource)
    assert hasattr(chunk_response.source, "url")
    assert not hasattr(chunk_response.source, "author")
    assert chunk_response.source.type == "url"

    # Content should be URLChunkContent (has is_summary field)
    assert isinstance(chunk_response.content, URLChunkContent)
    assert hasattr(chunk_response.content, "is_summary")
    assert chunk_response.content.content_type == "url_chunk"
