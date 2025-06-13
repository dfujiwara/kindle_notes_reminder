from sqlmodel import Session, select
from src.repositories.models import Book
from src.repositories.interfaces import BookRepositoryInterface

class BookRepository(BookRepositoryInterface):
    def __init__(self, session: Session):
        self.session = session

    def add(self, book: Book) -> Book:
        # Check if a book with the same title and author exists
        statement = select(Book).where(
            Book.title == book.title,
            Book.author == book.author
        )
        existing_book = self.session.exec(statement).first()

        if existing_book:
            return existing_book

        # If no existing book found, create a new one
        self.session.add(book)
        self.session.commit()
        self.session.refresh(book)
        return book

    def get(self, book_id: int) -> Book | None:
        return self.session.get(Book, book_id)

    def list(self) -> list[Book]:
        statement = select(Book)
        return list(self.session.exec(statement))

    def delete(self, book_id: int) -> None:
        book = self.get(book_id)
        if not book:
            return
        self.session.delete(book)
        self.session.commit()
