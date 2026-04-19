from sqlalchemy import text

from tests.integration.seeds import (
    seed_cold_start_scenario,
    seed_tenant_isolation_scenario,
    seed_warm_recommendation_scenario,
)


def test_recommend_returns_personalized_results(client, db_session):
    seeded = seed_warm_recommendation_scenario(db_session)

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
    assert len(data["items"]) > 0

    returned_ids = {item["product_id"] for item in data["items"]}
    assert seeded["products"]["earbuds"] in returned_ids or seeded["products"]["charger"] in returned_ids


def test_recommend_falls_back_to_popularity_for_cold_start(client, db_session):
    seeded = seed_cold_start_scenario(db_session)

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

    assert len(data["items"]) > 0
    returned_ids = {item["product_id"] for item in data["items"]}
    assert seeded["products"]["popular_1"] in returned_ids or seeded["products"]["popular_2"] in returned_ids


def test_recommend_respects_exclude_product_ids(client, db_session):
    seeded = seed_warm_recommendation_scenario(db_session)

    excluded_id = seeded["products"]["earbuds"]

    response = client.post(
        "/api/v1/recommend",
        headers={"x-tenant-id": seeded["tenant_id"]},
        json={
            "customer_id": seeded["customer_id"],
            "surface": "home",
            "limit": 5,
            "exclude_product_ids": [excluded_id],
        },
    )

    assert response.status_code == 200
    data = response.json()

    returned_ids = {item["product_id"] for item in data["items"]}
    assert excluded_id not in returned_ids


def test_recommend_logs_decision(client, db_session):
    seeded = seed_warm_recommendation_scenario(db_session)

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

    row = db_session.exec(
        text("""
            SELECT decision_id, customer_id, tenant_id
            FROM recommendation_decisions
            WHERE decision_id = :decision_id
            """),
            params={"decision_id": data["decision_id"]},
    ).mappings().first()

    assert row is not None
    assert row["customer_id"] == seeded["customer_id"]
    assert str(row["tenant_id"]) == seeded["tenant_id"]


def test_tenant_isolation_end_to_end(client, db_session):
    seeded = seed_tenant_isolation_scenario(db_session)

    tenant_a = seeded["tenant_a"]
    tenant_b = seeded["tenant_b"]

    response = client.post(
        "/api/v1/recommend",
        headers={"x-tenant-id": tenant_a["tenant_id"]},
        json={
            "customer_id": tenant_a["customer_id"],
            "surface": "home",
            "limit": 10,
            "exclude_product_ids": [],
        },
    )

    assert response.status_code == 200
    data = response.json()

    returned_ids = {item["product_id"] for item in data["items"]}
    assert tenant_b["product_id"] not in returned_ids