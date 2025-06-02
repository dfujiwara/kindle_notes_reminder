from sqlmodel import Session, select
from src.repositories.models import Book
from src.repositories.interfaces import BookRepositoryInterface

class BookRepository(BookRepositoryInterface):
    def __init__(self, session: Session):
        self.session = session

    def add(self, book: Book) -> Book:
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
