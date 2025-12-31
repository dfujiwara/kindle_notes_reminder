"""
Shared pytest fixtures for router tests.

Provides reusable dependency injection fixtures to reduce boilerplate in test files.
Each fixture returns a setup function that creates fresh stub instances and handles
dependency overrides with automatic cleanup.
"""

from typing import Generator, Callable
import pytest

from src.main import app
from src.dependencies import (
    get_book_repository,
    get_note_repository,
    get_evaluation_repository,
    get_embedding_client,
    get_llm_client,
    get_url_repository,
    get_urlchunk_repository,
)
from src.test_utils import (
    StubBookRepository,
    StubNoteRepository,
    StubEvaluationRepository,
    StubEmbeddingClient,
    StubLLMClient,
    StubURLRepository,
    StubURLChunkRepository,
)


@pytest.fixture
def setup_book_note_deps() -> Generator[Callable[..., tuple[StubBookRepository, StubNoteRepository]], None, None]:
    """
    Setup book and note repository dependencies.

    Returns a function that creates fresh stub instances and overrides deps.
    Most common pattern - used in ~15 tests.

    Usage:
        def test_something(setup_book_note_deps):
            book_repo, note_repo = setup_book_note_deps()
            # Test code here - cleanup is automatic!
    """

    def _setup(
        include_sample_book: bool = False,
    ) -> tuple[StubBookRepository, StubNoteRepository]:
        book_repo = StubBookRepository(include_sample_book=include_sample_book)
        note_repo = StubNoteRepository()

        app.dependency_overrides[get_book_repository] = lambda: book_repo
        app.dependency_overrides[get_note_repository] = lambda: note_repo

        return book_repo, note_repo

    yield _setup
    app.dependency_overrides.clear()


@pytest.fixture
def setup_search_deps() -> Generator[Callable[..., tuple[StubBookRepository, StubNoteRepository, StubEmbeddingClient]], None, None]:
    """
    Setup dependencies for search endpoints (book, note, embedding).

    Used in test_search.py (5 tests).

    Usage:
        def test_search(setup_search_deps):
            book_repo, note_repo, embedding_client = setup_search_deps()
            # Test code here - cleanup is automatic!
    """

    def _setup(
        embedding_should_fail: bool = False,
    ) -> tuple[StubBookRepository, StubNoteRepository, StubEmbeddingClient]:
        book_repo = StubBookRepository()
        note_repo = StubNoteRepository()
        embedding_client = StubEmbeddingClient(should_fail=embedding_should_fail)

        app.dependency_overrides[get_book_repository] = lambda: book_repo
        app.dependency_overrides[get_note_repository] = lambda: note_repo
        app.dependency_overrides[get_embedding_client] = lambda: embedding_client

        return book_repo, note_repo, embedding_client

    yield _setup
    app.dependency_overrides.clear()


@pytest.fixture
def setup_evaluation_deps() -> Generator[Callable[..., tuple[StubNoteRepository, StubEvaluationRepository]], None, None]:
    """
    Setup dependencies for evaluation endpoints (note, evaluation).

    Used in test_evaluations.py (3 tests).

    Usage:
        def test_evaluation(setup_evaluation_deps):
            note_repo, eval_repo = setup_evaluation_deps()
            # Test code here - cleanup is automatic!
    """

    def _setup() -> tuple[StubNoteRepository, StubEvaluationRepository]:
        note_repo = StubNoteRepository()
        eval_repo = StubEvaluationRepository()

        app.dependency_overrides[get_note_repository] = lambda: note_repo
        app.dependency_overrides[get_evaluation_repository] = lambda: eval_repo

        return note_repo, eval_repo

    yield _setup
    app.dependency_overrides.clear()


@pytest.fixture
def setup_url_deps() -> Generator[Callable[..., tuple[StubURLRepository, StubURLChunkRepository]], None, None]:
    """
    Setup dependencies for URL endpoints.

    Used in test_urls.py (5 tests).

    Usage:
        def test_url(setup_url_deps):
            url_repo, chunk_repo = setup_url_deps()
            # Test code here - cleanup is automatic!
    """

    def _setup() -> tuple[StubURLRepository, StubURLChunkRepository]:
        url_repo = StubURLRepository()
        chunk_repo = StubURLChunkRepository()

        app.dependency_overrides[get_url_repository] = lambda: url_repo
        app.dependency_overrides[get_urlchunk_repository] = lambda: chunk_repo

        return url_repo, chunk_repo

    yield _setup
    app.dependency_overrides.clear()


@pytest.fixture
def setup_notebook_deps() -> Generator[Callable[..., tuple[StubBookRepository, StubNoteRepository, StubEmbeddingClient, StubLLMClient]], None, None]:
    """
    Setup dependencies for notebook upload endpoints.

    Used in test_notebooks.py (3 tests).

    Usage:
        def test_notebook(setup_notebook_deps):
            book_repo, note_repo, embedding_client, llm_client = setup_notebook_deps()
            # Test code here - cleanup is automatic!
    """

    def _setup() -> tuple[
        StubBookRepository,
        StubNoteRepository,
        StubEmbeddingClient,
        StubLLMClient,
    ]:
        book_repo = StubBookRepository()
        note_repo = StubNoteRepository()
        embedding_client = StubEmbeddingClient()
        llm_client = StubLLMClient()

        app.dependency_overrides[get_book_repository] = lambda: book_repo
        app.dependency_overrides[get_note_repository] = lambda: note_repo
        app.dependency_overrides[get_embedding_client] = lambda: embedding_client
        app.dependency_overrides[get_llm_client] = lambda: llm_client

        return book_repo, note_repo, embedding_client, llm_client

    yield _setup
    app.dependency_overrides.clear()
