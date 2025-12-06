"""
Evaluation-related endpoints for analytics and insights from AI quality evaluations.
"""

from fastapi import APIRouter, Depends, HTTPException
from src.repositories.interfaces import (
    EvaluationRepositoryInterface,
    NoteRepositoryInterface,
)
from src.repositories.models import NoteEvaluationHistory
from src.dependencies import get_evaluation_repository, get_note_repository
from .response_builders import build_note_response

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
    note_repository: NoteRepositoryInterface = Depends(get_note_repository),
    evaluation_repository: EvaluationRepositoryInterface = Depends(
        get_evaluation_repository
    ),
) -> NoteEvaluationHistory:
    """Get all evaluations for a specific note."""
    # Verify note exists
    note = note_repository.get_by_id(note_id)
    if not note:
        raise HTTPException(status_code=404, detail=f"Note {note_id} not found")

    # Get all evaluations for this note
    evaluations = evaluation_repository.get_by_note_id(note_id)

    return NoteEvaluationHistory(
        note=build_note_response(note),
        evaluations=evaluations,
    )
