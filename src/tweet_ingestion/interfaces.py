"""
Twitter fetching interfaces, data classes, and exceptions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Awaitable, Callable, Protocol


class TwitterFetchError(Exception):
    """Base exception for Twitter fetching errors."""

    pass


class TweetNotFoundError(TwitterFetchError):
    """Exception raised when a tweet is deleted or private."""

    pass


class RateLimitError(TwitterFetchError):
    """Exception raised when Twitter rate limit is exceeded."""

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class ThreadTooLargeError(TwitterFetchError):
    """Exception raised when thread exceeds maximum depth."""

    pass


@dataclass
class FetchedTweet:
    """Result of fetching a single tweet."""

    tweet_id: str
    author_username: str
    author_display_name: str
    content: str
    tweeted_at: datetime
    media_urls: list[str] = field(default_factory=lambda: [])
    conversation_id: str | None = None
    in_reply_to_tweet_id: str | None = None


@dataclass
class FetchedThread:
    """Result of fetching a tweet thread."""

    root_tweet_id: str
    author_username: str
    author_display_name: str
    tweets: list[FetchedTweet] = field(default_factory=lambda: [])


# Type alias for thread fetcher function
# This is the callable signature used by process_tweet_content
ThreadFetcherFn = Callable[[str, int], Awaitable[FetchedThread]]


class TwitterFetcherInterface(Protocol):
    """Protocol for Twitter fetching implementations."""

    async def fetch_tweet(self, tweet_id: str) -> FetchedTweet:
        """
        Fetch a single tweet by ID.

        Args:
            tweet_id: The Twitter-assigned tweet ID

        Returns:
            FetchedTweet with tweet content and metadata

        Raises:
            TwitterFetchError: If fetching fails
            TweetNotFoundError: If tweet is deleted or private
            RateLimitError: If rate limit exceeded
        """
        ...

    async def fetch_thread(self, tweet_id: str, max_depth: int = 50) -> FetchedThread:
        """
        Fetch a tweet thread starting from any tweet in the thread.

        Args:
            tweet_id: The Twitter-assigned tweet ID (can be any tweet in thread)
            max_depth: Maximum number of tweets to fetch (default 50)

        Returns:
            FetchedThread with all tweets in conversation order

        Raises:
            TwitterFetchError: If fetching fails
            TweetNotFoundError: If tweet is deleted or private
            RateLimitError: If rate limit exceeded
            ThreadTooLargeError: If thread exceeds max_depth
        """
        ...
