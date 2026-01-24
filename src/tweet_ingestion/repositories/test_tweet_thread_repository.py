"""
Tests for TweetThreadRepository methods using in-memory database.
"""

import pytest
from .tweet_thread_repository import TweetThreadRepository
from src.repositories.models import TweetThreadCreate, TweetThreadResponse


@pytest.fixture(name="sample_threads")
def sample_threads_fixture(
    tweet_thread_repo: TweetThreadRepository,
) -> list[TweetThreadResponse]:
    """Create sample tweet threads and return them as TweetThreadResponse objects."""
    threads = [
        TweetThreadCreate(
            root_tweet_id="123456789",
            author_username="user1",
            author_display_name="User One",
            title="Thread about AI",
        ),
        TweetThreadCreate(
            root_tweet_id="987654321",
            author_username="user2",
            author_display_name="User Two",
            title="Thread about Python",
        ),
        TweetThreadCreate(
            root_tweet_id="111222333",
            author_username="user1",
            author_display_name="User One",
            title="Another thread by user1",
        ),
    ]
    for thread in threads:
        tweet_thread_repo.add(thread)

    return tweet_thread_repo.list_threads()


def test_add_new_thread(tweet_thread_repo: TweetThreadRepository):
    """Test adding a new tweet thread."""
    thread_create = TweetThreadCreate(
        root_tweet_id="555666777",
        author_username="newuser",
        author_display_name="New User",
        title="New thread title",
    )

    result = tweet_thread_repo.add(thread_create)

    assert result.id is not None
    assert result.root_tweet_id == "555666777"
    assert result.author_username == "newuser"
    assert result.author_display_name == "New User"
    assert result.title == "New thread title"
    assert result.tweet_count == 0
    assert result.fetched_at is not None
    assert result.created_at is not None


def test_add_duplicate_root_tweet_id_returns_existing(
    tweet_thread_repo: TweetThreadRepository,
):
    """Test adding a thread with the same root_tweet_id returns existing record."""
    thread_create = TweetThreadCreate(
        root_tweet_id="duplicate123",
        author_username="user1",
        author_display_name="User One",
        title="First Title",
    )

    # Add the thread first time
    first_result = tweet_thread_repo.add(thread_create)
    first_id = first_result.id

    # Add the same thread again with different title
    thread_create_2 = TweetThreadCreate(
        root_tweet_id="duplicate123",
        author_username="different_user",
        author_display_name="Different User",
        title="Different Title",
    )
    second_result = tweet_thread_repo.add(thread_create_2)

    # Should return the existing thread, not create a new one
    assert second_result.id == first_id
    assert second_result.root_tweet_id == "duplicate123"
    assert second_result.title == "First Title"  # Original title preserved

    # Verify only one thread exists
    all_threads = tweet_thread_repo.list_threads()
    assert len(all_threads) == 1


def test_add_same_author_different_root_tweet_id(
    tweet_thread_repo: TweetThreadRepository,
):
    """Test adding threads with same author but different root_tweet_ids creates separate records."""
    thread1 = TweetThreadCreate(
        root_tweet_id="thread1",
        author_username="sameuser",
        author_display_name="Same User",
        title="Thread One",
    )
    thread2 = TweetThreadCreate(
        root_tweet_id="thread2",
        author_username="sameuser",
        author_display_name="Same User",
        title="Thread Two",
    )

    result1 = tweet_thread_repo.add(thread1)
    result2 = tweet_thread_repo.add(thread2)

    # Should create two separate threads
    assert result1.id != result2.id
    assert [result1.root_tweet_id, result2.root_tweet_id] == ["thread1", "thread2"]

    # Verify both threads exist
    all_threads = tweet_thread_repo.list_threads()
    assert len(all_threads) == 2


def test_get_existing_thread(
    tweet_thread_repo: TweetThreadRepository, sample_threads: list[TweetThreadResponse]
):
    """Test getting a thread by ID when it exists."""
    thread_id = sample_threads[0].id

    result = tweet_thread_repo.get(thread_id)

    assert result is not None
    assert result.id == thread_id
    assert result.root_tweet_id == "123456789"
    assert result.author_username == "user1"


def test_get_nonexistent_thread(tweet_thread_repo: TweetThreadRepository):
    """Test getting a thread by ID when it doesn't exist."""
    result = tweet_thread_repo.get(999)

    assert result is None


def test_get_by_root_tweet_id_existing(
    tweet_thread_repo: TweetThreadRepository, sample_threads: list[TweetThreadResponse]
):
    """Test getting a thread by root_tweet_id when it exists."""
    result = tweet_thread_repo.get_by_root_tweet_id("123456789")

    assert result is not None
    assert result.id == sample_threads[0].id
    assert result.root_tweet_id == "123456789"
    assert result.author_username == "user1"


def test_get_by_root_tweet_id_nonexistent(tweet_thread_repo: TweetThreadRepository):
    """Test getting a thread by root_tweet_id when it doesn't exist."""
    result = tweet_thread_repo.get_by_root_tweet_id("nonexistent")

    assert result is None


def test_get_by_ids(
    tweet_thread_repo: TweetThreadRepository, sample_threads: list[TweetThreadResponse]
):
    """Test getting multiple threads by IDs."""
    thread_ids = [sample_threads[0].id, sample_threads[2].id]

    result = tweet_thread_repo.get_by_ids(thread_ids)

    assert len(result) == 2
    result_ids = {t.id for t in result}
    assert result_ids == set(thread_ids)


def test_get_by_ids_empty_list(tweet_thread_repo: TweetThreadRepository):
    """Test getting threads with empty ID list."""
    result = tweet_thread_repo.get_by_ids([])

    assert result == []


def test_get_by_ids_nonexistent(tweet_thread_repo: TweetThreadRepository):
    """Test getting threads by IDs when they don't exist."""
    result = tweet_thread_repo.get_by_ids([999, 1000])

    assert result == []


def test_list_threads_empty(tweet_thread_repo: TweetThreadRepository):
    """Test listing threads when none exist."""
    result = tweet_thread_repo.list_threads()

    assert result == []


def test_list_threads_multiple(
    tweet_thread_repo: TweetThreadRepository, sample_threads: list[TweetThreadResponse]
):
    """Test listing multiple threads."""
    result = tweet_thread_repo.list_threads()

    assert len(result) == 3
    root_tweet_ids = {t.root_tweet_id for t in result}
    assert {"123456789", "987654321", "111222333"} == root_tweet_ids


def test_update_tweet_count(
    tweet_thread_repo: TweetThreadRepository, sample_threads: list[TweetThreadResponse]
):
    """Test updating a thread's tweet count."""
    thread_id = sample_threads[0].id

    # Verify initial count is 0
    thread = tweet_thread_repo.get(thread_id)
    assert thread is not None
    assert thread.tweet_count == 0

    # Update the count
    tweet_thread_repo.update_tweet_count(thread_id, 5)

    # Verify count was updated
    thread = tweet_thread_repo.get(thread_id)
    assert thread is not None
    assert thread.tweet_count == 5


def test_update_tweet_count_nonexistent_thread(
    tweet_thread_repo: TweetThreadRepository,
):
    """Test updating tweet count for a thread that doesn't exist (should not raise error)."""
    # Should not raise an error
    tweet_thread_repo.update_tweet_count(999, 10)


def test_delete_existing_thread(
    tweet_thread_repo: TweetThreadRepository, sample_threads: list[TweetThreadResponse]
):
    """Test deleting an existing thread."""
    thread_id = sample_threads[0].id

    # Verify thread exists before deletion
    assert tweet_thread_repo.get(thread_id) is not None

    # Delete the thread
    tweet_thread_repo.delete(thread_id)

    # Verify thread is deleted
    assert tweet_thread_repo.get(thread_id) is None

    # Verify other threads still exist
    remaining_threads = tweet_thread_repo.list_threads()
    assert len(remaining_threads) == 2


def test_delete_nonexistent_thread(
    tweet_thread_repo: TweetThreadRepository, sample_threads: list[TweetThreadResponse]
):
    """Test deleting a thread that doesn't exist (should not raise error)."""
    # Should not raise an error
    tweet_thread_repo.delete(999)

    # Verify existing threads were not affected
    all_threads = tweet_thread_repo.list_threads()
    assert len(all_threads) == 3
