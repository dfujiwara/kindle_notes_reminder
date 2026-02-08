"""
Tests for Twitter fetching and content extraction functionality.
"""

import httpx
import pytest
import respx
from httpx import Response
from unittest.mock import patch

from src.tweet_ingestion.interfaces import (
    TwitterFetchError,
    TweetNotFoundError,
    RateLimitError,
    ThreadTooLargeError,
)
from src.tweet_ingestion.twitter_fetcher import (
    fetch_tweet,
    fetch_thread,
    parse_tweet_input,
)


class TestParseTweetInput:
    """Tests for parse_tweet_input function."""

    def test_parse_tweet_id_directly(self):
        """Test parsing a numeric tweet ID."""
        assert parse_tweet_input("1234567890") == "1234567890"

    def test_parse_twitter_url(self):
        """Test parsing a twitter.com URL."""
        url = "https://twitter.com/user/status/1234567890"
        assert parse_tweet_input(url) == "1234567890"

    def test_parse_x_url(self):
        """Test parsing an x.com URL."""
        url = "https://x.com/user/status/9876543210"
        assert parse_tweet_input(url) == "9876543210"

    def test_parse_invalid_input_raises_error(self):
        """Test that invalid input raises TwitterFetchError."""
        with pytest.raises(TwitterFetchError, match="Invalid tweet input"):
            parse_tweet_input("not-a-valid-tweet")

    def test_parse_invalid_url_raises_error(self):
        """Test that invalid URL raises TwitterFetchError."""
        with pytest.raises(TwitterFetchError, match="Invalid tweet input"):
            parse_tweet_input("https://example.com/something")


# Sample Twitter API v2 responses
SAMPLE_TWEET_RESPONSE = {
    "data": {
        "id": "1234567890",
        "text": "This is a sample tweet content",
        "author_id": "12345",
        "conversation_id": "1234567890",
        "created_at": "2024-01-15T10:30:00.000Z",
    },
    "includes": {
        "users": [{"id": "12345", "username": "testuser", "name": "Test User"}]
    },
}

SAMPLE_TWEET_WITH_MEDIA_RESPONSE = {
    "data": {
        "id": "1234567891",
        "text": "Tweet with images!",
        "author_id": "12345",
        "conversation_id": "1234567891",
        "created_at": "2024-01-15T11:00:00.000Z",
        "attachments": {"media_keys": ["media1", "media2"]},
    },
    "includes": {
        "users": [{"id": "12345", "username": "testuser", "name": "Test User"}],
        "media": [
            {"media_key": "media1", "url": "https://pbs.twimg.com/media/image1.jpg"},
            {
                "media_key": "media2",
                "preview_image_url": "https://pbs.twimg.com/media/video_preview.jpg",
            },
        ],
    },
}

SAMPLE_THREAD_SEARCH_RESPONSE = {
    "data": [
        {
            "id": "1234567890",
            "text": "Thread tweet 1/3",
            "author_id": "12345",
            "conversation_id": "1234567890",
            "created_at": "2024-01-15T10:00:00.000Z",
        },
        {
            "id": "1234567891",
            "text": "Thread tweet 2/3",
            "author_id": "12345",
            "conversation_id": "1234567890",
            "created_at": "2024-01-15T10:01:00.000Z",
        },
        {
            "id": "1234567892",
            "text": "Thread tweet 3/3",
            "author_id": "12345",
            "conversation_id": "1234567890",
            "created_at": "2024-01-15T10:02:00.000Z",
        },
    ],
    "includes": {
        "users": [{"id": "12345", "username": "threadauthor", "name": "Thread Author"}]
    },
}


class TestFetchTweet:
    """Tests for fetch_tweet function."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_tweet_success(self):
        """Test successful tweet fetch."""
        respx.get("https://api.twitter.com/2/tweets/1234567890").mock(
            return_value=Response(200, json=SAMPLE_TWEET_RESPONSE)
        )

        result = await fetch_tweet("1234567890", bearer_token="test_token")

        assert result.tweet_id == "1234567890"
        assert result.content == "This is a sample tweet content"
        assert result.author_username == "testuser"
        assert result.author_display_name == "Test User"
        assert result.conversation_id == "1234567890"

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_tweet_with_media(self):
        """Test fetching tweet with media attachments."""
        respx.get("https://api.twitter.com/2/tweets/1234567891").mock(
            return_value=Response(200, json=SAMPLE_TWEET_WITH_MEDIA_RESPONSE)
        )

        result = await fetch_tweet("1234567891", bearer_token="test_token")

        assert result.tweet_id == "1234567891"
        assert len(result.media_urls) == 2
        assert "https://pbs.twimg.com/media/image1.jpg" in result.media_urls
        assert "https://pbs.twimg.com/media/video_preview.jpg" in result.media_urls

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_tweet_not_found(self):
        """Test that 404 raises TweetNotFoundError."""
        respx.get("https://api.twitter.com/2/tweets/9999999999").mock(
            return_value=Response(404)
        )

        with pytest.raises(TweetNotFoundError, match="Tweet not found"):
            await fetch_tweet("9999999999", bearer_token="test_token")

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_tweet_rate_limited(self):
        """Test that 429 raises RateLimitError."""
        respx.get("https://api.twitter.com/2/tweets/1234567890").mock(
            return_value=Response(429, headers={"retry-after": "60"})
        )

        with pytest.raises(RateLimitError) as exc_info:
            await fetch_tweet("1234567890", bearer_token="test_token")

        assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_tweet_rate_limited_no_retry_header(self):
        """Test rate limit without retry-after header."""
        respx.get("https://api.twitter.com/2/tweets/1234567890").mock(
            return_value=Response(429)
        )

        with pytest.raises(RateLimitError) as exc_info:
            await fetch_tweet("1234567890", bearer_token="test_token")

        assert exc_info.value.retry_after is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_tweet_api_error_in_response(self):
        """Test handling of API errors in response body."""
        error_response = {"errors": [{"detail": "Tweet not found or not accessible"}]}
        respx.get("https://api.twitter.com/2/tweets/1234567890").mock(
            return_value=Response(200, json=error_response)
        )

        with pytest.raises(TweetNotFoundError):
            await fetch_tweet("1234567890", bearer_token="test_token")

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_tweet_timeout(self):
        """Test that timeout raises TwitterFetchError."""
        respx.get("https://api.twitter.com/2/tweets/1234567890").mock(
            side_effect=httpx.TimeoutException("Connection timeout")
        )

        with pytest.raises(TwitterFetchError, match="Timeout"):
            await fetch_tweet("1234567890", bearer_token="test_token")

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_tweet_http_error(self):
        """Test that HTTP errors raise TwitterFetchError."""
        respx.get("https://api.twitter.com/2/tweets/1234567890").mock(
            return_value=Response(500)
        )

        with pytest.raises(TwitterFetchError, match="HTTP error 500"):
            await fetch_tweet("1234567890", bearer_token="test_token")

    @pytest.mark.asyncio
    async def test_fetch_tweet_no_bearer_token(self):
        """Test that missing bearer token raises TwitterFetchError."""
        with patch(
            "src.tweet_ingestion.twitter_fetcher._get_bearer_token",
            side_effect=TwitterFetchError("Twitter Bearer Token not configured"),
        ):
            with pytest.raises(TwitterFetchError, match="Bearer Token not configured"):
                await fetch_tweet("1234567890")

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_tweet_parses_created_at(self):
        """Test that created_at is parsed correctly."""
        respx.get("https://api.twitter.com/2/tweets/1234567890").mock(
            return_value=Response(200, json=SAMPLE_TWEET_RESPONSE)
        )

        result = await fetch_tweet("1234567890", bearer_token="test_token")

        assert result.tweeted_at is not None
        assert result.tweeted_at.year == 2024
        assert result.tweeted_at.month == 1
        assert result.tweeted_at.day == 15


class TestFetchThread:
    """Tests for fetch_thread function."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_single_tweet_thread(self):
        """Test fetching a single tweet (no thread)."""
        single_tweet_response = {
            "data": {
                "id": "1234567890",
                "text": "Just a single tweet",
                "author_id": "12345",
                "created_at": "2024-01-15T10:00:00.000Z",
            },
            "includes": {
                "users": [
                    {"id": "12345", "username": "singleuser", "name": "Single User"}
                ]
            },
        }

        respx.get("https://api.twitter.com/2/tweets/1234567890").mock(
            return_value=Response(200, json=single_tweet_response)
        )

        result = await fetch_thread("1234567890", bearer_token="test_token")

        assert result.root_tweet_id == "1234567890"
        assert len(result.tweets) == 1
        assert result.tweets[0].content == "Just a single tweet"
        assert result.author_username == "singleuser"

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_thread_via_conversation_search(self):
        """Test fetching a multi-tweet thread."""
        # First call: get initial tweet
        initial_tweet_response = {
            "data": {
                "id": "1234567892",
                "text": "Thread tweet 3/3",
                "author_id": "12345",
                "conversation_id": "1234567890",
                "created_at": "2024-01-15T10:02:00.000Z",
            },
            "includes": {
                "users": [
                    {"id": "12345", "username": "threadauthor", "name": "Thread Author"}
                ]
            },
        }

        respx.get("https://api.twitter.com/2/tweets/1234567892").mock(
            return_value=Response(200, json=initial_tweet_response)
        )

        # Second call: search conversation
        respx.get("https://api.twitter.com/2/tweets/search/recent").mock(
            return_value=Response(200, json=SAMPLE_THREAD_SEARCH_RESPONSE)
        )

        result = await fetch_thread("1234567892", bearer_token="test_token")

        # Should have all 3 tweets
        assert len(result.tweets) == 3
        assert result.root_tweet_id == "1234567890"
        assert result.author_username == "threadauthor"

        # Tweets should be sorted by created_at
        assert result.tweets[0].content == "Thread tweet 1/3"
        assert result.tweets[1].content == "Thread tweet 2/3"
        assert result.tweets[2].content == "Thread tweet 3/3"

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_thread_empty_search_results(self):
        """Test thread fetch when search returns no results."""
        initial_tweet_response = {
            "data": {
                "id": "1234567890",
                "text": "Initial tweet",
                "author_id": "12345",
                "conversation_id": "1234567890",
                "created_at": "2024-01-15T10:00:00.000Z",
            },
            "includes": {
                "users": [{"id": "12345", "username": "testuser", "name": "Test User"}]
            },
        }

        respx.get("https://api.twitter.com/2/tweets/1234567890").mock(
            return_value=Response(200, json=initial_tweet_response)
        )

        # Empty search result
        respx.get("https://api.twitter.com/2/tweets/search/recent").mock(
            return_value=Response(200, json={"meta": {"result_count": 0}})
        )

        result = await fetch_thread("1234567890", bearer_token="test_token")

        # Should fall back to just the initial tweet
        assert len(result.tweets) == 1
        assert result.tweets[0].tweet_id == "1234567890"

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_thread_tweet_not_found(self):
        """Test that TweetNotFoundError propagates from thread fetch."""
        respx.get("https://api.twitter.com/2/tweets/9999999999").mock(
            return_value=Response(404)
        )

        with pytest.raises(TweetNotFoundError):
            await fetch_thread("9999999999", bearer_token="test_token")

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_thread_rate_limited(self):
        """Test rate limit handling in thread fetch."""
        respx.get("https://api.twitter.com/2/tweets/1234567890").mock(
            return_value=Response(429, headers={"retry-after": "120"})
        )

        with pytest.raises(RateLimitError) as exc_info:
            await fetch_thread("1234567890", bearer_token="test_token")

        assert exc_info.value.retry_after == 120

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_thread_respects_max_depth(self):
        """Test that thread fetching respects max_depth parameter."""
        # Create response with many tweets
        many_tweets = {
            "data": [
                {
                    "id": f"tweet_{i}",
                    "text": f"Tweet {i}",
                    "author_id": "12345",
                    "conversation_id": "root_tweet",
                    "created_at": f"2024-01-15T10:{i:02d}:00.000Z",
                }
                for i in range(10)
            ],
            "includes": {
                "users": [
                    {"id": "12345", "username": "prolific", "name": "Prolific User"}
                ]
            },
        }

        initial_response = {
            "data": {
                "id": "root_tweet",
                "text": "Root tweet",
                "author_id": "12345",
                "conversation_id": "root_tweet",
                "created_at": "2024-01-15T10:00:00.000Z",
            },
            "includes": {
                "users": [
                    {"id": "12345", "username": "prolific", "name": "Prolific User"}
                ]
            },
        }

        respx.get("https://api.twitter.com/2/tweets/root_tweet").mock(
            return_value=Response(200, json=initial_response)
        )

        respx.get("https://api.twitter.com/2/tweets/search/recent").mock(
            return_value=Response(200, json=many_tweets)
        )

        # Should raise ThreadTooLargeError when exceeding max_depth
        with pytest.raises(ThreadTooLargeError):
            await fetch_thread("root_tweet", max_depth=5, bearer_token="test_token")


class TestFetchThreadFallback:
    """Tests for recursive thread traversal fallback."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_fallback_to_recursive_on_search_error(self):
        """Test fallback to recursive traversal when search fails."""
        # Initial tweet with reply chain
        tweet_2 = {
            "data": {
                "id": "tweet_2",
                "text": "Reply tweet",
                "author_id": "12345",
                "conversation_id": "tweet_1",
                "in_reply_to_status_id": "tweet_1",
                "created_at": "2024-01-15T10:01:00.000Z",
            },
            "includes": {
                "users": [{"id": "12345", "username": "author", "name": "Author"}]
            },
        }

        tweet_1 = {
            "data": {
                "id": "tweet_1",
                "text": "Original tweet",
                "author_id": "12345",
                "conversation_id": "tweet_1",
                "created_at": "2024-01-15T10:00:00.000Z",
            },
            "includes": {
                "users": [{"id": "12345", "username": "author", "name": "Author"}]
            },
        }

        # Mock initial tweet fetch
        respx.get("https://api.twitter.com/2/tweets/tweet_2").mock(
            return_value=Response(200, json=tweet_2)
        )

        # Mock search failing (e.g., tweets older than 7 days)
        respx.get("https://api.twitter.com/2/tweets/search/recent").mock(
            return_value=Response(403)  # Forbidden - simulating access denied
        )

        # Mock recursive fetch of parent tweet
        respx.get("https://api.twitter.com/2/tweets/tweet_1").mock(
            return_value=Response(200, json=tweet_1)
        )

        result = await fetch_thread("tweet_2", bearer_token="test_token")

        # Should have both tweets via recursive traversal
        assert len(result.tweets) == 2
        assert result.root_tweet_id == "tweet_1"
