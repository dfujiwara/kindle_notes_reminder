from sqlmodel import Session, select
from src.repositories.models import Note, Book
from src.repositories.interfaces import NoteRepositoryInterface
from sqlalchemy import func
from src.types import Embedding


class NoteRepository(NoteRepositoryInterface):
    def __init__(self, session: Session):
        self.session = session

    def add(self, note: Note) -> Note:
        # Check if a note with the same content hash exists
        statement = select(Note).where(Note.content_hash == note.content_hash)
        existing_note = self.session.exec(statement).first()

        if existing_note:
            return existing_note

        # If no existing note found, create a new one
        self.session.add(note)
        self.session.commit()
        self.session.refresh(note)
        return note

    def get(self, note_id: int) -> Note | None:
        return self.session.get(Note, note_id)

    def list_notes(self) -> list[Note]:
        statement = select(Note)
        return list(self.session.exec(statement))

    def get_by_book_id(self, book_id: int) -> list[Note]:
        statement = select(Note).where(Note.book_id == book_id)
        return list(self.session.exec(statement))

    def delete(self, note_id: int) -> None:
        note = self.get(note_id)
        if not note:
            return
        self.session.delete(note)
        self.session.commit()

    def get_random(self) -> Note | None:
        statement = select(Note).join(Book).order_by(func.random()).limit(1)
        return self.session.exec(statement).first()

    def update_embedding(self, note: Note, embedding: Embedding) -> Note:
        """
        Update the embedding for a note.

        Args:
            note: The note to update
            embedding: The embedding vector to update the note with

        Returns:
            The updated note with the new embedding
        """
        note.embedding = embedding
        self.session.add(note)
        self.session.commit()
        self.session.refresh(note)
        return note

    def find_similar_notes(
        self, note: Note, limit: int = 5, similarity_threshold: float = 0.3
    ) -> list[Note]:
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

        return list(self.session.exec(statement))

    def search_notes_by_embedding(
        self, embedding: Embedding, limit: int = 10, similarity_threshold: float = 0.5
    ) -> list[Note]:
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

        return list(self.session.exec(statement))
