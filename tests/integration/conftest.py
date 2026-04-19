import os
from pathlib import Path

import pytest
import redis
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlmodel import Session

from app.main import app
from app.db.dependencies import get_db
from app.core.redis_client import get_redis


TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/aira",
)

TEST_REDIS_URL = os.getenv(
    "TEST_REDIS_URL",
    "redis://localhost:6379/15",
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def alembic_config() -> Config:
    config = Config(str(_project_root() / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    return config


@pytest.fixture(scope="session")
def engine(alembic_config: Config):
    command.upgrade(alembic_config, "head")
    engine = create_engine(TEST_DATABASE_URL, future=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def redis_client():
    client = redis.Redis.from_url(TEST_REDIS_URL, decode_responses=True)
    client.ping()
    yield client
    client.close()


def _truncate_all_tables(session: Session):
    session.exec(text("""
        TRUNCATE TABLE
            recommendation_decisions,
            product_cooccurrence,
            customer_features,
            pipeline_checkpoints,
            interactionevent,
            product,
            "user",
            tenant
        RESTART IDENTITY CASCADE
    """))
    session.commit()


@pytest.fixture()
def db_session(engine):
    with Session(engine) as session:
        _truncate_all_tables(session)
        yield session
        session.rollback()


@pytest.fixture()
def clean_redis(redis_client):
    redis_client.flushdb()
    yield redis_client
    redis_client.flushdb()


@pytest.fixture()
def client(db_session: Session, clean_redis):
    def override_get_db():
        yield db_session

    def override_get_redis():
        return clean_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()