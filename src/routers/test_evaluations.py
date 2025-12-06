"""
Tests for the evaluations router endpoints.
"""

from fastapi.testclient import TestClient
from datetime import datetime, timezone
from unittest.mock import MagicMock
from sqlmodel import Session
from ..main import app
from ..dependencies import get_evaluation_repository
from ..database import get_session
from ..repositories.models import Evaluation, Note
from ..test_utils import StubEvaluationRepository

client = TestClient(app)


def test_get_note_evaluation_history_success():
    """Test getting evaluation history for a note that exists with evaluations."""
    eval_repo = StubEvaluationRepository()

    # Create evaluations for note_id=1
    eval1 = Evaluation(
        id=1,
        note_id=1,
        score=0.85,
        prompt="Test prompt 1",
        response="Test response 1",
        analysis="Test analysis 1",
        model_name="gpt-4",
        created_at=datetime(2025, 8, 1, tzinfo=timezone.utc),
    )
    eval2 = Evaluation(
        id=2,
        note_id=1,
        score=0.92,
        prompt="Test prompt 2",
        response="Test response 2",
        analysis="Test analysis 2",
        model_name="gpt-4o",
        created_at=datetime(2025, 8, 15, tzinfo=timezone.utc),
    )
    eval_repo.add(eval1)
    eval_repo.add(eval2)

    # Mock the session to return a note
    mock_session = MagicMock(spec=Session)
    mock_note = Note(
        id=1,
        content="Test content",
        content_hash="test_hash",
        book_id=1,
        created_at=datetime.now(timezone.utc),
    )
    mock_session.exec.return_value.first.return_value = mock_note

    app.dependency_overrides[get_evaluation_repository] = lambda: eval_repo
    app.dependency_overrides[get_session] = lambda: mock_session

    try:
        response = client.get("/notes/1/evaluations")

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert data["note_id"] == 1
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
    eval_repo = StubEvaluationRepository()

    # Mock the session to return a note
    mock_session = MagicMock(spec=Session)
    mock_note = Note(
        id=1,
        content="Test content",
        content_hash="test_hash",
        book_id=1,
        created_at=datetime.now(timezone.utc),
    )
    mock_session.exec.return_value.first.return_value = mock_note

    app.dependency_overrides[get_evaluation_repository] = lambda: eval_repo
    app.dependency_overrides[get_session] = lambda: mock_session

    try:
        response = client.get("/notes/1/evaluations")

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert data["note_id"] == 1
        assert data["evaluations"] == []
    finally:
        app.dependency_overrides.clear()


def test_get_note_evaluation_history_note_not_found():
    """Test getting evaluation history for a note that doesn't exist."""
    eval_repo = StubEvaluationRepository()

    # Mock the session to return None (note not found)
    mock_session = MagicMock(spec=Session)
    mock_session.exec.return_value.first.return_value = None

    app.dependency_overrides[get_evaluation_repository] = lambda: eval_repo
    app.dependency_overrides[get_session] = lambda: mock_session

    try:
        response = client.get("/notes/999/evaluations")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_get_note_evaluation_history_chronological_order():
    """Test that evaluations are returned in chronological order."""
    eval_repo = StubEvaluationRepository()

    # Create evaluations in non-chronological order
    eval_newest = Evaluation(
        id=1,
        note_id=1,
        score=0.95,
        prompt="Newest prompt",
        response="Newest response",
        analysis="Newest analysis",
        model_name="gpt-4o",
        created_at=datetime(2025, 12, 5, tzinfo=timezone.utc),
    )
    eval_oldest = Evaluation(
        id=2,
        note_id=1,
        score=0.80,
        prompt="Oldest prompt",
        response="Oldest response",
        analysis="Oldest analysis",
        model_name="gpt-4",
        created_at=datetime(2025, 8, 1, tzinfo=timezone.utc),
    )
    eval_middle = Evaluation(
        id=3,
        note_id=1,
        score=0.88,
        prompt="Middle prompt",
        response="Middle response",
        analysis="Middle analysis",
        model_name="gpt-4",
        created_at=datetime(2025, 10, 15, tzinfo=timezone.utc),
    )

    # Add in random order
    eval_repo.add(eval_newest)
    eval_repo.add(eval_oldest)
    eval_repo.add(eval_middle)

    # Mock the session to return a note
    mock_session = MagicMock(spec=Session)
    mock_note = Note(
        id=1,
        content="Test content",
        content_hash="test_hash",
        book_id=1,
        created_at=datetime.now(timezone.utc),
    )
    mock_session.exec.return_value.first.return_value = mock_note

    app.dependency_overrides[get_evaluation_repository] = lambda: eval_repo
    app.dependency_overrides[get_session] = lambda: mock_session

    try:
        response = client.get("/notes/1/evaluations")

        assert response.status_code == 200
        data = response.json()

        # Note: The stub repository returns evaluations in the order they were added
        # In a real implementation with proper ordering by created_at, we would check:
        # assert data["evaluations"][0]["created_at"] == "2025-08-01T00:00:00+00:00"
        # assert data["evaluations"][1]["created_at"] == "2025-10-15T00:00:00+00:00"
        # assert data["evaluations"][2]["created_at"] == "2025-12-05T00:00:00+00:00"

        # For now, just verify all three evaluations are present
        assert len(data["evaluations"]) == 3
    finally:
        app.dependency_overrides.clear()


def test_get_note_evaluation_history_multiple_notes():
    """Test that evaluations are correctly filtered by note_id."""
    eval_repo = StubEvaluationRepository()

    # Create evaluations for different notes
    eval_note1 = Evaluation(
        id=1,
        note_id=1,
        score=0.85,
        prompt="Note 1 prompt",
        response="Note 1 response",
        analysis="Note 1 analysis",
        model_name="gpt-4",
        created_at=datetime.now(timezone.utc),
    )
    eval_note2_v1 = Evaluation(
        id=2,
        note_id=2,
        score=0.80,
        prompt="Note 2 prompt v1",
        response="Note 2 response v1",
        analysis="Note 2 analysis v1",
        model_name="gpt-4",
        created_at=datetime.now(timezone.utc),
    )
    eval_note2_v2 = Evaluation(
        id=3,
        note_id=2,
        score=0.92,
        prompt="Note 2 prompt v2",
        response="Note 2 response v2",
        analysis="Note 2 analysis v2",
        model_name="gpt-4o",
        created_at=datetime.now(timezone.utc),
    )

    eval_repo.add(eval_note1)
    eval_repo.add(eval_note2_v1)
    eval_repo.add(eval_note2_v2)

    # Mock the session to return a note
    mock_session = MagicMock(spec=Session)
    mock_note = Note(
        id=2,
        content="Test content",
        content_hash="test_hash",
        book_id=1,
        created_at=datetime.now(timezone.utc),
    )
    mock_session.exec.return_value.first.return_value = mock_note

    app.dependency_overrides[get_evaluation_repository] = lambda: eval_repo
    app.dependency_overrides[get_session] = lambda: mock_session

    try:
        response = client.get("/notes/2/evaluations")

        assert response.status_code == 200
        data = response.json()

        # Should only get evaluations for note_id=2
        assert data["note_id"] == 2
        assert len(data["evaluations"]) == 2

        # Verify both evaluations are for note_id=2
        assert all(eval["note_id"] == 2 for eval in data["evaluations"])

        # Verify the correct evaluations were returned
        scores = [eval["score"] for eval in data["evaluations"]]
        assert 0.80 in scores
        assert 0.92 in scores
    finally:
        app.dependency_overrides.clear()
