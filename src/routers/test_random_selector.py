"""
Tests for the random content selector.

Tests weighted random selection between notes, URL chunks, and tweets.
"""

from src.routers.random_selector import (
    RandomNoteSelection,
    RandomChunkSelection,
    RandomTweetSelection,
    RandomSelection,
    select_random_content,
)
from src.repositories.models import NoteCreate, TweetCreate, URLChunkCreate
from src.test_utils import (
    StubNoteRepository,
    StubTweetRepository,
    StubURLChunkRepository,
)
from datetime import datetime, timezone


def _make_tweet_repo_with_tweets(count: int) -> StubTweetRepository:
    tweet_repo = StubTweetRepository()
    for i in range(count):
        tweet_repo.add(
            TweetCreate(
                tweet_id=f"tweet_{i}",
                author_username="testuser",
                author_display_name="Test User",
                content=f"Tweet {i} content",
                thread_id=1,
                position_in_thread=i,
                tweeted_at=datetime.now(timezone.utc),
                embedding=[0.3] * 1536,
            )
        )
    return tweet_repo


def test_select_random_content_empty_database():
    """Test that None is returned when no content exists."""
    note_repo = StubNoteRepository()
    chunk_repo = StubURLChunkRepository()
    tweet_repo = StubTweetRepository()

    result = select_random_content(note_repo, chunk_repo, tweet_repo)
    assert result is None


def test_select_random_content_only_notes():
    """Test selection when only notes exist."""
    note_repo = StubNoteRepository()
    chunk_repo = StubURLChunkRepository()
    tweet_repo = StubTweetRepository()

    # Add notes with embeddings
    for i in range(5):
        note_repo.add(
            NoteCreate(
                book_id=1,
                content=f"Note {i} content",
                content_hash=f"hash_{i}",
                embedding=[0.1] * 1536,
            )
        )
    result = select_random_content(note_repo, chunk_repo, tweet_repo)
    assert result is not None
    assert result.content_type == "note"
    assert result.item.book_id == 1


def test_select_random_content_only_chunks():
    """Test selection when only chunks exist."""
    note_repo = StubNoteRepository()
    chunk_repo = StubURLChunkRepository()
    tweet_repo = StubTweetRepository()

    # Add chunks with embeddings
    for i in range(5):
        chunk_repo.add(
            URLChunkCreate(
                url_id=1,
                content=f"Chunk {i} content",
                content_hash=f"chunk_hash_{i}",
                chunk_order=i,
                is_summary=False,
                embedding=[0.2] * 1536,
            )
        )
    result = select_random_content(note_repo, chunk_repo, tweet_repo)
    assert result is not None
    assert result.content_type == "url_chunk"
    assert result.item.url_id == 1


def test_select_random_content_only_tweets():
    """Test selection when only tweets exist."""
    note_repo = StubNoteRepository()
    chunk_repo = StubURLChunkRepository()
    tweet_repo = _make_tweet_repo_with_tweets(5)

    result = select_random_content(note_repo, chunk_repo, tweet_repo)
    assert result is not None
    assert result.content_type == "tweet"
    assert isinstance(result, RandomTweetSelection)


def test_select_random_content_both_types():
    """Test selection when both notes and chunks exist."""
    note_repo = StubNoteRepository()
    chunk_repo = StubURLChunkRepository()
    tweet_repo = StubTweetRepository()

    # Add note and chunks
    for i in range(10):
        note_repo.add(
            NoteCreate(
                book_id=1,
                content=f"Note {i}",
                content_hash=f"note_hash_{i}",
                embedding=[0.1] * 1536,
            )
        )
        chunk_repo.add(
            URLChunkCreate(
                url_id=1,
                content=f"Chunk {i}",
                content_hash=f"chunk_hash_{i}",
                chunk_order=i,
                is_summary=False,
                embedding=[0.2] * 1536,
            )
        )

    # With equal counts, we should eventually get both types
    results: list[RandomSelection | None] = []
    for _ in range(20):
        result = select_random_content(note_repo, chunk_repo, tweet_repo)
        results.append(result)

    # Verify we got both types
    has_note = any(r.content_type == "note" for r in results if r is not None)
    has_chunk = any(r.content_type == "url_chunk" for r in results if r is not None)
    assert has_note, "Expected at least one note selection"
    assert has_chunk, "Expected at least one chunk selection"


def test_select_random_content_all_three_types():
    """Test selection when notes, chunks, and tweets all exist."""
    note_repo = StubNoteRepository()
    chunk_repo = StubURLChunkRepository()
    tweet_repo = _make_tweet_repo_with_tweets(10)

    for i in range(10):
        note_repo.add(
            NoteCreate(
                book_id=1,
                content=f"Note {i}",
                content_hash=f"note_hash_{i}",
                embedding=[0.1] * 1536,
            )
        )
        chunk_repo.add(
            URLChunkCreate(
                url_id=1,
                content=f"Chunk {i}",
                content_hash=f"chunk_hash_{i}",
                chunk_order=i,
                is_summary=False,
                embedding=[0.2] * 1536,
            )
        )

    results: list[RandomSelection | None] = []
    for _ in range(30):
        result = select_random_content(note_repo, chunk_repo, tweet_repo)
        results.append(result)

    has_note = any(r.content_type == "note" for r in results if r is not None)
    has_chunk = any(r.content_type == "url_chunk" for r in results if r is not None)
    has_tweet = any(r.content_type == "tweet" for r in results if r is not None)
    assert has_note, "Expected at least one note selection"
    assert has_chunk, "Expected at least one chunk selection"
    assert has_tweet, "Expected at least one tweet selection"


def test_select_random_content_weighted_distribution():
    """Test that distribution is roughly proportional to counts."""
    note_repo = StubNoteRepository()
    chunk_repo = StubURLChunkRepository()
    tweet_repo = StubTweetRepository()

    # Add 3 notes with embeddings
    for i in range(3):
        note_repo.add(
            NoteCreate(
                book_id=1,
                content=f"Note {i}",
                content_hash=f"note_hash_{i}",
                embedding=[0.1] * 1536,
            )
        )

    # Add 1 chunk with embeddings
    chunk_repo.add(
        URLChunkCreate(
            url_id=1,
            content="Chunk",
            content_hash="chunk_hash_0",
            chunk_order=0,
            is_summary=False,
            embedding=[0.2] * 1536,
        )
    )

    note_count = 0
    chunk_count = 0

    # Run many times to check distribution
    for _ in range(100):
        result = select_random_content(note_repo, chunk_repo, tweet_repo)
        if isinstance(result, RandomNoteSelection):
            note_count += 1
        elif isinstance(result, RandomChunkSelection):
            chunk_count += 1

    # With 3:1 ratio, expect roughly 75% notes, 25% chunks
    # Allow some variance (40-85% for notes)
    assert 40 <= note_count <= 85, f"Expected ~75 notes, got {note_count}"
    assert 15 <= chunk_count <= 60, f"Expected ~25 chunks, got {chunk_count}"
