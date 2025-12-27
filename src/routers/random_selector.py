"""
Random content selector for unified /random endpoint.

Provides weighted random selection between Kindle notes and URL chunks
based on available content counts.
"""

import random
from dataclasses import dataclass
from typing import Literal

from src.repositories.interfaces import (
    NoteRepositoryInterface,
    URLChunkRepositoryInterface,
)
from src.repositories.models import NoteRead, URLChunkRead


@dataclass
class RandomNoteSelection:
    """Selection result for a random note."""

    content_type: Literal["note"]
    item: NoteRead


@dataclass
class RandomChunkSelection:
    """Selection result for a random URL chunk."""

    content_type: Literal["url_chunk"]
    item: URLChunkRead


RandomSelection = RandomNoteSelection | RandomChunkSelection


def select_random_content(
    note_repo: NoteRepositoryInterface,
    chunk_repo: URLChunkRepositoryInterface,
) -> RandomSelection | None:
    """
    Select random content (note or URL chunk) with weighted distribution.

    Distribution is proportional to the number of items with embeddings in each
    repository. For example, if there are 10 notes and 5 chunks with embeddings,
    a note will be selected approximately 2/3 of the time.

    Args:
        note_repo: Repository for notes
        chunk_repo: Repository for URL chunks

    Returns:
        RandomNoteSelection or RandomChunkSelection if content exists,
        None if no content with embeddings is found in either repository
    """
    note_count = note_repo.count_with_embeddings()
    chunk_count = chunk_repo.count_with_embeddings()
    total = note_count + chunk_count

    if total == 0:
        return None

    # Weighted random selection
    rand_value = random.randint(0, total - 1)

    if rand_value < note_count:
        note = note_repo.get_random()
        if note:
            return RandomNoteSelection(content_type="note", item=note)
    else:
        chunk = chunk_repo.get_random()
        if chunk:
            return RandomChunkSelection(content_type="url_chunk", item=chunk)

    return None
