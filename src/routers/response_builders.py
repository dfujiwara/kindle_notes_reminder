"""Helper functions for building API response models."""

from src.repositories.models import (
    BookResponse,
    NoteRead,
    NoteResponse,
    NoteWithRelatedNotesResponse,
)


def build_note_response(note: NoteRead) -> NoteResponse:
    """Build a NoteResponse from a NoteRead model."""
    return NoteResponse(
        id=note.id,
        content=note.content,
        created_at=note.created_at,
    )


def build_note_with_related_notes_response(
    book: BookResponse,
    note: NoteRead,
    related_notes: list[NoteRead],
) -> NoteWithRelatedNotesResponse:
    """Build metadata response with book, note, and related notes."""
    return NoteWithRelatedNotesResponse(
        book=book,
        note=build_note_response(note),
        related_notes=[build_note_response(n) for n in related_notes],
    )
