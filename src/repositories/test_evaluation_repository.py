"""
Tests for EvaluationRepository methods using in-memory database.
"""

import pytest
from datetime import datetime, timezone, timedelta
from .evaluation_repository import EvaluationRepository
from .book_repository import BookRepository
from .note_repository import NoteRepository
from .models import BookCreate, NoteCreate, Evaluation


@pytest.fixture(name="sample_note_id")
def sample_note_id_fixture(book_repo: BookRepository, note_repo: NoteRepository) -> int:
    """Create a sample book and note, return the note ID."""
    book = BookCreate(title="Test Book", author="Test Author")
    book = book_repo.add(book)
    assert book.id is not None

    note = NoteCreate(
        content="Test note content",
        content_hash="test_hash",
        book_id=book.id,
    )
    note = note_repo.add(note)
    assert note.id is not None
    return note.id


@pytest.fixture(name="another_note_id")
def another_note_id_fixture(
    book_repo: BookRepository, note_repo: NoteRepository
) -> int:
    """Create another sample book and note, return the note ID."""
    book = BookCreate(title="Another Book", author="Another Author")
    book = book_repo.add(book)
    assert book.id is not None

    note = NoteCreate(
        content="Another note content",
        content_hash="another_hash",
        book_id=book.id,
    )
    note = note_repo.add(note)
    assert note.id is not None
    return note.id


def test_add_evaluation(evaluation_repo: EvaluationRepository, sample_note_id: int):
    """Test adding a new evaluation."""
    evaluation = Evaluation(
        score=0.85,
        prompt="Test prompt",
        response="Test response",
        analysis="Test analysis",
        model_name="gpt-4",
        note_id=sample_note_id,
    )

    result = evaluation_repo.add(evaluation)

    assert result.id is not None
    assert result.score == 0.85
    assert result.prompt == "Test prompt"
    assert result.response == "Test response"
    assert result.analysis == "Test analysis"
    assert result.model_name == "gpt-4"
    assert result.note_id == sample_note_id
    assert result.created_at is not None
    assert isinstance(result.created_at, datetime)


def test_get_by_note_id_success(
    evaluation_repo: EvaluationRepository, sample_note_id: int
):
    """Test retrieving evaluations for a note that has evaluations."""
    # Add multiple evaluations
    eval1 = Evaluation(
        score=0.8,
        prompt="First prompt",
        response="First response",
        analysis="First analysis",
        note_id=sample_note_id,
    )
    eval2 = Evaluation(
        score=0.9,
        prompt="Second prompt",
        response="Second response",
        analysis="Second analysis",
        note_id=sample_note_id,
    )

    evaluation_repo.add(eval1)
    evaluation_repo.add(eval2)

    results = evaluation_repo.get_by_note_id(sample_note_id)

    assert len(results) == 2
    assert all(e.note_id == sample_note_id for e in results)


def test_get_by_note_id_empty(evaluation_repo: EvaluationRepository):
    """Test retrieving evaluations when none exist for a note."""
    results = evaluation_repo.get_by_note_id(999)
    assert results == []


def test_get_by_note_id_ordering(
    evaluation_repo: EvaluationRepository, sample_note_id: int
):
    """Test that get_by_note_id returns evaluations ordered by created_at DESC."""
    # Create evaluations with explicit timestamps
    now = datetime.now(timezone.utc)
    older_time = now - timedelta(hours=2)
    newest_time = now + timedelta(hours=1)

    # Add evaluations in non-chronological order
    eval2 = Evaluation(
        score=0.7,
        prompt="Middle eval",
        response="Middle response",
        analysis="Middle analysis",
        note_id=sample_note_id,
        created_at=now,
    )
    eval1 = Evaluation(
        score=0.6,
        prompt="Oldest eval",
        response="Oldest response",
        analysis="Oldest analysis",
        note_id=sample_note_id,
        created_at=older_time,
    )
    eval3 = Evaluation(
        score=0.9,
        prompt="Newest eval",
        response="Newest response",
        analysis="Newest analysis",
        note_id=sample_note_id,
        created_at=newest_time,
    )

    evaluation_repo.add(eval2)
    evaluation_repo.add(eval1)
    evaluation_repo.add(eval3)

    results = evaluation_repo.get_by_note_id(sample_note_id)

    assert len(results) == 3
    # Should be ordered by created_at DESC (newest first)
    assert results[0].prompt == "Newest eval"
    assert results[1].prompt == "Middle eval"
    assert results[2].prompt == "Oldest eval"


def test_get_by_note_id_filters_by_note(
    evaluation_repo: EvaluationRepository,
    sample_note_id: int,
    another_note_id: int,
):
    """Test that get_by_note_id only returns evaluations for the specified note."""
    # Add evaluations for first note
    eval1 = Evaluation(
        score=0.8,
        prompt="Note 1 eval",
        response="Note 1 response",
        analysis="Note 1 analysis",
        note_id=sample_note_id,
    )

    # Add evaluations for second note
    eval2 = Evaluation(
        score=0.9,
        prompt="Note 2 eval",
        response="Note 2 response",
        analysis="Note 2 analysis",
        note_id=another_note_id,
    )

    evaluation_repo.add(eval1)
    evaluation_repo.add(eval2)

    # Get evaluations for first note
    results1 = evaluation_repo.get_by_note_id(sample_note_id)
    assert len(results1) == 1
    assert results1[0].note_id == sample_note_id
    assert results1[0].prompt == "Note 1 eval"

    # Get evaluations for second note
    results2 = evaluation_repo.get_by_note_id(another_note_id)
    assert len(results2) == 1
    assert results2[0].note_id == another_note_id
    assert results2[0].prompt == "Note 2 eval"
