"""
Shared pytest fixtures for repository tests.
"""

import pytest
from sqlmodel import Session
from .book_repository import BookRepository
from .note_repository import NoteRepository
from .evaluation_repository import EvaluationRepository


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
