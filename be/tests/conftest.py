"""Shared pytest fixtures for the UdyamCred backend tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the be/ directory is importable as the project root.
BE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BE_DIR))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base  # noqa: E402
from app import models  # noqa: E402,F401  (register tables on metadata)
from app.policy import load_policy  # noqa: E402
from synth.generator import SyntheticDataGenerator  # noqa: E402


@pytest.fixture(scope="session")
def policy():
    return load_policy()


@pytest.fixture(scope="session")
def generator(policy):
    return SyntheticDataGenerator(policy, seed=42)


@pytest.fixture
def shops(generator):
    """The deterministic 10-shop golden dataset (seed 42)."""
    return generator.generate(10, seed=42)


@pytest.fixture
def engine():
    """A fresh in-memory SQLite engine with all tables created.

    Shared by db_session and client so API writes are visible to direct DB
    queries in the same test (single StaticPool connection).
    """
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture
def db_session(engine):
    """A SQLAlchemy session bound to the in-memory engine fixture."""
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(engine):
    """A FastAPI TestClient wired to the same in-memory engine as db_session."""
    from fastapi.testclient import TestClient

    from app.database import get_db
    from main import app

    TestSession = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
