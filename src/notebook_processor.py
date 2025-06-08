from src.notebook_parser import NotebookParseResult
from src.repositories.models import Book, Note
import hashlib
from src.repositories.interfaces import BookRepositoryInterface, NoteRepositoryInterface


def process_notebook_result(result: NotebookParseResult, book_repo: BookRepositoryInterface, note_repo: NoteRepositoryInterface):
    # Create a Book instance
    book = Book(title=result.book_title, author=result.authors_str)

    # Add the book to the repository
    book = book_repo.add(book)

    if book.id is None:
        raise ValueError("Book ID is None after adding to repository")

    # Iterate over notes and add them to the repository
    for note_content in result.notes:
        # Generate a stable hash using hashlib
        content_hash = hashlib.sha256(note_content.encode('utf-8')).hexdigest()
        note = Note(content=note_content, content_hash=content_hash, book_id=book.id)
        note_repo.add(note)
