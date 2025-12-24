"""
Tests for URLRepository methods using in-memory database.
"""

import pytest
from .url_repository import URLRepository
from .models import URLCreate, URLResponse


@pytest.fixture(name="sample_urls")
def sample_urls_fixture(url_repo: URLRepository) -> list[URLResponse]:
    """Create sample URLs and return them as URLResponse objects."""
    urls = [
        URLCreate(url="https://example.com/article1", title="Article One"),
        URLCreate(url="https://example.com/article2", title="Article Two"),
        URLCreate(url="https://example.org/post", title="Blog Post"),
    ]
    for url in urls:
        url_repo.add(url)

    return url_repo.list_urls()


def test_add_new_url(url_repo: URLRepository):
    """Test adding a new URL."""
    url_create = URLCreate(url="https://example.com/new-article", title="New Article")

    result = url_repo.add(url_create)

    assert result.id is not None
    assert result.url == "https://example.com/new-article"
    assert result.title == "New Article"
    assert result.fetched_at is not None
    assert result.created_at is not None


def test_add_duplicate_url_returns_existing(url_repo: URLRepository):
    """Test adding a URL with the same URL returns existing record."""
    url_create = URLCreate(url="https://example.com/duplicate", title="First Title")

    # Add the URL first time
    first_result = url_repo.add(url_create)
    first_id = first_result.id

    # Add the same URL again with different title
    url_create_2 = URLCreate(
        url="https://example.com/duplicate", title="Different Title"
    )
    second_result = url_repo.add(url_create_2)

    # Should return the existing URL, not create a new one
    assert second_result.id == first_id
    assert second_result.url == "https://example.com/duplicate"
    assert second_result.title == "First Title"  # Original title preserved

    # Verify only one URL exists
    all_urls = url_repo.list_urls()
    assert len(all_urls) == 1


def test_add_same_title_different_url(url_repo: URLRepository):
    """Test adding URLs with same title but different URLs creates separate records."""
    url1 = URLCreate(url="https://example.com/page1", title="Same Title")
    url2 = URLCreate(url="https://example.com/page2", title="Same Title")

    result1 = url_repo.add(url1)
    result2 = url_repo.add(url2)

    # Should create two separate URLs
    assert result1.id != result2.id
    assert [result1.url, result2.url] == [
        "https://example.com/page1",
        "https://example.com/page2",
    ]

    # Verify both URLs exist
    all_urls = url_repo.list_urls()
    assert len(all_urls) == 2


def test_get_existing_url(url_repo: URLRepository, sample_urls: list[URLResponse]):
    """Test getting a URL by ID when it exists."""
    url_id = sample_urls[0].id

    result = url_repo.get(url_id)

    assert result is not None
    assert result.id == url_id
    assert result.url == "https://example.com/article1"
    assert result.title == "Article One"


def test_get_nonexistent_url(url_repo: URLRepository):
    """Test getting a URL by ID when it doesn't exist."""
    result = url_repo.get(999)

    assert result is None


def test_get_by_url_existing(url_repo: URLRepository, sample_urls: list[URLResponse]):
    """Test getting a URL by URL string when it exists."""
    result = url_repo.get_by_url("https://example.com/article1")

    assert result is not None
    assert result.id == sample_urls[0].id
    assert result.url == "https://example.com/article1"
    assert result.title == "Article One"


def test_get_by_url_nonexistent(url_repo: URLRepository):
    """Test getting a URL by URL string when it doesn't exist."""
    result = url_repo.get_by_url("https://nonexistent.com/page")

    assert result is None


def test_list_urls_empty(url_repo: URLRepository):
    """Test listing URLs when none exist."""
    result = url_repo.list_urls()

    assert result == []


def test_list_urls_multiple(url_repo: URLRepository, sample_urls: list[URLResponse]):
    """Test listing multiple URLs."""
    result = url_repo.list_urls()

    assert len(result) == 3
    urls = {url.url for url in result}
    assert {
        "https://example.com/article1",
        "https://example.com/article2",
        "https://example.org/post",
    } == urls


def test_delete_existing_url(url_repo: URLRepository, sample_urls: list[URLResponse]):
    """Test deleting an existing URL."""
    url_id = sample_urls[0].id

    # Verify URL exists before deletion
    assert url_repo.get(url_id) is not None

    # Delete the URL
    url_repo.delete(url_id)

    # Verify URL is deleted
    assert url_repo.get(url_id) is None

    # Verify other URLs still exist
    remaining_urls = url_repo.list_urls()
    assert len(remaining_urls) == 2


def test_delete_nonexistent_url(
    url_repo: URLRepository, sample_urls: list[URLResponse]
):
    """Test deleting a URL that doesn't exist (should not raise error)."""
    # Should not raise an error
    url_repo.delete(999)

    # Verify existing URLs were not affected
    all_urls = url_repo.list_urls()
    assert len(all_urls) == 3
