"""
Shared pytest fixtures for router tests.

Provides reusable dependency injection fixtures to reduce boilerplate in test files.
Each fixture returns a setup function that creates fresh stub repositories and
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
    get_url_fetcher,
)
from src.test_utils import (
    StubBookRepository,
    StubNoteRepository,
    StubEvaluationRepository,
    StubEmbeddingClient,
    StubLLMClient,
    StubURLRepository,
    StubURLChunkRepository,
    StubURLFetcher,
)

# Type aliases for fixtures
BookNoteDepsSetup = Callable[..., tuple[StubBookRepository, StubNoteRepository]]
SearchDepsSetup = Callable[
    ...,
    tuple[
        StubBookRepository,
        StubNoteRepository,
        StubEmbeddingClient,
        StubURLRepository,
        StubURLChunkRepository,
    ],
]
EvaluationDepsSetup = Callable[..., tuple[StubNoteRepository, StubEvaluationRepository]]
URLDepsSetup = Callable[
    ...,
    tuple[
        StubURLRepository,
        StubURLChunkRepository,
        StubURLFetcher,
    ],
]
NotebookDepsSetup = Callable[
    ...,
    tuple[StubBookRepository, StubNoteRepository, StubEmbeddingClient, StubLLMClient],
]
RandomV2DepsSetup = Callable[
    ...,
    tuple[
        StubBookRepository,
        StubNoteRepository,
        StubEvaluationRepository,
        StubURLRepository,
        StubURLChunkRepository,
    ],
]


@pytest.fixture
def setup_book_note_deps() -> Generator[BookNoteDepsSetup, None, None]:
    """
    Setup book and note repository dependencies.

    Returns a function for flexible configuration. Most common pattern - used in ~15 tests.

    Usage:
        def test_something(setup_book_note_deps):
            book_repo, note_repo = setup_book_note_deps()
            # or with config:
            book_repo, note_repo = setup_book_note_deps(include_sample_book=True)
            # Cleanup is automatic!
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
def setup_search_deps() -> Generator[SearchDepsSetup, None, None]:
    """
    Setup dependencies for search endpoints (book, note, URL, embedding).

    Returns a function for flexible configuration. Used in test_search.py (5 tests).

    Usage:
        def test_search(setup_search_deps):
            book_repo, note_repo, embedding_client, url_repo, chunk_repo = setup_search_deps()
            # or with config:
            book_repo, note_repo, embedding_client, url_repo, chunk_repo = setup_search_deps(embedding_should_fail=True)
            # Cleanup is automatic!
    """

    def _setup(
        embedding_should_fail: bool = False,
    ) -> tuple[
        StubBookRepository,
        StubNoteRepository,
        StubEmbeddingClient,
        StubURLRepository,
        StubURLChunkRepository,
    ]:
        book_repo = StubBookRepository()
        note_repo = StubNoteRepository()
        embedding_client = StubEmbeddingClient(should_fail=embedding_should_fail)
        url_repo = StubURLRepository()
        chunk_repo = StubURLChunkRepository()

        app.dependency_overrides[get_book_repository] = lambda: book_repo
        app.dependency_overrides[get_note_repository] = lambda: note_repo
        app.dependency_overrides[get_embedding_client] = lambda: embedding_client
        app.dependency_overrides[get_url_repository] = lambda: url_repo
        app.dependency_overrides[get_urlchunk_repository] = lambda: chunk_repo

        return book_repo, note_repo, embedding_client, url_repo, chunk_repo

    yield _setup
    app.dependency_overrides.clear()


@pytest.fixture
def setup_evaluation_deps() -> Generator[EvaluationDepsSetup, None, None]:
    """
    Setup dependencies for evaluation endpoints (note, evaluation).

    Returns a function for consistent interface. Used in test_evaluations.py (3 tests).

    Usage:
        def test_evaluation(setup_evaluation_deps):
            note_repo, eval_repo = setup_evaluation_deps()
            # Cleanup is automatic!
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
def setup_url_deps() -> Generator[URLDepsSetup, None, None]:
    """
    Setup dependencies for URL endpoints.

    Returns a function for flexible configuration. Used in test_urls.py (5 tests).

    Usage:
        def test_url(setup_url_deps):
            url_repo, chunk_repo, fetcher = setup_url_deps()
            # or with error simulation:
            url_repo, chunk_repo, fetcher = setup_url_deps(fetcher_should_fail=True)
            # Cleanup is automatic!
    """

    def _setup(
        fetcher_should_fail: bool = False,
    ) -> tuple[StubURLRepository, StubURLChunkRepository, StubURLFetcher]:
        url_repo = StubURLRepository()
        chunk_repo = StubURLChunkRepository()
        fetcher = StubURLFetcher(should_fail=fetcher_should_fail)

        app.dependency_overrides[get_url_repository] = lambda: url_repo
        app.dependency_overrides[get_urlchunk_repository] = lambda: chunk_repo
        app.dependency_overrides[get_url_fetcher] = lambda: fetcher
        app.dependency_overrides[get_llm_client] = lambda: StubLLMClient()
        app.dependency_overrides[get_embedding_client] = lambda: StubEmbeddingClient()

        return url_repo, chunk_repo, fetcher

    yield _setup
    app.dependency_overrides.clear()


@pytest.fixture
def setup_notebook_deps() -> Generator[NotebookDepsSetup, None, None]:
    """
    Setup dependencies for notebook upload endpoints.

    Returns a function for consistent interface. Used in test_notebooks.py (3 tests).

    Usage:
        def test_notebook(setup_notebook_deps):
            book_repo, note_repo, embedding_client, llm_client = setup_notebook_deps()
            # Cleanup is automatic!
    """

    def _setup() -> tuple[
        StubBookRepository, StubNoteRepository, StubEmbeddingClient, StubLLMClient
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


@pytest.fixture
def setup_random_v2_deps() -> Generator[RandomV2DepsSetup, None, None]:
    """
    Setup dependencies for /random/v2 endpoint (book, note, evaluation, URL, chunk).

    Returns a function for consistent interface. Used in test_random_v2.py.

    Usage:
        def test_random_v2(setup_random_v2_deps):
            book_repo, note_repo, eval_repo, url_repo, chunk_repo = setup_random_v2_deps()
            # Cleanup is automatic!
    """

    def _setup() -> tuple[
        StubBookRepository,
        StubNoteRepository,
        StubEvaluationRepository,
        StubURLRepository,
        StubURLChunkRepository,
    ]:
        book_repo = StubBookRepository()
        note_repo = StubNoteRepository()
        eval_repo = StubEvaluationRepository()
        url_repo = StubURLRepository()
        chunk_repo = StubURLChunkRepository()

        app.dependency_overrides[get_book_repository] = lambda: book_repo
        app.dependency_overrides[get_note_repository] = lambda: note_repo
        app.dependency_overrides[get_evaluation_repository] = lambda: eval_repo
        app.dependency_overrides[get_url_repository] = lambda: url_repo
        app.dependency_overrides[get_urlchunk_repository] = lambda: chunk_repo
        # Provide multiple responses: one for context generation, one for evaluation
        app.dependency_overrides[get_llm_client] = lambda: StubLLMClient(
            responses=["Test LLM response", "Score: 0.8\nEvaluation: Good response"]
        )

        return book_repo, note_repo, eval_repo, url_repo, chunk_repo

    yield _setup
    app.dependency_overrides.clear()
