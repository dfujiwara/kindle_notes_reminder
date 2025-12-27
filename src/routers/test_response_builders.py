"""
Tests for unified response builders in response_builders.py

These tests verify that builder functions correctly map domain models
to unified response models using discriminated unions.
"""

from datetime import datetime, timezone
import pytest
from ..repositories.models import (
    BookResponse,
    NoteRead,
    URLResponse,
    URLChunkRead,
    BookSource,
    URLSource,
    NoteContent,
    URLChunkContent,
)
from .response_builders import (
    build_source_response_from_book,
    build_source_response_from_url,
    build_content_item_from_note,
    build_content_item_from_chunk,
    build_unified_response_for_note,
    build_unified_response_for_chunk,
)


@pytest.fixture
def book_response() -> BookResponse:
    """Create a test BookResponse."""
    return BookResponse(
        id=1,
        title="Test Book",
        author="Test Author",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def book_with_custom_values() -> BookResponse:
    """Create a BookResponse with custom values for detailed testing."""
    return BookResponse(
        id=42,
        title="The Pragmatic Programmer",
        author="Hunt & Thomas",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def note_read() -> NoteRead:
    """Create a test NoteRead."""
    return NoteRead(
        id=1,
        content="Test note content",
        content_hash="hash_1",
        book_id=1,
        embedding=None,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def related_notes() -> list[NoteRead]:
    """Create related NoteRead fixtures."""
    return [
        NoteRead(
            id=2,
            content="Good naming saves debugging time.",
            content_hash="hash_2",
            book_id=1,
            embedding=None,
            created_at=datetime.now(timezone.utc),
        ),
        NoteRead(
            id=3,
            content="Comments should explain why, not what.",
            content_hash="hash_3",
            book_id=1,
            embedding=None,
            created_at=datetime.now(timezone.utc),
        ),
    ]


@pytest.fixture
def url_response() -> URLResponse:
    """Create a test URLResponse."""
    created_at = datetime.now(timezone.utc)
    return URLResponse(
        id=1,
        url="https://example.com",
        title="Example",
        fetched_at=created_at,
        created_at=created_at,
    )


@pytest.fixture
def url_with_custom_values() -> URLResponse:
    """Create a URLResponse with custom values for detailed testing."""
    created_at = datetime.now(timezone.utc)
    return URLResponse(
        id=5,
        url="https://example.com/guide",
        title="Complete Guide",
        fetched_at=created_at,
        created_at=created_at,
    )


@pytest.fixture
def url_chunk_read() -> URLChunkRead:
    """Create a test URLChunkRead."""
    return URLChunkRead(
        id=1,
        content="Test chunk content",
        content_hash="hash_1",
        url_id=1,
        chunk_order=0,
        is_summary=False,
        embedding=None,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def url_chunk_summary() -> URLChunkRead:
    """Create a test URLChunkRead summary."""
    return URLChunkRead(
        id=1,
        content="Summary of the URL content.",
        content_hash="hash_summary",
        url_id=1,
        chunk_order=0,
        is_summary=True,
        embedding=None,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def related_chunks() -> list[URLChunkRead]:
    """Create related URLChunkRead fixtures."""
    return [
        URLChunkRead(
            id=2,
            content="First section details.",
            content_hash="hash_chunk_1",
            url_id=1,
            chunk_order=1,
            is_summary=False,
            embedding=None,
            created_at=datetime.now(timezone.utc),
        ),
        URLChunkRead(
            id=3,
            content="Second section details.",
            content_hash="hash_chunk_2",
            url_id=1,
            chunk_order=2,
            is_summary=False,
            embedding=None,
            created_at=datetime.now(timezone.utc),
        ),
    ]


# Tests for Source Response Builders


def test_build_source_response_from_book(book_response: BookResponse):
    """Test conversion of BookResponse to BookSource."""
    result = build_source_response_from_book(book_response)
    assert result.id == book_response.id
    assert result.title == book_response.title
    assert result.author == book_response.author
    assert result.type == "book"
    assert result.created_at == book_response.created_at


def test_build_source_response_from_url(url_response: URLResponse):
    """Test conversion of URLResponse to URLSource."""
    result = build_source_response_from_url(url_response)
    assert result.id == url_response.id
    assert result.title == url_response.title
    assert result.url == url_response.url
    assert result.type == "url"
    assert result.created_at == url_response.created_at


# Tests for Content Item Builders


def test_build_content_item_from_note(note_read: NoteRead):
    """Test conversion of NoteRead to NoteContent."""
    result = build_content_item_from_note(note_read)
    assert result.id == note_read.id
    assert result.content == note_read.content
    assert result.content_type == "note"
    assert result.created_at == note_read.created_at


def test_build_content_item_from_chunk(url_chunk_read: URLChunkRead):
    """Test conversion of URLChunkRead to URLChunkContent."""
    result = build_content_item_from_chunk(url_chunk_read)
    assert result.id == url_chunk_read.id
    assert result.content == url_chunk_read.content
    assert result.content_type == "url_chunk"
    assert result.chunk_order == url_chunk_read.chunk_order
    assert result.is_summary is False


def test_build_content_item_from_chunk_summary(url_chunk_summary: URLChunkRead):
    """Test conversion of URLChunkRead summary to URLChunkContent."""
    result = build_content_item_from_chunk(url_chunk_summary)
    assert result.id == url_chunk_summary.id
    assert result.is_summary is True
    assert result.chunk_order == 0
    assert result.content == url_chunk_summary.content


# Tests for Unified Response Builders


def test_build_unified_response_for_note(
    book_with_custom_values: BookResponse,
    note_read: NoteRead,
    related_notes: list[NoteRead],
):
    """Test building unified response for a note with related notes."""
    result = build_unified_response_for_note(
        book_with_custom_values, note_read, related_notes
    )

    assert isinstance(result.source, BookSource)
    assert result.source.id == book_with_custom_values.id
    assert result.source.title == book_with_custom_values.title
    assert result.source.author == book_with_custom_values.author
    assert result.source.type == "book"

    assert isinstance(result.content, NoteContent)
    assert result.content.id == note_read.id
    assert result.content.content == note_read.content
    assert result.content.content_type == "note"

    assert len(result.related_items) == 2
    assert all(isinstance(item, NoteContent) for item in result.related_items)
    assert result.related_items[0].id == related_notes[0].id
    assert result.related_items[1].id == related_notes[1].id


def test_build_unified_response_for_note_no_related(
    book_response: BookResponse,
    note_read: NoteRead,
):
    """Test building unified response for a note with no related notes."""
    result = build_unified_response_for_note(book_response, note_read, [])

    assert isinstance(result.source, BookSource)
    assert isinstance(result.content, NoteContent)
    assert result.related_items == []


def test_build_unified_response_for_chunk(
    url_with_custom_values: URLResponse,
    url_chunk_summary: URLChunkRead,
    related_chunks: list[URLChunkRead],
):
    """Test building unified response for a URL chunk with related chunks."""
    result = build_unified_response_for_chunk(
        url_with_custom_values, url_chunk_summary, related_chunks
    )

    assert isinstance(result.source, URLSource)
    assert result.source.id == url_with_custom_values.id
    assert result.source.url == url_with_custom_values.url
    assert result.source.title == url_with_custom_values.title
    assert result.source.type == "url"

    assert isinstance(result.content, URLChunkContent)
    assert result.content.id == url_chunk_summary.id
    assert result.content.is_summary is True
    assert result.content.chunk_order == 0
    assert result.content.content_type == "url_chunk"

    assert len(result.related_items) == 2
    assert all(isinstance(item, URLChunkContent) for item in result.related_items)
