"""
Shared pytest fixtures for all tests.
"""

from contextlib import contextmanager
from typing import Generator

import pytest
from sqlmodel import Session, SQLModel, create_engine


@pytest.fixture(name="session")
def session_fixture():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="session_factory")
def session_factory_fixture(session: Session):
    """Wrap the in-memory session as a factory for background task testing."""

    @contextmanager
    def _factory() -> Generator[Session, None, None]:
        yield session

    return _factory
