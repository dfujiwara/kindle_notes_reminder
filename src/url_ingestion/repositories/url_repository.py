from sqlmodel import Session, col, select

from src.repositories.models import URL, URLCreate, URLResponse

from .interfaces import URLRepositoryInterface


class URLRepository(URLRepositoryInterface):
    def __init__(self, session: Session):
        self.session = session

    def add(self, url: URLCreate) -> URLResponse:
        # Check if a URL with the same url exists
        statement = select(URL).where(URL.url == url.url)
        existing_url = self.session.exec(statement).first()

        if existing_url:
            return URLResponse.model_validate(existing_url)

        # If no existing URL found, create a new one
        db_url = URL.model_validate(url)
        self.session.add(db_url)
        self.session.flush()
        self.session.refresh(db_url)
        return URLResponse.model_validate(db_url)

    def get(self, url_id: int) -> URLResponse | None:
        url = self.session.get(URL, url_id)
        return URLResponse.model_validate(url) if url else None

    def get_by_url(self, url: str) -> URLResponse | None:
        statement = select(URL).where(URL.url == url)
        db_url = self.session.exec(statement).first()
        return URLResponse.model_validate(db_url) if db_url else None

    def get_by_ids(self, url_ids: list[int]) -> list[URLResponse]:
        if not url_ids:
            return []
        statement = select(URL).where(col(URL.id).in_(url_ids))
        urls = self.session.exec(statement).all()
        return [URLResponse.model_validate(url) for url in urls]

    def list_urls(self) -> list[URLResponse]:
        statement = select(URL)
        urls = self.session.exec(statement).all()
        return [URLResponse.model_validate(url) for url in urls]

    def delete(self, url_id: int) -> None:
        url = self.session.get(URL, url_id)
        if not url:
            return
        self.session.delete(url)
        self.session.flush()
