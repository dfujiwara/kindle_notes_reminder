"""Tests for the tweet content processing pipeline."""

import pytest
from datetime import datetime, timezone

from src.tweet_ingestion.tweet_processor import (
    process_tweet_content,
    create_thread_summary_prompt,
    create_tweet_context_prompt,
)
from src.tweet_ingestion.twitter_fetcher import (
    FetchedThread,
    FetchedTweet,
    ThreadFetcherFn,
    TwitterFetchError,
)
from src.test_utils import (
    StubTweetThreadRepository,
    StubTweetRepository,
    StubEmbeddingClient,
    StubLLMClient,
)
from src.repositories.models import TweetThreadCreate, TweetCreate


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


class TestCreatePrompts:
    """Tests for prompt creation functions."""

    def test_create_thread_summary_prompt(self):
        """Test thread summary prompt creation."""
        content = "Tweet 1: Hello\n\nTweet 2: World"
        prompt = create_thread_summary_prompt(content)

        assert "concise 2-3 sentence summary" in prompt
        assert content in prompt

    def test_create_tweet_context_prompt(self):
        """Test tweet context prompt creation."""
        prompt = create_tweet_context_prompt(
            author_username="elonmusk",
            thread_title="Thoughts on AI",
            tweet_content="AI will change everything.",
        )

        assert "@elonmusk" in prompt
        assert "Thoughts on AI" in prompt
        assert "AI will change everything" in prompt


class TestProcessTweetContent:
    """Tests for process_tweet_content function."""

    @pytest.fixture
    def single_tweet_fetcher(self) -> ThreadFetcherFn:
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
    def multi_tweet_fetcher(self) -> ThreadFetcherFn:
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
    def failing_fetcher(self) -> ThreadFetcherFn:
        """Mock fetcher that raises an error."""

        async def _fetch(tweet_id: str, max_depth: int = 50) -> FetchedThread:
            raise TwitterFetchError("Failed to fetch tweet")

        return _fetch

    @pytest.mark.asyncio
    async def test_process_single_tweet_success(
        self, single_tweet_fetcher: ThreadFetcherFn
    ) -> None:
        """Test successful processing of a single tweet."""
        thread_repo = StubTweetThreadRepository()
        tweet_repo = StubTweetRepository()
        embedding_client = StubEmbeddingClient()
        llm_client = StubLLMClient()

        result = await process_tweet_content(
            "1234567890",
            thread_repo,
            tweet_repo,
            llm_client,
            embedding_client,
            fetch_fn=single_tweet_fetcher,
        )

        # Check thread
        assert result.thread.root_tweet_id == "1234567890"
        assert result.thread.author_username == "testuser"
        assert result.thread.tweet_count == 1

        # Check tweets
        assert len(result.tweets) == 1
        assert result.tweets[0].content == "This is a single tweet for testing."
        assert result.tweets[0].position_in_thread == 0

    @pytest.mark.asyncio
    async def test_process_multi_tweet_thread_success(
        self, multi_tweet_fetcher: ThreadFetcherFn
    ) -> None:
        """Test successful processing of a multi-tweet thread."""
        thread_repo = StubTweetThreadRepository()
        tweet_repo = StubTweetRepository()
        embedding_client = StubEmbeddingClient()
        llm_client = StubLLMClient(responses=["This is a thread about the topic."])

        result = await process_tweet_content(
            "1111111111",
            thread_repo,
            tweet_repo,
            llm_client,
            embedding_client,
            fetch_fn=multi_tweet_fetcher,
        )

        # Check thread
        assert result.thread.root_tweet_id == "1111111111"
        assert result.thread.tweet_count == 3
        # Title should be LLM-generated summary
        assert result.thread.title == "This is a thread about the topic."

        # Check tweets
        assert len(result.tweets) == 3
        assert result.tweets[0].position_in_thread == 0
        assert result.tweets[1].position_in_thread == 1
        assert result.tweets[2].position_in_thread == 2

    @pytest.mark.asyncio
    async def test_process_tweet_with_url_input(
        self, single_tweet_fetcher: ThreadFetcherFn
    ) -> None:
        """Test processing with a Twitter URL input."""
        thread_repo = StubTweetThreadRepository()
        tweet_repo = StubTweetRepository()
        embedding_client = StubEmbeddingClient()
        llm_client = StubLLMClient()

        result = await process_tweet_content(
            "https://twitter.com/user/status/1234567890",
            thread_repo,
            tweet_repo,
            llm_client,
            embedding_client,
            fetch_fn=single_tweet_fetcher,
        )

        assert result.thread.root_tweet_id == "1234567890"
        assert len(result.tweets) == 1

    @pytest.mark.asyncio
    async def test_process_tweet_with_x_url_input(
        self, single_tweet_fetcher: ThreadFetcherFn
    ) -> None:
        """Test processing with an x.com URL input."""
        thread_repo = StubTweetThreadRepository()
        tweet_repo = StubTweetRepository()
        embedding_client = StubEmbeddingClient()
        llm_client = StubLLMClient()

        result = await process_tweet_content(
            "https://x.com/user/status/1234567890",
            thread_repo,
            tweet_repo,
            llm_client,
            embedding_client,
            fetch_fn=single_tweet_fetcher,
        )

        assert result.thread.root_tweet_id == "1234567890"

    @pytest.mark.asyncio
    async def test_process_duplicate_thread_returns_existing(self):
        """Test that duplicate threads return existing record without re-saving.

        Note: The fetcher is still called to get the root_tweet_id for deduplication,
        but the existing data from the database is returned rather than re-processing.
        """
        thread_repo = StubTweetThreadRepository()
        tweet_repo = StubTweetRepository()
        embedding_client = StubEmbeddingClient()
        llm_client = StubLLMClient()

        # Pre-populate with existing thread
        existing_thread = thread_repo.add(
            TweetThreadCreate(
                root_tweet_id="1234567890",
                author_username="existinguser",
                author_display_name="Existing User",
                title="Existing thread",
            )
        )
        thread_repo.update_tweet_count(existing_thread.id, 1)

        tweet_repo.add(
            TweetCreate(
                tweet_id="1234567890",
                author_username="existinguser",
                author_display_name="Existing User",
                content="Existing tweet content",
                media_urls=[],
                thread_id=existing_thread.id,
                position_in_thread=0,
                tweeted_at=datetime.now(timezone.utc),
            )
        )

        # Fetcher returns the same root_tweet_id as the existing thread
        # (simulating fetching a tweet that's already in the database)
        fetcher_called = False

        async def mock_fetcher(tweet_id: str, max_depth: int = 50) -> FetchedThread:
            nonlocal fetcher_called
            fetcher_called = True
            return make_fetched_thread(
                root_tweet_id="1234567890",
                tweets=[
                    make_fetched_tweet(
                        tweet_id="1234567890",
                        content="Fresh content from API (should be ignored)",
                    )
                ],
            )

        result = await process_tweet_content(
            "1234567890",
            thread_repo,
            tweet_repo,
            llm_client,
            embedding_client,
            fetch_fn=mock_fetcher,
        )

        # Fetcher should be called (to get root_tweet_id for deduplication)
        assert fetcher_called

        # Should return existing data from database, not the fetched data
        assert result.thread.title == "Existing thread"
        assert result.thread.author_username == "existinguser"
        assert len(result.tweets) == 1
        assert result.tweets[0].content == "Existing tweet content"

        # Should not have created new records
        assert len(thread_repo.threads) == 1
        assert len(tweet_repo.tweets) == 1

    @pytest.mark.asyncio
    async def test_process_tweet_generates_embeddings(
        self, multi_tweet_fetcher: ThreadFetcherFn
    ) -> None:
        """Test that embeddings are generated for all tweets."""
        thread_repo = StubTweetThreadRepository()
        tweet_repo = StubTweetRepository()
        embedding_client = StubEmbeddingClient()
        llm_client = StubLLMClient(responses=["Thread summary"])

        await process_tweet_content(
            "1111111111",
            thread_repo,
            tweet_repo,
            llm_client,
            embedding_client,
            fetch_fn=multi_tweet_fetcher,
        )

        # Check all tweets have embeddings
        assert tweet_repo.count_with_embeddings() == 3

    @pytest.mark.asyncio
    async def test_process_tweet_fetch_error_propagates(
        self, failing_fetcher: ThreadFetcherFn
    ) -> None:
        """Test that fetch errors are propagated."""
        thread_repo = StubTweetThreadRepository()
        tweet_repo = StubTweetRepository()
        embedding_client = StubEmbeddingClient()
        llm_client = StubLLMClient()

        with pytest.raises(TwitterFetchError, match="Failed to fetch tweet"):
            await process_tweet_content(
                "1234567890",
                thread_repo,
                tweet_repo,
                llm_client,
                embedding_client,
                fetch_fn=failing_fetcher,
            )

    @pytest.mark.asyncio
    async def test_process_tweet_invalid_input_raises_error(
        self, single_tweet_fetcher: ThreadFetcherFn
    ) -> None:
        """Test that invalid input raises error."""
        thread_repo = StubTweetThreadRepository()
        tweet_repo = StubTweetRepository()
        embedding_client = StubEmbeddingClient()
        llm_client = StubLLMClient()

        with pytest.raises(TwitterFetchError, match="Invalid tweet input"):
            await process_tweet_content(
                "not-a-valid-tweet-or-url",
                thread_repo,
                tweet_repo,
                llm_client,
                embedding_client,
                fetch_fn=single_tweet_fetcher,
            )

    @pytest.mark.asyncio
    async def test_single_tweet_uses_content_as_title(
        self, single_tweet_fetcher: ThreadFetcherFn
    ) -> None:
        """Test that single tweets use truncated content as title."""
        thread_repo = StubTweetThreadRepository()
        tweet_repo = StubTweetRepository()
        embedding_client = StubEmbeddingClient()
        llm_client = StubLLMClient()

        result = await process_tweet_content(
            "1234567890",
            thread_repo,
            tweet_repo,
            llm_client,
            embedding_client,
            fetch_fn=single_tweet_fetcher,
        )

        # Single tweet should use content as title (possibly truncated)
        assert "This is a single tweet" in result.thread.title

    @pytest.mark.asyncio
    async def test_process_tweet_with_media_urls(self):
        """Test processing a tweet with media attachments."""
        thread_repo = StubTweetThreadRepository()
        tweet_repo = StubTweetRepository()
        embedding_client = StubEmbeddingClient()
        llm_client = StubLLMClient()

        async def fetcher_with_media(
            tweet_id: str, max_depth: int = 50
        ) -> FetchedThread:
            tweet = FetchedTweet(
                tweet_id=tweet_id,
                author_username="mediauser",
                author_display_name="Media User",
                content="Check out this image!",
                media_urls=[
                    "https://pbs.twimg.com/media/image1.jpg",
                    "https://pbs.twimg.com/media/image2.jpg",
                ],
                conversation_id=tweet_id,
                in_reply_to_tweet_id=None,
                tweeted_at=datetime.now(timezone.utc),
            )
            return make_fetched_thread(
                root_tweet_id=tweet_id,
                tweets=[tweet],
                author_username="mediauser",
                author_display_name="Media User",
            )

        result = await process_tweet_content(
            "9999999999",
            thread_repo,
            tweet_repo,
            llm_client,
            embedding_client,
            fetch_fn=fetcher_with_media,
        )

        assert len(result.tweets) == 1
        assert len(result.tweets[0].media_urls) == 2
        assert "image1.jpg" in result.tweets[0].media_urls[0]

    @pytest.mark.asyncio
    async def test_llm_failure_uses_fallback_title(
        self, multi_tweet_fetcher: ThreadFetcherFn
    ) -> None:
        """Test that LLM failure falls back to truncated first tweet."""
        thread_repo = StubTweetThreadRepository()
        tweet_repo = StubTweetRepository()
        embedding_client = StubEmbeddingClient()
        llm_client = StubLLMClient(should_fail=True)

        result = await process_tweet_content(
            "1111111111",
            thread_repo,
            tweet_repo,
            llm_client,
            embedding_client,
            fetch_fn=multi_tweet_fetcher,
        )

        # Should fall back to first tweet content
        assert "Introduction to the topic" in result.thread.title
