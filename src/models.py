from sqlmodel import Field, SQLModel, Relationship

metadata = SQLModel.metadata

class Book(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    author: str

    # Relationship
    notes: list["Note"] = Relationship(back_populates="book")


class Note(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    content: str

    # Foreign key to Book
    book_id: int = Field(foreign_key="book.id")
    # Relationship
    book: Book = Relationship(back_populates="notes")
