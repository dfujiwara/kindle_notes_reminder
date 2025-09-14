from sqlmodel import Field, SQLModel, Relationship, UniqueConstraint, Column
from datetime import datetime, timezone
from pgvector.sqlalchemy import Vector
from typing import Optional, TYPE_CHECKING, cast
from src.types import Embedding

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

metadata = SQLModel.metadata


class BookBase(SQLModel):
    """Base model with shared fields"""

    title: str
    author: str


class BookCreate(BookBase):
    """Model for creating new books (no id required)"""

    pass


class Book(BookBase, table=True):
    """Database table model"""

    __table_args__ = (UniqueConstraint("title", "author", name="uix_title_author"),)

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationship
    notes: list["Note"] = Relationship(back_populates="book")


class BookRead(BookBase):
    """Model for reading books (id is guaranteed to exist)"""

    id: int
    created_at: datetime


class BookResponse(SQLModel):
    id: int
    title: str
    author: str
    created_at: datetime


class BookWithNotesResponse(BookResponse):
    note_count: int


class NoteBase(SQLModel):
    """Base model with shared fields"""

    content: str
    content_hash: str = Field(unique=True)
    book_id: int = Field(foreign_key="book.id")
    embedding: Optional[Embedding] = None


class NoteCreate(NoteBase):
    """Model for creating new notes (no id required)"""

    pass


class Note(NoteBase, table=True):
    """Database table model"""

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    embedding: Optional[Embedding] = Field(
        default=None, sa_column=Column("embedding", Vector(1536))
    )  # OpenAI embeddings are 1536 dimensions

    # Relationships
    book: Book = Relationship(back_populates="notes")
    evaluations: list["Evaluation"] = Relationship(back_populates="note")

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


class NoteRead(NoteBase):
    """Model for reading notes (id is guaranteed to exist)"""

    id: int
    created_at: datetime


class Evaluation(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    score: float = Field(ge=0.0, le=1.0)
    prompt: str
    response: str
    analysis: str
    model_name: str = Field(default="gpt-4")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Foreign key to Note
    note_id: int = Field(foreign_key="note.id")
    # Relationship
    note: Note = Relationship(back_populates="evaluations")
