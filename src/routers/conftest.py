"""
Shared pytest fixtures for router tests.

Provides reusable dependency injection fixtures to reduce boilerplate in test files.
Each fixture returns a setup function that creates fresh stub instances and handles
dependency overrides with automatic cleanup.
"""

from typing import Generator, Callable, Any, Dict
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
def override_dependencies() -> Generator[Callable[[Dict[Any, Any]], Dict[Any, Any]], None, None]:
    """
    Base fixture that handles dependency override setup and cleanup.

    Returns a function that accepts dependency mappings and sets up overrides.
    Automatically cleans up after the test completes.

    Usage:
        def test_something(override_dependencies):
            repo = StubBookRepository()
            override_dependencies({get_book_repository: repo})
    """

    def _override(dependency_map: Dict[Any, Any]) -> Dict[Any, Any]:
        for dependency_func, stub_instance in dependency_map.items():
            app.dependency_overrides[dependency_func] = lambda inst=stub_instance: inst  # type: ignore[assignment]
        return dependency_map

    yield _override
    app.dependency_overrides.clear()


@pytest.fixture
def setup_book_note_deps(override_dependencies: Callable[[Dict[Any, Any]], Dict[Any, Any]]) -> Callable:  # type: ignore[return]
    """
    Setup book and note repository dependencies.

    Returns a function that creates fresh stub instances and overrides deps.
    Most common pattern - used in ~15 tests.

    Returns:
        A callable that returns (StubBookRepository, StubNoteRepository)

    Usage:
        def test_something(setup_book_note_deps):
            book_repo, note_repo = setup_book_note_deps()
            # Test code here
    """

    def _setup(
        include_sample_book: bool = False,
    ) -> tuple[StubBookRepository, StubNoteRepository]:
        book_repo = StubBookRepository(include_sample_book=include_sample_book)
        note_repo = StubNoteRepository()

        override_dependencies(
            {get_book_repository: book_repo, get_note_repository: note_repo}
        )

        return book_repo, note_repo

    return _setup


@pytest.fixture
def setup_search_deps(override_dependencies: Callable[[Dict[Any, Any]], Dict[Any, Any]]) -> Callable:  # type: ignore[return]
    """
    Setup dependencies for search endpoints (book, note, embedding).

    Returns a function that creates fresh stub instances for search tests.
    Used in test_search.py (5 tests).

    Returns:
        A callable that returns (StubBookRepository, StubNoteRepository, StubEmbeddingClient)

    Usage:
        def test_search(setup_search_deps):
            book_repo, note_repo, embedding_client = setup_search_deps()
            # Test code here
    """

    def _setup(
        embedding_should_fail: bool = False,
    ) -> tuple[StubBookRepository, StubNoteRepository, StubEmbeddingClient]:
        book_repo = StubBookRepository()
        note_repo = StubNoteRepository()
        embedding_client = StubEmbeddingClient(should_fail=embedding_should_fail)

        override_dependencies(
            {
                get_book_repository: book_repo,
                get_note_repository: note_repo,
                get_embedding_client: embedding_client,
            }
        )

        return book_repo, note_repo, embedding_client

    return _setup


@pytest.fixture
def setup_evaluation_deps(override_dependencies: Callable[[Dict[Any, Any]], Dict[Any, Any]]) -> Callable:  # type: ignore[return]
    """
    Setup dependencies for evaluation endpoints (note, evaluation).

    Returns a function that creates fresh stub instances for evaluation tests.
    Used in test_evaluations.py (3 tests).

    Returns:
        A callable that returns (StubNoteRepository, StubEvaluationRepository)

    Usage:
        def test_evaluation(setup_evaluation_deps):
            note_repo, eval_repo = setup_evaluation_deps()
            # Test code here
    """

    def _setup() -> tuple[StubNoteRepository, StubEvaluationRepository]:
        note_repo = StubNoteRepository()
        eval_repo = StubEvaluationRepository()

        override_dependencies(
            {
                get_note_repository: note_repo,
                get_evaluation_repository: eval_repo,
            }
        )

        return note_repo, eval_repo

    return _setup


@pytest.fixture
def setup_url_deps(override_dependencies: Callable[[Dict[Any, Any]], Dict[Any, Any]]) -> Callable:  # type: ignore[return]
    """
    Setup dependencies for URL endpoints.

    Returns a function that creates fresh stub instances for URL tests.
    Used in test_urls.py (5 tests).

    Returns:
        A callable that returns (StubURLRepository, StubURLChunkRepository)

    Usage:
        def test_url(setup_url_deps):
            url_repo, chunk_repo = setup_url_deps()
            # Test code here
    """

    def _setup() -> tuple[StubURLRepository, StubURLChunkRepository]:
        url_repo = StubURLRepository()
        chunk_repo = StubURLChunkRepository()

        override_dependencies(
            {
                get_url_repository: url_repo,
                get_urlchunk_repository: chunk_repo,
            }
        )

        return url_repo, chunk_repo

    return _setup


@pytest.fixture
def setup_notebook_deps(override_dependencies: Callable[[Dict[Any, Any]], Dict[Any, Any]]) -> Callable:  # type: ignore[return]
    """
    Setup dependencies for notebook upload endpoints.

    Returns a function that creates fresh stub instances for notebook tests.
    Used in test_notebooks.py (3 tests).

    Returns:
        A callable that returns (StubBookRepository, StubNoteRepository, StubEmbeddingClient, StubLLMClient)

    Usage:
        def test_notebook(setup_notebook_deps):
            book_repo, note_repo, embedding_client, llm_client = setup_notebook_deps()
            # Test code here
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

        override_dependencies(
            {
                get_book_repository: book_repo,
                get_note_repository: note_repo,
                get_embedding_client: embedding_client,
                get_llm_client: llm_client,
            }
        )

        return book_repo, note_repo, embedding_client, llm_client

    return _setup
