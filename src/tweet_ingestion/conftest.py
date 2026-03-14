"""Pytest fixtures for tweet ingestion tests."""

import pytest
from datetime import datetime, timezone
from typing import Callable

from src.tweet_ingestion.interfaces import (
    FetchedThread,
    FetchedTweet,
    ThreadFetcherFn,
    TwitterFetchError,
)
from src.test_utils import (
    StubEmbeddingClient,
    StubLLMClient,
    StubTweetRepository,
    StubTweetThreadRepository,
)

TweetProcessorDepsSetup = Callable[
    ...,
    tuple[
        StubTweetThreadRepository,
        StubTweetRepository,
        StubEmbeddingClient,
        StubLLMClient,
    ],
]


def make_fetched_tweet(
    tweet_id: str,
    content: str,
    author_username: str = "testuser",
    author_display_name: str = "Test User",
    conversation_id: str | None = None,
) -> FetchedTweet:
    """Helper to create a FetchedTweet for testing."""
    return FetchedTweet(
        tweet_id=tweet_id,
        author_username=author_username,
        author_display_name=author_display_name,
        content=content,
        media_urls=[],
        conversation_id=conversation_id,
        in_reply_to_tweet_id=None,
        tweeted_at=datetime.now(timezone.utc),
    )


def make_fetched_thread(
    root_tweet_id: str,
    tweets: list[FetchedTweet],
    author_username: str = "testuser",
    author_display_name: str = "Test User",
) -> FetchedThread:
    """Helper to create a FetchedThread for testing."""
    return FetchedThread(
        root_tweet_id=root_tweet_id,
        author_username=author_username,
        author_display_name=author_display_name,
        tweets=tweets,
    )


@pytest.fixture
def single_tweet_fetcher() -> ThreadFetcherFn:
    """Mock fetcher returning a single tweet."""

    async def _fetch(tweet_id: str, max_depth: int = 50) -> FetchedThread:
        tweet = make_fetched_tweet(
            tweet_id=tweet_id,
            content="This is a single tweet for testing.",
            conversation_id=tweet_id,
        )
        return make_fetched_thread(
            root_tweet_id=tweet_id,
            tweets=[tweet],
        )

    return _fetch


@pytest.fixture
def multi_tweet_fetcher() -> ThreadFetcherFn:
    """Mock fetcher returning a multi-tweet thread."""

    async def _fetch(tweet_id: str, max_depth: int = 50) -> FetchedThread:
        tweets = [
            make_fetched_tweet(
                tweet_id="1111111111",
                content="Thread 1/3: Introduction to the topic.",
                conversation_id="1111111111",
            ),
            make_fetched_tweet(
                tweet_id="1111111112",
                content="Thread 2/3: Deep dive into details.",
                conversation_id="1111111111",
            ),
            make_fetched_tweet(
                tweet_id="1111111113",
                content="Thread 3/3: Conclusion and takeaways.",
                conversation_id="1111111111",
            ),
        ]
        return make_fetched_thread(
            root_tweet_id="1111111111",
            tweets=tweets,
        )

    return _fetch


@pytest.fixture
def failing_fetcher() -> ThreadFetcherFn:
    """Mock fetcher that raises an error."""

    async def _fetch(tweet_id: str, max_depth: int = 50) -> FetchedThread:
        raise TwitterFetchError("Failed to fetch tweet")

    return _fetch


@pytest.fixture
def setup_tweet_processor_deps() -> TweetProcessorDepsSetup:
    """Setup stub dependencies for tweet processor tests.

    Returns a callable that accepts optional failure/response configuration
    and returns a tuple of (thread_repo, tweet_repo, embedding_client, llm_client).

    Usage:
        def test_something(setup_tweet_processor_deps):
            thread_repo, tweet_repo, embedding_client, llm_client = setup_tweet_processor_deps()
            # or with config:
            thread_repo, tweet_repo, embedding_client, llm_client = setup_tweet_processor_deps(
                embedding_should_fail=True,
                llm_responses=["summary"],
            )
    """

    def _setup(
        embedding_should_fail: bool = False,
        llm_should_fail: bool = False,
        llm_responses: list[str] | None = None,
    ) -> tuple[
        StubTweetThreadRepository,
        StubTweetRepository,
        StubEmbeddingClient,
        StubLLMClient,
    ]:
        thread_repo = StubTweetThreadRepository()
        tweet_repo = StubTweetRepository()
        embedding_client = StubEmbeddingClient(should_fail=embedding_should_fail)
        llm_client = StubLLMClient(
            should_fail=llm_should_fail,
            responses=llm_responses if llm_responses is not None else [],
        )
        return thread_repo, tweet_repo, embedding_client, llm_client

    return _setup
