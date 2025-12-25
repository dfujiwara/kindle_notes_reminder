"""
Shared pytest fixtures for URL repository tests.
"""

import pytest
from sqlmodel import Session
from .url_repository import URLRepository
from .urlchunk_repository import URLChunkRepository


@pytest.fixture(name="url_repo")
def url_repo_fixture(session: Session) -> URLRepository:
    """Create a URLRepository instance with an in-memory database session."""
    return URLRepository(session)


@pytest.fixture(name="urlchunk_repo")
def urlchunk_repo_fixture(session: Session) -> URLChunkRepository:
    """Create a URLChunkRepository instance with an in-memory database session."""
    return URLChunkRepository(session)
