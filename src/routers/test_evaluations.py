"""
Tests for the evaluations router endpoints.
"""

from fastapi.testclient import TestClient
from datetime import datetime, timezone
from ..main import app
from ..dependencies import get_evaluation_repository, get_note_repository
from ..repositories.models import Evaluation, NoteCreate
from ..test_utils import StubEvaluationRepository, StubNoteRepository

client = TestClient(app)


def test_get_note_evaluation_history_success():
    """Test getting evaluation history for a note that exists with evaluations."""
    note_repo = StubNoteRepository()
    eval_repo = StubEvaluationRepository()

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

    app.dependency_overrides[get_note_repository] = lambda: note_repo
    app.dependency_overrides[get_evaluation_repository] = lambda: eval_repo

    try:
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
    finally:
        app.dependency_overrides.clear()


def test_get_note_evaluation_history_empty():
    """Test getting evaluation history for a note that exists but has no evaluations."""
    note_repo = StubNoteRepository()
    eval_repo = StubEvaluationRepository()

    # Create a note with no evaluations
    note_repo.add(
        NoteCreate(
            content="Test content",
            content_hash="test_hash",
            book_id=1,
        )
    )

    app.dependency_overrides[get_note_repository] = lambda: note_repo
    app.dependency_overrides[get_evaluation_repository] = lambda: eval_repo

    try:
        response = client.get("/notes/1/evaluations")

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert data["note"]["id"] == 1
        assert data["note"]["content"] == "Test content"
        assert data["evaluations"] == []
    finally:
        app.dependency_overrides.clear()


def test_get_note_evaluation_history_note_not_found():
    """Test getting evaluation history for a note that doesn't exist."""
    note_repo = StubNoteRepository()
    eval_repo = StubEvaluationRepository()

    # Don't add any notes to the repository

    app.dependency_overrides[get_note_repository] = lambda: note_repo
    app.dependency_overrides[get_evaluation_repository] = lambda: eval_repo

    try:
        response = client.get("/notes/999/evaluations")

        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
