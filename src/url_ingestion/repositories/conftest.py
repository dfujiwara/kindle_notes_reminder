"""
Shared pytest fixtures for URL repository tests.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine
from .url_repository import URLRepository
from .urlchunk_repository import URLChunkRepository


@pytest.fixture(name="session")
def session_fixture():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="url_repo")
def url_repo_fixture(session: Session) -> URLRepository:
    """Create a URLRepository instance with an in-memory database session."""
    return URLRepository(session)


@pytest.fixture(name="urlchunk_repo")
def urlchunk_repo_fixture(session: Session) -> URLChunkRepository:
    """Create a URLChunkRepository instance with an in-memory database session."""
    return URLChunkRepository(session)
