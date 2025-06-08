from sqlmodel import Field, SQLModel, Relationship, UniqueConstraint
from datetime import datetime, timezone

metadata = SQLModel.metadata

class Book(SQLModel, table=True):
    __table_args__ = (UniqueConstraint('title', 'author', name='uix_title_author'),)

    id: int | None = Field(default=None, primary_key=True)
    title: str
    author: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationship
    notes: list["Note"] = Relationship(back_populates="book")


class Note(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    content: str
    content_hash: str = Field(unique=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Foreign key to Book
    book_id: int = Field(foreign_key="book.id")
    # Relationship
    book: Book = Relationship(back_populates="notes")
