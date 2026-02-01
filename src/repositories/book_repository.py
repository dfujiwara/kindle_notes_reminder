from sqlmodel import Session, select, col
from src.repositories.models import Book, BookCreate, BookResponse
from src.repositories.interfaces import BookRepositoryInterface


class BookRepository(BookRepositoryInterface):
    def __init__(self, session: Session):
        self.session = session

    def add(self, book: BookCreate) -> BookResponse:
        # Check if a book with the same title and author exists
        statement = select(Book).where(
            Book.title == book.title, Book.author == book.author
        )
        existing_book = self.session.exec(statement).first()

        if existing_book:
            return BookResponse.model_validate(existing_book)

        # If no existing book found, create a new one
        db_book = Book.model_validate(book)
        self.session.add(db_book)
        self.session.flush()
        self.session.refresh(db_book)
        return BookResponse.model_validate(db_book)

    def get(self, book_id: int) -> BookResponse | None:
        book = self.session.get(Book, book_id)
        return BookResponse.model_validate(book) if book else None

    def list_books(self) -> list[BookResponse]:
        statement = select(Book)
        books = self.session.exec(statement).all()
        return [BookResponse.model_validate(book) for book in books]

    def get_by_ids(self, book_ids: list[int]) -> list[BookResponse]:
        statement = select(Book).where(col(Book.id).in_(book_ids))
        books = self.session.exec(statement).all()
        return [BookResponse.model_validate(book) for book in books]

    def delete(self, book_id: int) -> None:
        book = self.session.get(Book, book_id)
        if not book:
            return
        self.session.delete(book)
        self.session.flush()
