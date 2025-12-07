"""
Shared pytest fixtures for repository tests.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine
from .book_repository import BookRepository
from .note_repository import NoteRepository


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
