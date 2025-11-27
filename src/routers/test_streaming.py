"""
Tests for streaming SSE endpoints in notes.py

These tests verify the Server-Sent Events (SSE) streaming functionality
for both random note and specific note endpoints.
"""

import json
import pytest
from httpx import AsyncClient, ASGITransport
from typing import Callable, Generator, Any
from ..main import app
from ..dependencies import (
    get_book_repository,
    get_note_repository,
    get_llm_client,
    get_evaluation_repository,
)
from ..repositories.models import NoteCreate, BookCreate
from ..test_utils import (
    StubNoteRepository,
    StubBookRepository,
    StubEvaluationRepository,
    StubLLMClient,
)

# Type alias for the setup function returned by fixture
SetupFunction = Callable[
    [list[str] | None],
    tuple[
        StubNoteRepository, StubBookRepository, StubEvaluationRepository, StubLLMClient
    ],
]


evaluation_response = (
    "Score: 0.85\nEvaluation: Well-structured and informative response."
)


@pytest.fixture
def setup_dependencies() -> Generator[SetupFunction, None, None]:
    """Fixture to set up dependency overrides with proper cleanup"""

    def _setup(
        llm_responses: list[str] | None = None,
    ) -> tuple[
        StubNoteRepository, StubBookRepository, StubEvaluationRepository, StubLLMClient
    ]:
        if llm_responses is None:
            llm_responses = ["Default additional context", evaluation_response]

        # Create fresh instances for each test call
        book_repo = StubBookRepository()
        note_repo = StubNoteRepository()
        evaluation_repo = StubEvaluationRepository()
        llm_client = StubLLMClient(responses=llm_responses)

        # Override dependencies
        app.dependency_overrides[get_book_repository] = lambda: book_repo
        app.dependency_overrides[get_note_repository] = lambda: note_repo
        app.dependency_overrides[get_llm_client] = lambda: llm_client
        app.dependency_overrides[get_evaluation_repository] = lambda: evaluation_repo

        return note_repo, book_repo, evaluation_repo, llm_client

    yield _setup

    # Cleanup
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_random_note_stream_success(setup_dependencies: SetupFunction):
    """Test streaming random note endpoint returns proper SSE events"""
    note_repo, book_repo, _, _ = setup_dependencies(
        ["This is additional context about the note", evaluation_response]
    )

    # Create a book
    book = BookCreate(title="Test Book", author="Test Author")
    book = book_repo.add(book)

    # Add notes
    note1 = NoteCreate(
        content="Primary note content",
        content_hash="hash1",
        book_id=book.id,
    )
    note2 = NoteCreate(
        content="Related note content",
        content_hash="hash2",
        book_id=book.id,
    )
    added_note1 = note_repo.add(note1)
    note_repo.add(note2)

    # Make streaming request - note the correct path is /random/stream
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "GET", "/random/stream", headers={"Accept": "text/event-stream"}
        ) as response:
            assert response.status_code == 200
            assert (
                response.headers["content-type"] == "text/event-stream; charset=utf-8"
            )

            events: list[dict[str, Any]] = []
            event_type: str = ""
            async for line in response.aiter_lines():
                if line.startswith("event: "):
                    event_type = line[7:]  # Remove "event: " prefix
                elif line.startswith("data: "):
                    data = json.loads(line[6:])  # Remove "data: " prefix
                    events.append({"type": event_type, "data": data})

            # Verify event sequence: metadata -> context_chunk(s) -> context_complete
            assert len(events) >= 2
            assert events[0]["type"] == "metadata"
            assert events[-1]["type"] == "context_complete"

            # Verify metadata event contains expected structure
            metadata = events[0]["data"]
            assert "book" in metadata
            assert metadata["book"]["id"] == book.id
            assert metadata["book"]["title"] == "Test Book"
            assert "note" in metadata
            assert metadata["note"]["id"] == added_note1.id
            assert metadata["note"]["content"] == "Primary note content"
            assert "related_notes" in metadata
            assert len(metadata["related_notes"]) == 1

            # Verify content events contain chunks
            content_events = [e for e in events if e["type"] == "context_chunk"]
            assert len(content_events) > 0
            # Reconstruct the full content from chunks
            full_content = "".join([e["data"]["content"] for e in content_events])
            assert "This is additional context about the note" in full_content


@pytest.mark.asyncio
async def test_get_random_note_stream_no_notes(setup_dependencies: SetupFunction):
    """Test streaming random note endpoint when no notes exist"""
    setup_dependencies(["additional context", evaluation_response])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/random/stream")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "No notes found"


@pytest.mark.asyncio
async def test_get_note_with_context_stream_success(setup_dependencies: SetupFunction):
    """Test streaming specific note endpoint returns proper SSE events"""
    note_repo, book_repo, _, _ = setup_dependencies(
        ["Specific note context", evaluation_response]
    )

    # Create a book
    book = BookCreate(title="Test Book", author="Test Author")
    book = book_repo.add(book)

    # Add notes
    note1 = NoteCreate(
        content="Specific note content",
        content_hash="hash1",
        book_id=book.id,
    )
    note2 = NoteCreate(
        content="Related note content",
        content_hash="hash2",
        book_id=book.id,
    )
    added_note1 = note_repo.add(note1)
    note_repo.add(note2)

    # Make streaming request for specific note - note the correct path
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "GET",
            f"/books/{book.id}/notes/{added_note1.id}/stream",
            headers={"Accept": "text/event-stream"},
        ) as response:
            assert response.status_code == 200
            assert (
                response.headers["content-type"] == "text/event-stream; charset=utf-8"
            )

            events: list[dict[str, Any]] = []
            event_type = None
            async for line in response.aiter_lines():
                if line.startswith("event: "):
                    event_type = line[7:]
                elif line.startswith("data: "):
                    data = json.loads(line[6:])
                    events.append({"type": event_type, "data": data})

            # Verify event sequence
            assert len(events) >= 2
            assert events[0]["type"] == "metadata"
            assert events[-1]["type"] == "context_complete"

            # Verify metadata for specific note
            metadata = events[0]["data"]
            assert metadata["book"]["id"] == book.id
            assert metadata["note"]["id"] == added_note1.id
            assert metadata["note"]["content"] == "Specific note content"
            assert len(metadata["related_notes"]) == 1

            # Verify content streaming
            content_events = [e for e in events if e["type"] == "context_chunk"]
            assert len(content_events) > 0
            full_content = "".join([e["data"]["content"] for e in content_events])
            assert "Specific note context" in full_content


@pytest.mark.asyncio
async def test_get_note_with_context_stream_note_not_found(
    setup_dependencies: SetupFunction,
):
    """Test streaming specific note endpoint when note doesn't exist"""
    _, book_repo, _, _ = setup_dependencies(None)

    # Create a book
    book = BookCreate(title="Test Book", author="Test Author")
    book = book_repo.add(book)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/books/{book.id}/notes/999/stream")
        assert response.status_code == 404
        data = response.json()
        assert (
            data["detail"] == "Note not found or doesn't belong to the specified book"
        )


@pytest.mark.asyncio
async def test_get_note_with_context_stream_wrong_book(
    setup_dependencies: SetupFunction,
):
    """Test streaming when note belongs to different book"""
    note_repo, book_repo, _, _ = setup_dependencies(None)

    # Create two books
    book1 = BookCreate(title="Book 1", author="Author 1")
    book2 = BookCreate(title="Book 2", author="Author 2")
    book1 = book_repo.add(book1)
    book2 = book_repo.add(book2)

    # Add note to book1
    note = NoteCreate(
        content="Note in book 1",
        content_hash="hash1",
        book_id=book1.id,
    )
    added_note = note_repo.add(note)

    # Try to access the note from book2 (should fail)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/books/{book2.id}/notes/{added_note.id}/stream")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_streaming_error_handling(setup_dependencies: SetupFunction):
    """Test that errors during streaming are handled gracefully"""
    note_repo, book_repo, _, llm_client = setup_dependencies(
        ["Should not be called", evaluation_response]
    )

    # Make the LLM client fail
    llm_client.should_fail = True

    # Create a book and note
    book = BookCreate(title="Error Test", author="Test Author")
    book = book_repo.add(book)
    note = NoteCreate(content="Error test note", content_hash="hash1", book_id=book.id)
    note_repo.add(note)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "GET", "/random/stream", headers={"Accept": "text/event-stream"}
        ) as response:
            assert response.status_code == 200

            events: list[dict[str, Any]] = []
            event_type = None
            async for line in response.aiter_lines():
                if line.startswith("event: "):
                    event_type = line[7:]
                elif line.startswith("data: "):
                    data = json.loads(line[6:])
                    events.append({"type": event_type, "data": data})

            # Should get metadata and then an error event
            assert events[0]["type"] == "metadata"
            assert events[1]["type"] == "error"
            assert len(events) == 2
            assert "detail" in events[1]["data"]
