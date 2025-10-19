from sqlmodel import Session, select
from src.repositories.models import Note, NoteCreate, NoteRead, Book
from src.repositories.interfaces import NoteRepositoryInterface
from sqlalchemy import func, column, Integer
from src.types import Embedding


class NoteRepository(NoteRepositoryInterface):
    def __init__(self, session: Session):
        self.session = session

    def add(self, note: NoteCreate) -> NoteRead:
        # Check if a note with the same content hash exists
        statement = select(Note).where(Note.content_hash == note.content_hash)
        existing_note = self.session.exec(statement).first()

        if existing_note:
            return NoteRead.model_validate(existing_note)

        # If no existing note found, create a new one
        db_note = Note(
            content=note.content,
            content_hash=note.content_hash,
            book_id=note.book_id,
            embedding=note.embedding,
        )
        self.session.add(db_note)
        self.session.commit()
        self.session.refresh(db_note)

        return NoteRead.model_validate(db_note)

    def get(self, note_id: int, book_id: int) -> NoteRead | None:
        statement = (
            select(Note).where(Note.id == note_id).where(Note.book_id == book_id)
        )
        note = self.session.exec(statement).first()
        if not note:
            return None

        return NoteRead.model_validate(note)

    def list_notes(self) -> list[NoteRead]:
        statement = select(Note)
        notes = self.session.exec(statement)
        return [NoteRead.model_validate(note) for note in notes]

    def get_by_book_id(self, book_id: int) -> list[NoteRead]:
        statement = select(Note).where(Note.book_id == book_id)
        notes = self.session.exec(statement)
        return [NoteRead.model_validate(note) for note in notes]

    def delete(self, note_id: int) -> None:
        note = self.session.get(Note, note_id)
        if not note:
            return
        self.session.delete(note)
        self.session.commit()

    def get_random(self) -> NoteRead | None:
        statement = select(Note).join(Book).order_by(func.random()).limit(1)
        note = self.session.exec(statement).first()
        if not note:
            return None

        return NoteRead.model_validate(note)

    def find_similar_notes(
        self, note: NoteRead, limit: int = 5, similarity_threshold: float = 0.3
    ) -> list[NoteRead]:
        """
        Find notes similar to the given note using vector similarity.
        Only searches within the same book as the input note.

        Args:
            note: The note to find similar notes for
            limit: Maximum number of similar notes to return (default: 5)
            similarity_threshold: Maximum cosine distance to consider notes similar (default: 0.3)
                                Lower values mean more similar (0 = identical, 1 = completely different)

        Returns:
            A list of similar notes from the same book, ordered by similarity (most similar first)
        """
        if note.embedding is None:
            return []

        distance = Note.embedding_cosine_distance(note.embedding)

        statement = (
            select(Note)
            .where(Note.id != note.id)
            .where(Note.book_id == note.book_id)
            .where(Note.embedding_is_not_null())
            .where(distance <= similarity_threshold)
            .order_by(distance)
            .limit(limit)
        )

        notes = self.session.exec(statement)
        return [NoteRead.model_validate(note) for note in notes]

    def search_notes_by_embedding(
        self, embedding: Embedding, limit: int = 10, similarity_threshold: float = 0.5
    ) -> list[NoteRead]:
        """
        Search for notes similar to the given embedding across all books.

        Args:
            embedding: The embedding vector to search for
            limit: Maximum number of notes to return (default: 10)
            similarity_threshold: Maximum cosine distance to consider notes similar (default: 0.5)
                                Lower values mean more similar (0 = identical, 1 = completely different)

        Returns:
            A list of similar notes from all books, ordered by similarity (most similar first)
        """
        distance = Note.embedding_cosine_distance(embedding)

        statement = (
            select(Note)
            .join(Book)
            .where(Note.embedding_is_not_null())
            .where(distance <= similarity_threshold)
            .order_by(distance)
            .limit(limit)
        )

        notes = self.session.exec(statement)
        return [NoteRead.model_validate(note) for note in notes]

    def get_note_counts_by_book_ids(self, book_ids: list[int]) -> dict[int, int]:
        """
        Get the count of notes for each book ID in the given list.

        Args:
            book_ids: List of book IDs to get note counts for

        Returns:
            Dictionary mapping book_id to note count. Books with no notes won't appear in the result.
        """
        if not book_ids:
            return {}

        # Create column expressions that work with the type system
        book_id_col = column("book_id", Integer)

        statement = (
            select(book_id_col, func.count())
            .select_from(Note)
            .where(book_id_col.in_(book_ids))
            .group_by(book_id_col)
        )

        results = self.session.exec(statement)
        return {book_id: count for book_id, count in results}
