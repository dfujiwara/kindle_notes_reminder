from sqlmodel import Field, SQLModel, Relationship, UniqueConstraint, Column
from datetime import datetime, timezone
from pgvector.sqlalchemy import Vector
from typing import Optional, TYPE_CHECKING, cast
from src.types import Embedding

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

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

    @classmethod
    def embedding_cosine_distance(cls, target: Embedding) -> "ColumnElement[float]":
        """Calculate cosine distance to target embedding."""
        embedding_col = cast("ColumnElement[Vector]", cls.__table__.c.embedding)  # type: ignore
        return embedding_col.cosine_distance(target)

    @classmethod
    def embedding_is_not_null(cls) -> "ColumnElement[bool]":
        """Check if embedding is not null."""
        embedding_col = cast("ColumnElement[Vector]", cls.__table__.c.embedding)  # type: ignore
        return embedding_col.is_not(None)
