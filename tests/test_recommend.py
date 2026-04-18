# tests/test_recommend.py

import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy import text

from app.main import app
from app.db.dependencies import get_db


TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/aira",
)


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(TEST_DATABASE_URL)
    return engine


@pytest.fixture(scope="session", autouse=True)
def create_test_schema(engine):
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture()
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def seed_recommendation_data(session: Session):
    tenant_id = str(uuid4())
    customer_id = "cust_1"

    product_1 = str(uuid4())
    product_2 = str(uuid4())
    product_3 = str(uuid4())

    now = datetime.now(timezone.utc)

    session.exec(
        text("""
            INSERT INTO tenant (id, name, slug, plan_tier, created_at)
            VALUES (:id, :name, :slug, :plan_tier, :created_at)
        """),
        {
            "id": tenant_id,
            "name": "Test Tenant",
            "slug": f"test-tenant-{tenant_id[:8]}",
            "plan_tier": "pro",
            "created_at": now,
        },
    )

    session.exec(
        text("""
            INSERT INTO product (
                id, tenant_id, external_id, title, description, price, currency,
                category, tags, metadata, active, created_at
            )
            VALUES
                (:p1, :tenant_id, 'ext-1', 'Phone', 'Phone desc', 499.0, 'USD', 'electronics', '[]', '{}'::json, true, :created_at),
                (:p2, :tenant_id, 'ext-2', 'Earbuds', 'Earbuds desc', 99.0, 'USD', 'electronics', '[]', '{}'::json, true, :created_at),
                (:p3, :tenant_id, 'ext-3', 'Case', 'Case desc', 29.0, 'USD', 'accessories', '[]', '{}'::json, true, :created_at)
        """),
        {
            "p1": product_1,
            "p2": product_2,
            "p3": product_3,
            "tenant_id": tenant_id,
            "created_at": now,
        },
    )

    session.exec(
        text("""
            INSERT INTO customer_features (
                id,
                tenant_id,
                customer_id,
                total_views,
                total_cart_adds,
                total_purchases,
                distinct_products_viewed,
                distinct_categories_viewed,
                days_since_first_seen,
                days_since_last_activity,
                category_affinity,
                avg_days_between_purchases,
                total_revenue,
                avg_order_value,
                avg_session_duration_seconds,
                avg_products_viewed_per_session,
                updated_at
            )
            VALUES (
                :id,
                :tenant_id,
                :customer_id,
                10,
                2,
                1,
                3,
                2,
                30,
                1,
                '{"electronics": 9, "accessories": 4}'::jsonb,
                12.5,
                499.00,
                499.00,
                300.0,
                2.5,
                :updated_at
            )
        """),
        {
            "id": str(uuid4()),
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "updated_at": now,
        },
    )

    session.exec(
        text("""
            INSERT INTO product_cooccurrence (
                id,
                tenant_id,
                product_a_id,
                product_b_id,
                co_count,
                confidence,
                last_updated
            )
            VALUES
                (:id1, :tenant_id, :p1, :p2, 5, 0.80, :updated_at),
                (:id2, :tenant_id, :p1, :p3, 3, 0.45, :updated_at)
        """),
        {
            "id1": str(uuid4()),
            "id2": str(uuid4()),
            "tenant_id": tenant_id,
            "p1": product_1,
            "p2": product_2,
            "p3": product_3,
            "updated_at": now,
        },
    )

    session.exec(
        text("""
            INSERT INTO interactionevent (
                id,
                tenant_id,
                customer_id,
                event_type,
                product_id,
                properties,
                timestamp
            )
            VALUES
                (:e1, :tenant_id, :customer_id, 'product_view', :p1, '{}'::json, :ts1),
                (:e2, :tenant_id, :customer_id, 'add_to_cart', :p1, '{}'::json, :ts2)
        """),
        {
            "e1": str(uuid4()),
            "e2": str(uuid4()),
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "p1": product_1,
            "ts1": now,
            "ts2": now,
        },
    )

    session.commit()

    return {
        "tenant_id": tenant_id,
        "customer_id": customer_id,
        "product_1": product_1,
        "product_2": product_2,
        "product_3": product_3,
    }


def test_recommend_happy_path(client: TestClient, db_session: Session):
    seeded = seed_recommendation_data(db_session)

    response = client.post(
        "/api/v1/recommend",
        headers={"x-tenant-id": seeded["tenant_id"]},
        json={
            "customer_id": seeded["customer_id"],
            "surface": "home",
            "limit": 5,
            "exclude_product_ids": [],
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "decision_id" in data
    assert "model_version" in data
    assert "latency_ms" in data
    assert len(data["items"]) <= 5
    assert isinstance(data["items"], list)

    if data["items"]:
        first = data["items"][0]
        assert "product_id" in first
        assert "score" in first
        assert "reason" in first