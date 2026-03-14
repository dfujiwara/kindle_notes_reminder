"""
Random content selector for unified /random endpoint.

Provides weighted random selection between Kindle notes, URL chunks, and tweets
based on available content counts.
"""

import random
from dataclasses import dataclass
from typing import Literal

from src.repositories.interfaces import NoteRepositoryInterface
from src.repositories.models import NoteRead, TweetRead, URLChunkRead
from src.tweet_ingestion.repositories.interfaces import TweetRepositoryInterface
from src.url_ingestion.repositories.interfaces import URLChunkRepositoryInterface


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


@dataclass
class RandomTweetSelection:
    """Selection result for a random tweet."""

    content_type: Literal["tweet"]
    item: TweetRead


RandomSelection = RandomNoteSelection | RandomChunkSelection | RandomTweetSelection


def select_random_content(
    note_repo: NoteRepositoryInterface,
    chunk_repo: URLChunkRepositoryInterface,
    tweet_repo: TweetRepositoryInterface,
) -> RandomSelection | None:
    """
    Select random content (note, URL chunk, or tweet) with weighted distribution.

    Distribution is proportional to the number of items with embeddings in each
    repository. For example, if there are 10 notes, 5 chunks, and 5 tweets with
    embeddings, a note will be selected approximately 1/2 of the time.

    Args:
        note_repo: Repository for notes
        chunk_repo: Repository for URL chunks
        tweet_repo: Repository for tweets

    Returns:
        RandomNoteSelection, RandomChunkSelection, or RandomTweetSelection if content
        exists, None if no content with embeddings is found in any repository
    """
    note_count = note_repo.count_with_embeddings()
    chunk_count = chunk_repo.count_with_embeddings()
    tweet_count = tweet_repo.count_with_embeddings()
    total = note_count + chunk_count + tweet_count

    if total == 0:
        return None

    # Weighted random selection
    rand_value = random.randint(0, total - 1)

    if rand_value < note_count:
        note = note_repo.get_random()
        if note:
            return RandomNoteSelection(content_type="note", item=note)
    elif rand_value < note_count + chunk_count:
        chunk = chunk_repo.get_random()
        if chunk:
            return RandomChunkSelection(content_type="url_chunk", item=chunk)
    else:
        tweet = tweet_repo.get_random()
        if tweet:
            return RandomTweetSelection(content_type="tweet", item=tweet)

    return None
