"""
Test utilities and stub implementations for testing.

This module provides reusable stub implementations of repositories and clients
that can be used across different test files.
"""

from src.repositories.models import (
    BookCreate,
    BookResponse,
    NoteCreate,
    NoteRead,
    Evaluation,
    URLCreate,
    URLResponse,
    URLChunkCreate,
    URLChunkRead,
)
from src.repositories.interfaces import (
    BookRepositoryInterface,
    EvaluationRepositoryInterface,
    NoteRepositoryInterface,
)
from src.url_ingestion.repositories.interfaces import (
    URLRepositoryInterface,
    URLChunkRepositoryInterface,
)
from src.embedding_interface import EmbeddingClientInterface, EmbeddingError
from src.llm_interface import LLMClientInterface, LLMError
from src.url_ingestion.url_fetcher import (
    URLFetchError,
    FetchedContent,
)
from src.types import Embedding
from src.config import settings
from datetime import datetime, timezone
from typing import AsyncGenerator


class StubBookRepository(BookRepositoryInterface):
    """Stub implementation of BookRepository for testing."""

    def __init__(self, include_sample_book: bool = False):
        self.books: list[BookResponse] = []
        if include_sample_book:
            sample_book = BookResponse(
                id=1,
                title="The Pragmatic Programmer",
                author="David Thomas",
                created_at=datetime.now(timezone.utc),
            )
            self.books.append(sample_book)

    def add(self, book: BookCreate) -> BookResponse:
        book_read = BookResponse(
            id=len(self.books) + 1,
            title=book.title,
            author=book.author,
            created_at=datetime.now(timezone.utc),
        )
        self.books.append(book_read)
        return book_read

    def get(self, book_id: int) -> BookResponse | None:
        return next((book for book in self.books if book.id == book_id), None)

    def list_books(self) -> list[BookResponse]:
        return self.books

    def get_by_ids(self, book_ids: list[int]) -> list[BookResponse]:
        return [b for b in self.books if b.id in book_ids]

    def delete(self, book_id: int) -> None:
        self.books = [book for book in self.books if book.id != book_id]


class StubNoteRepository(NoteRepositoryInterface):
    """Stub implementation of NoteRepository for testing."""

    def __init__(self):
        self.notes: list[NoteRead] = []

    def add(self, note: NoteCreate) -> NoteRead:
        note_read = NoteRead(
            id=len(self.notes) + 1,
            created_at=datetime.now(timezone.utc),
            book_id=note.book_id,
            content=note.content,
            content_hash=note.content_hash,
            embedding=note.embedding,
        )
        self.notes.append(note_read)
        return note_read

    def get(self, note_id: int, book_id: int) -> NoteRead | None:
        return next(
            (
                note
                for note in self.notes
                if note.id == note_id and note.book_id == book_id
            ),
            None,
        )

    def get_by_id(self, note_id: int) -> NoteRead | None:
        return next((note for note in self.notes if note.id == note_id), None)

    def list_notes(self) -> list[NoteRead]:
        return self.notes

    def get_by_book_id(self, book_id: int) -> list[NoteRead]:
        return [note for note in self.notes if note.book_id == book_id]

    def delete(self, note_id: int) -> None:
        self.notes = [note for note in self.notes if note.id != note_id]

    def get_random(self) -> NoteRead | None:
        return self.notes[0] if self.notes else None

    def find_similar_notes(
        self, note: NoteRead, limit: int = 5, similarity_threshold: float = 0.3
    ) -> list[NoteRead]:
        """
        Stub implementation of find_similar_notes.
        Returns first `limit` notes from the same book (excluding the input note).
        """
        return [n for n in self.notes if n.id != note.id and n.book_id == note.book_id][
            :limit
        ]

    def search_notes_by_embedding(
        self, embedding: Embedding, limit: int = 10, similarity_threshold: float = 0.5
    ) -> list[NoteRead]:
        """
        Stub implementation of search_notes_by_embedding.
        Returns first `limit` notes from all books.
        """
        return self.notes[:limit]

    def get_note_counts_by_book_ids(self, book_ids: list[int]) -> dict[int, int]:
        result: dict[int, int] = {}
        book_ids_set = set(book_ids)
        for note in self.notes:
            if note.book_id in book_ids_set:
                result[note.book_id] = result.get(note.book_id, 0) + 1
        return result

    def count_with_embeddings(self) -> int:
        return len([n for n in self.notes if n.embedding is not None])


class StubEvaluationRepository(EvaluationRepositoryInterface):
    def __init__(self):
        self.evaluations: list[Evaluation] = []

    def add(self, evaluation: Evaluation) -> Evaluation:
        evaluation.id = len(self.evaluations) + 1  # Simulate auto-increment ID
        self.evaluations.append(evaluation)
        return evaluation

    def get_by_note_id(self, note_id: int) -> list[Evaluation]:
        return [eval for eval in self.evaluations if eval.note_id == note_id]


class StubURLRepository(URLRepositoryInterface):
    """Stub implementation of URLRepository for testing."""

    def __init__(self):
        self.urls: list[URLResponse] = []

    def add(self, url: URLCreate) -> URLResponse:
        # Check for duplicate URL
        existing = self.get_by_url(url.url)
        if existing:
            return existing

        url_response = URLResponse(
            id=len(self.urls) + 1,
            url=url.url,
            title=url.title,
            fetched_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        self.urls.append(url_response)
        return url_response

    def get(self, url_id: int) -> URLResponse | None:
        return next((url for url in self.urls if url.id == url_id), None)

    def get_by_url(self, url: str) -> URLResponse | None:
        return next((u for u in self.urls if u.url == url), None)

    def get_by_ids(self, url_ids: list[int]) -> list[URLResponse]:
        return [url for url in self.urls if url.id in url_ids]

    def list_urls(self) -> list[URLResponse]:
        return self.urls

    def delete(self, url_id: int) -> None:
        self.urls = [url for url in self.urls if url.id != url_id]


class StubURLChunkRepository(URLChunkRepositoryInterface):
    """Stub implementation of URLChunkRepository for testing."""

    def __init__(self):
        self.chunks: list[URLChunkRead] = []

    def add(self, chunk: URLChunkCreate) -> URLChunkRead:
        # Check for duplicate content_hash
        existing = next(
            (c for c in self.chunks if c.content_hash == chunk.content_hash), None
        )
        if existing:
            return existing

        chunk_read = URLChunkRead(
            id=len(self.chunks) + 1,
            created_at=datetime.now(timezone.utc),
            url_id=chunk.url_id,
            content=chunk.content,
            content_hash=chunk.content_hash,
            chunk_order=chunk.chunk_order,
            is_summary=chunk.is_summary,
            embedding=chunk.embedding,
        )
        self.chunks.append(chunk_read)
        return chunk_read

    def get(self, chunk_id: int, url_id: int) -> URLChunkRead | None:
        return next(
            (
                chunk
                for chunk in self.chunks
                if chunk.id == chunk_id and chunk.url_id == url_id
            ),
            None,
        )

    def get_by_id(self, chunk_id: int) -> URLChunkRead | None:
        return next((chunk for chunk in self.chunks if chunk.id == chunk_id), None)

    def get_random(self) -> URLChunkRead | None:
        return self.chunks[0] if self.chunks else None

    def get_by_url_id(self, url_id: int) -> list[URLChunkRead]:
        return sorted(
            [chunk for chunk in self.chunks if chunk.url_id == url_id],
            key=lambda c: c.chunk_order,
        )

    def find_similar_chunks(
        self, chunk: URLChunkRead, limit: int = 5
    ) -> list[URLChunkRead]:
        """
        Stub implementation of find_similar_chunks.
        Returns first `limit` chunks from the same URL (excluding the input chunk).
        """
        return [
            c for c in self.chunks if c.id != chunk.id and c.url_id == chunk.url_id
        ][:limit]

    def search_chunks_by_embedding(
        self, embedding: Embedding, limit: int = 10, similarity_threshold: float = 0.5
    ) -> list[URLChunkRead]:
        """
        Stub implementation of search_chunks_by_embedding.
        Returns first `limit` chunks from all URLs.
        """
        return self.chunks[:limit]

    def get_chunk_counts_by_url_ids(self, url_ids: list[int]) -> dict[int, int]:
        result: dict[int, int] = {}
        url_ids_set = set(url_ids)
        for chunk in self.chunks:
            if chunk.url_id in url_ids_set:
                result[chunk.url_id] = result.get(chunk.url_id, 0) + 1
        return result

    def count_with_embeddings(self) -> int:
        return len([c for c in self.chunks if c.embedding is not None])

    def delete_by_url_id(self, url_id: int) -> None:
        self.chunks = [c for c in self.chunks if c.url_id != url_id]


class StubURLFetcher:
    """Stub implementation of URL fetcher for testing."""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.calls: list[str] = []  # Track calls for verification

    async def __call__(
        self, url: str, max_content_size: int | None = None
    ) -> FetchedContent:
        """Stub fetcher that can simulate success or failure."""
        self.calls.append(url)

        if self.should_fail:
            raise URLFetchError("Failed to fetch URL")

        # Return minimal successful fetch result
        return FetchedContent(
            url=url, title=f"Test: {url}", content="Test content from stub fetcher."
        )


class StubEmbeddingClient(EmbeddingClientInterface):
    """Stub implementation of EmbeddingClient for testing."""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    async def generate_embedding(self, content: str) -> list[float]:
        if self.should_fail:
            raise EmbeddingError("Simulated embedding generation failure")
        # Return a simple mock embedding using configured dimension
        return [0.1] * settings.embedding_dimension


class StubLLMClient(LLMClientInterface):
    """Stub implementation of LLMClient for testing."""

    def __init__(
        self, responses: list[str] = ["Test LLM response"], should_fail: bool = False
    ):
        self.responses = responses
        self.should_fail = should_fail
        self.call_count = 0

    async def get_response(
        self, prompt: str, instruction: str, json_mode: bool = False
    ) -> str:
        response = self.responses[self.call_count]
        self.call_count += 1
        if self.should_fail:
            raise LLMError("Simulated LLM generation failure")
        return response

    async def get_response_stream(
        self, prompt: str, instruction: str
    ) -> AsyncGenerator[str, None]:
        """Stub streaming response that yields the response in chunks."""
        response = await self.get_response(prompt, instruction)
        # Yield response in chunks (simulate streaming)
        chunk_size = 10
        for i in range(0, len(response), chunk_size):
            yield response[i : i + chunk_size]
