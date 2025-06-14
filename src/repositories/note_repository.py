from sqlmodel import Session, select
from src.repositories.models import Note, Book
from src.repositories.interfaces import NoteRepositoryInterface
from sqlalchemy import func

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

    def list(self) -> list[Note]:
        statement = select(Note)
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
