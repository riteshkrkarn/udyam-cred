"""SQLAlchemy engine, session factory, declarative base and helpers."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.config import settings

# SQLite needs check_same_thread=False for use across threads (e.g. FastAPI).
_connect_args = (
    {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

Base = declarative_base()


def init_db(engine=None) -> None:
    """Create all tables on the given engine (defaults to the module engine).

    Importing app.models here registers the ORM classes on Base.metadata.
    """
    from app import models  # noqa: F401  (registers tables on Base.metadata)

    target = engine if engine is not None else globals()["engine"]
    Base.metadata.create_all(bind=target)


def get_db():
    """FastAPI dependency that yields a database session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
