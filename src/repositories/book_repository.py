from sqlmodel import Session, select, col
from src.repositories.models import Book, BookCreate, BookRead
from src.repositories.interfaces import BookRepositoryInterface


class BookRepository(BookRepositoryInterface):
    def __init__(self, session: Session):
        self.session = session

    def add(self, book: BookCreate) -> BookRead:
        # Check if a book with the same title and author exists
        statement = select(Book).where(
            Book.title == book.title, Book.author == book.author
        )
        existing_book = self.session.exec(statement).first()

        if existing_book:
            return BookRead.model_validate(existing_book)

        # If no existing book found, create a new one
        db_book = Book.model_validate(book)
        self.session.add(db_book)
        self.session.commit()
        self.session.refresh(db_book)
        return BookRead.model_validate(db_book)

    def get(self, book_id: int) -> BookRead | None:
        book = self.session.get(Book, book_id)
        return BookRead.model_validate(book) if book else None

    def list_books(self) -> list[BookRead]:
        statement = select(Book)
        books = self.session.exec(statement).all()
        return [BookRead.model_validate(book) for book in books]

    def get_by_ids(self, book_ids: list[int]) -> list[BookRead]:
        statement = select(Book).where(col(Book.id).in_(book_ids))
        books = self.session.exec(statement).all()
        return [BookRead.model_validate(book) for book in books]

    def delete(self, book_id: int) -> None:
        book = self.session.get(Book, book_id)
        if not book:
            return
        self.session.delete(book)
        self.session.commit()
