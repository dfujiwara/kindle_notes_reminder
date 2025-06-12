from src.notebook_processor import process_notebook_result
from src.repositories.models import Note, Book
from src.notebook_parser import NotebookParseResult
from src.repositories.interfaces import BookRepositoryInterface, NoteRepositoryInterface
import hashlib


class StubBookRepository(BookRepositoryInterface):
    def __init__(self):
        self.books: list[Book] = []

    def add(self, book: Book) -> Book:
        book.id = len(self.books) + 1  # Simulate auto-increment ID
        self.books.append(book)
        return book

    def get(self, book_id: int) -> Book | None:
        return next((book for book in self.books if book.id == book_id), None)

    def list(self) -> list[Book]:
        return self.books

    def delete(self, book_id: int) -> None:
        self.books = [book for book in self.books if book.id != book_id]


class StubNoteRepository(NoteRepositoryInterface):
    def __init__(self):
        self.notes: list[Note] = []

    def add(self, note: Note) -> Note:
        note.id = len(self.notes) + 1  # Simulate auto-increment ID
        self.notes.append(note)
        return note

    def get(self, note_id: int) -> Note | None:
        return next((note for note in self.notes if note.id == note_id), None)

    def list(self) -> list[Note]:
        return self.notes

    def delete(self, note_id: int) -> None:
        self.notes = [note for note in self.notes if note.id != note_id]

    def get_random(self) -> Note | None:
        return self.notes[0] if self.notes else None


def test_process_notebook_result():
    # Use stub repositories
    book_repo = StubBookRepository()
    note_repo = StubNoteRepository()

    # Create a sample NotebookParseResult
    result = NotebookParseResult(
        book_title="Sample Book",
        authors_str="Author Name",
        notes=["Note 1", "Note 2"],
        total_notes=2
    )

    # Call the function
    process_notebook_result(result, book_repo, note_repo)

    # Assertions
    assert len(book_repo.books) == 1
    assert book_repo.books[0].title == "Sample Book"
    assert book_repo.books[0].author == "Author Name"
    assert len(note_repo.notes) == 2
    assert note_repo.notes[0].content == "Note 1"
    assert note_repo.notes[1].content == "Note 2"
    # Assertions for content_hash
    assert note_repo.notes[0].content_hash == hashlib.sha256("Note 1".encode('utf-8')).hexdigest()
    assert note_repo.notes[1].content_hash == hashlib.sha256("Note 2".encode('utf-8')).hexdigest()


def test_process_notebook_result_return_value():
    # Use stub repositories
    book_repo = StubBookRepository()
    note_repo = StubNoteRepository()

    # Create a sample NotebookParseResult
    result = NotebookParseResult(
        book_title="Sample Book",
        authors_str="Author Name",
        notes=["Note 1", "Note 2"],
        total_notes=2
    )

    # Call the function and get the return value
    returned_value = process_notebook_result(result, book_repo, note_repo)

    # Assertions for the book
    assert returned_value['book'] == {
        'id': 1,
        'title': "Sample Book",
        'author': "Author Name"
    }

    # Assertions for the notes
    expected_notes = [
        {'id': 1, 'book_id': 1, 'content': "Note 1", 'content_hash': hashlib.sha256("Note 1".encode('utf-8')).hexdigest()},
        {'id': 2, 'book_id': 1, 'content': "Note 2", 'content_hash': hashlib.sha256("Note 2".encode('utf-8')).hexdigest()}
    ]

    assert len(returned_value['notes']) == len(expected_notes)
    for note, expected in zip(returned_value['notes'], expected_notes):
        assert note == expected
