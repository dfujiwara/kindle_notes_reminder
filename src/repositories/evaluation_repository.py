from sqlmodel import Session, select
from src.repositories.models import Evaluation
from src.repositories.interfaces import EvaluationRepositoryInterface


class EvaluationRepository(EvaluationRepositoryInterface):
    def __init__(self, session: Session):
        self.session = session

    def add(self, evaluation: Evaluation) -> Evaluation:
        self.session.add(evaluation)
        self.session.commit()
        self.session.refresh(evaluation)
        return evaluation

    def get_by_note_id(self, note_id: int) -> list[Evaluation]:
        statement = select(Evaluation).where(Evaluation.note_id == note_id)
        return list(self.session.exec(statement))
