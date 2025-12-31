"""
Tests for the evaluations router endpoints.
"""

from fastapi.testclient import TestClient
from datetime import datetime, timezone
from ..main import app
from ..repositories.models import Evaluation, NoteCreate
from .conftest import EvaluationDepsSetup

client = TestClient(app)


def test_get_note_evaluation_history_success(
    setup_evaluation_deps: EvaluationDepsSetup,
):
    """Test getting evaluation history for a note that exists with evaluations."""
    note_repo, eval_repo = setup_evaluation_deps()

    # Create a note
    note = note_repo.add(
        NoteCreate(
            content="Test content",
            content_hash="test_hash",
            book_id=1,
        )
    )

    # Create evaluations for note_id=1
    eval1 = Evaluation(
        id=1,
        note_id=note.id,
        score=0.85,
        prompt="Test prompt 1",
        response="Test response 1",
        analysis="Test analysis 1",
        model_name="gpt-4",
        created_at=datetime(2025, 8, 1, tzinfo=timezone.utc),
    )
    eval2 = Evaluation(
        id=2,
        note_id=note.id,
        score=0.92,
        prompt="Test prompt 2",
        response="Test response 2",
        analysis="Test analysis 2",
        model_name="gpt-4o",
        created_at=datetime(2025, 8, 15, tzinfo=timezone.utc),
    )
    eval_repo.add(eval1)
    eval_repo.add(eval2)

    response = client.get("/notes/1/evaluations")

    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert data["note"]["id"] == 1
    assert data["note"]["content"] == "Test content"
    assert len(data["evaluations"]) == 2

    # Check first evaluation
    assert data["evaluations"][0]["id"] == 1
    assert data["evaluations"][0]["score"] == 0.85
    assert data["evaluations"][0]["model_name"] == "gpt-4"
    assert data["evaluations"][0]["analysis"] == "Test analysis 1"

    # Check second evaluation
    assert data["evaluations"][1]["id"] == 2
    assert data["evaluations"][1]["score"] == 0.92
    assert data["evaluations"][1]["model_name"] == "gpt-4o"
    assert data["evaluations"][1]["analysis"] == "Test analysis 2"


def test_get_note_evaluation_history_empty(setup_evaluation_deps: EvaluationDepsSetup):
    """Test getting evaluation history for a note that exists but has no evaluations."""
    note_repo, _ = setup_evaluation_deps()

    # Create a note with no evaluations
    note_repo.add(
        NoteCreate(
            content="Test content",
            content_hash="test_hash",
            book_id=1,
        )
    )

    response = client.get("/notes/1/evaluations")

    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert data["note"]["id"] == 1
    assert data["note"]["content"] == "Test content"
    assert data["evaluations"] == []


def test_get_note_evaluation_history_note_not_found(
    setup_evaluation_deps: EvaluationDepsSetup,
):
    """Test getting evaluation history for a note that doesn't exist."""
    _, _ = setup_evaluation_deps()

    response = client.get("/notes/999/evaluations")

    assert response.status_code == 404
