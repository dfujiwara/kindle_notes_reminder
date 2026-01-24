from sqlmodel import Session, col, select

from src.repositories.models import TweetThread, TweetThreadCreate, TweetThreadResponse

from .interfaces import TweetThreadRepositoryInterface


class TweetThreadRepository(TweetThreadRepositoryInterface):
    def __init__(self, session: Session):
        self.session = session

    def add(self, thread: TweetThreadCreate) -> TweetThreadResponse:
        # Check if a thread with the same root_tweet_id exists
        statement = select(TweetThread).where(
            TweetThread.root_tweet_id == thread.root_tweet_id
        )
        existing_thread = self.session.exec(statement).first()

        if existing_thread:
            return TweetThreadResponse.model_validate(existing_thread)

        # If no existing thread found, create a new one
        db_thread = TweetThread.model_validate(thread)
        self.session.add(db_thread)
        self.session.commit()
        self.session.refresh(db_thread)
        return TweetThreadResponse.model_validate(db_thread)

    def get(self, id: int) -> TweetThreadResponse | None:
        thread = self.session.get(TweetThread, id)
        return TweetThreadResponse.model_validate(thread) if thread else None

    def get_by_root_tweet_id(self, root_tweet_id: str) -> TweetThreadResponse | None:
        statement = select(TweetThread).where(
            TweetThread.root_tweet_id == root_tweet_id
        )
        db_thread = self.session.exec(statement).first()
        return TweetThreadResponse.model_validate(db_thread) if db_thread else None

    def get_by_ids(self, ids: list[int]) -> list[TweetThreadResponse]:
        if not ids:
            return []
        statement = select(TweetThread).where(col(TweetThread.id).in_(ids))
        threads = self.session.exec(statement).all()
        return [TweetThreadResponse.model_validate(thread) for thread in threads]

    def list_threads(self) -> list[TweetThreadResponse]:
        statement = select(TweetThread)
        threads = self.session.exec(statement).all()
        return [TweetThreadResponse.model_validate(thread) for thread in threads]

    def update_tweet_count(self, thread_id: int, tweet_count: int) -> None:
        thread = self.session.get(TweetThread, thread_id)
        if not thread:
            return
        thread.tweet_count = tweet_count
        self.session.add(thread)
        self.session.commit()

    def delete(self, thread_id: int) -> None:
        thread = self.session.get(TweetThread, thread_id)
        if not thread:
            return
        self.session.delete(thread)
        self.session.commit()
