"""
Tests for BookRepository methods using in-memory database.
"""

import pytest
from .book_repository import BookRepository
from .models import BookCreate, BookResponse


@pytest.fixture(name="sample_books")
def sample_books_fixture(book_repo: BookRepository) -> list[BookResponse]:
    """Create sample books and return them as BookResponse objects."""
    books = [
        BookCreate(title="Book One", author="Author A"),
        BookCreate(title="Book Two", author="Author B"),
        BookCreate(title="Book Three", author="Author C"),
    ]
    for book in books:
        book_repo.add(book)

    return book_repo.list_books()


def test_add_new_book(book_repo: BookRepository):
    """Test adding a new book."""
    book_create = BookCreate(title="New Book", author="New Author")

    result = book_repo.add(book_create)

    assert result.id is not None
    assert result.title == "New Book"
    assert result.author == "New Author"


def test_add_duplicate_book(book_repo: BookRepository):
    """Test adding a book with the same title and author returns existing book."""
    book_create = BookCreate(title="Duplicate Book", author="Same Author")

    # Add the book first time
    first_result = book_repo.add(book_create)
    first_id = first_result.id

    # Add the same book again
    second_result = book_repo.add(book_create)

    # Should return the existing book, not create a new one
    assert second_result.id == first_id
    assert second_result.title == "Duplicate Book"
    assert second_result.author == "Same Author"

    # Verify only one book exists
    all_books = book_repo.list_books()
    assert len(all_books) == 1


def test_add_same_title_different_author(book_repo: BookRepository):
    """Test adding books with same title but different authors creates separate books."""
    book1 = BookCreate(title="Same Title", author="Author A")
    book2 = BookCreate(title="Same Title", author="Author B")

    result1 = book_repo.add(book1)
    result2 = book_repo.add(book2)

    # Should create two separate books
    assert result1.id != result2.id
    assert result1.author == "Author A"
    assert result2.author == "Author B"

    # Verify both books exist
    all_books = book_repo.list_books()
    assert len(all_books) == 2


def test_get_existing_book(book_repo: BookRepository, sample_books: list[BookResponse]):
    """Test getting a book by ID when it exists."""
    book_id = sample_books[0].id

    result = book_repo.get(book_id)

    assert result is not None
    assert result.id == book_id
    assert result.title == "Book One"
    assert result.author == "Author A"


def test_get_nonexistent_book(book_repo: BookRepository):
    """Test getting a book by ID when it doesn't exist."""
    result = book_repo.get(999)

    assert result is None


def test_list_books_empty(book_repo: BookRepository):
    """Test listing books when none exist."""
    result = book_repo.list_books()

    assert result == []


def test_list_books_multiple(
    book_repo: BookRepository, sample_books: list[BookResponse]
):
    """Test listing multiple books."""
    result = book_repo.list_books()

    assert len(result) == 3
    titles = [book.title for book in result]
    assert "Book One" in titles
    assert "Book Two" in titles
    assert "Book Three" in titles


def test_get_by_ids_all_exist(
    book_repo: BookRepository, sample_books: list[BookResponse]
):
    """Test getting books by IDs when all exist."""
    book_ids = [sample_books[0].id, sample_books[2].id]

    result = book_repo.get_by_ids(book_ids)

    assert len(result) == 2
    result_ids = [book.id for book in result]
    assert sample_books[0].id in result_ids
    assert sample_books[2].id in result_ids


def test_get_by_ids_some_exist(
    book_repo: BookRepository, sample_books: list[BookResponse]
):
    """Test getting books by IDs when only some exist."""
    book_ids = [sample_books[0].id, 999]

    result = book_repo.get_by_ids(book_ids)

    # Should only return the existing book
    assert len(result) == 1
    assert result[0].id == sample_books[0].id


def test_get_by_ids_none_exist(book_repo: BookRepository):
    """Test getting books by IDs when none exist."""
    book_ids = [998, 999]

    result = book_repo.get_by_ids(book_ids)

    assert result == []


def test_get_by_ids_empty_list(book_repo: BookRepository):
    """Test getting books with empty ID list."""
    result = book_repo.get_by_ids([])

    assert result == []


def test_delete_existing_book(
    book_repo: BookRepository, sample_books: list[BookResponse]
):
    """Test deleting an existing book."""
    book_id = sample_books[0].id

    # Verify book exists before deletion
    assert book_repo.get(book_id) is not None

    # Delete the book
    book_repo.delete(book_id)

    # Verify book is deleted
    assert book_repo.get(book_id) is None

    # Verify other books still exist
    remaining_books = book_repo.list_books()
    assert len(remaining_books) == 2


def test_delete_nonexistent_book(
    book_repo: BookRepository, sample_books: list[BookResponse]
):
    """Test deleting a book that doesn't exist (should not raise error)."""
    # Should not raise an error
    book_repo.delete(999)

    # Verify existing books were not affected
    all_books = book_repo.list_books()
    assert len(all_books) == 3
