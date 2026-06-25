import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("INTERNAL_API_TOKEN", "test-internal-token")
os.environ["DATABASE_URL"] = "sqlite://"

import app.db.session as session_mod
from app.models import Base

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
session_mod.engine = test_engine
session_mod.SessionLocal = sessionmaker(bind=test_engine, autoflush=False)

TestingSession = sessionmaker(bind=test_engine, autoflush=False)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield


@pytest.fixture
def db():
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
