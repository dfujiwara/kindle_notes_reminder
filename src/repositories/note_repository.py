from sqlmodel import Session, select
from src.repositories.models import Note
from src.repositories.interfaces import NoteRepositoryInterface
from sqlalchemy import func

class NoteRepository(NoteRepositoryInterface):
    def __init__(self, session: Session):
        self.session = session

    def add(self, note: Note) -> Note:
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
        statement = select(Note).order_by(func.random()).limit(1)
        result = self.session.exec(statement).first()
        return result
