"""
Shared pytest fixtures for repository tests.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine
from .book_repository import BookRepository
from .note_repository import NoteRepository
from .evaluation_repository import EvaluationRepository
from .url_repository import URLRepository
from .urlchunk_repository import URLChunkRepository


@pytest.fixture(name="session")
def session_fixture():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="book_repo")
def book_repo_fixture(session: Session) -> BookRepository:
    """Create a BookRepository instance with an in-memory database session."""
    return BookRepository(session)


@pytest.fixture(name="note_repo")
def note_repo_fixture(session: Session) -> NoteRepository:
    """Create a NoteRepository instance with an in-memory database session."""
    return NoteRepository(session)


@pytest.fixture(name="evaluation_repo")
def evaluation_repo_fixture(session: Session) -> EvaluationRepository:
    """Create an EvaluationRepository instance with an in-memory database session."""
    return EvaluationRepository(session)


@pytest.fixture(name="url_repo")
def url_repo_fixture(session: Session) -> URLRepository:
    """Create a URLRepository instance with an in-memory database session."""
    return URLRepository(session)


@pytest.fixture(name="urlchunk_repo")
def urlchunk_repo_fixture(session: Session) -> URLChunkRepository:
    """Create a URLChunkRepository instance with an in-memory database session."""
    return URLChunkRepository(session)
