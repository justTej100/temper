from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings


def _sqlalchemy_url(url: str) -> str:
    # SQLAlchemy 2.x removed the legacy "postgres://" dialect alias
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


settings = get_settings()
engine = create_engine(_sqlalchemy_url(settings.database_url), echo=False, pool_pre_ping=True)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
