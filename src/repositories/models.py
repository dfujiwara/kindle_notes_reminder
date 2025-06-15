from sqlmodel import Field, SQLModel, Relationship, UniqueConstraint, Column
from datetime import datetime, timezone
from pgvector.sqlalchemy import Vector  # type: ignore
from typing import Optional
from src.types import Embedding

metadata = SQLModel.metadata


class Book(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("title", "author", name="uix_title_author"),)

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
    embedding: Optional[Embedding] = Field(
        default=None, sa_column=Column("embedding", Vector(1536))
    )  # OpenAI embeddings are 1536 dimensions

    # Foreign key to Book
    book_id: int = Field(foreign_key="book.id")
    # Relationship
    book: Book = Relationship(back_populates="notes")
