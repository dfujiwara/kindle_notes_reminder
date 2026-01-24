"""
Shared pytest fixtures for tweet repository tests.
"""

import pytest
from sqlmodel import Session
from .tweet_thread_repository import TweetThreadRepository
from .tweet_repository import TweetRepository


@pytest.fixture(name="tweet_thread_repo")
def tweet_thread_repo_fixture(session: Session) -> TweetThreadRepository:
    """Create a TweetThreadRepository instance with an in-memory database session."""
    return TweetThreadRepository(session)


@pytest.fixture(name="tweet_repo")
def tweet_repo_fixture(session: Session) -> TweetRepository:
    """Create a TweetRepository instance with an in-memory database session."""
    return TweetRepository(session)
