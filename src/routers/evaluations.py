"""
Evaluation-related endpoints for analytics and insights from AI quality evaluations.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from src.repositories.interfaces import EvaluationRepositoryInterface
from src.repositories.models import NoteEvaluationHistory, Note
from src.dependencies import get_evaluation_repository
from src.database import get_session

router = APIRouter(tags=["evaluations"])


@router.get(
    "/notes/{note_id}/evaluations",
    summary="Get evaluation history for a note",
    description="""
    Retrieve all historical evaluations for a specific note.

    This endpoint returns chronological evaluation history, enabling:
    - Tracking quality improvements over time
    - Comparing before/after when regenerating context
    - Validating prompt or model changes
    - A/B testing different approaches on the same content

    Evaluations are ordered by creation time (oldest to newest).
    Returns empty list if note has never been evaluated.
    """,
    response_description="Historical evaluation records for the note",
    responses={
        404: {"description": "Note not found"},
        200: {"description": "Evaluation history (may be empty list)"},
    },
)
async def get_note_evaluation_history(
    note_id: int,
    evaluation_repository: EvaluationRepositoryInterface = Depends(
        get_evaluation_repository
    ),
    session: Session = Depends(get_session),
) -> NoteEvaluationHistory:
    """Get all evaluations for a specific note."""
    # Verify note exists
    statement = select(Note).where(Note.id == note_id)
    note = session.exec(statement).first()
    if not note:
        raise HTTPException(status_code=404, detail=f"Note {note_id} not found")

    # Get all evaluations for this note
    evaluations = evaluation_repository.get_by_note_id(note_id)

    return NoteEvaluationHistory(
        note_id=note_id,
        evaluations=evaluations,
    )
