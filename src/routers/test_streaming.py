"""
Tests for streaming SSE endpoints.

These tests verify the Server-Sent Events (SSE) streaming functionality
for the specific note endpoint (/books/{book_id}/notes/{note_id} in notes.py).
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

    # Make streaming request for specific note
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "GET",
            f"/books/{book.id}/notes/{added_note1.id}",
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
        response = await client.get(f"/books/{book.id}/notes/999")
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
        response = await client.get(f"/books/{book2.id}/notes/{added_note.id}")
        assert response.status_code == 404
