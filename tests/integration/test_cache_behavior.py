import hashlib
import json

from tests.integration.seeds import seed_warm_recommendation_scenario


def build_expected_cache_key(tenant_id: str, customer_id: str, surface: str, limit: int, exclude_product_ids: list[str]) -> str:
    exclude_hash = hashlib.md5(
        json.dumps(sorted(exclude_product_ids)).encode("utf-8")
    ).hexdigest()
    return f"tenant:{tenant_id}:recommend:{customer_id}:{surface}:{limit}:{exclude_hash}"


def test_cache_is_tenant_scoped(client, db_session, clean_redis):
    seeded = seed_warm_recommendation_scenario(db_session)

    payload = {
        "customer_id": seeded["customer_id"],
        "surface": "home",
        "limit": 5,
        "exclude_product_ids": [],
    }

    response = client.post(
        "/api/v1/recommend",
        headers={"x-tenant-id": seeded["tenant_id"]},
        json=payload,
    )

    assert response.status_code == 200

    key = build_expected_cache_key(
        tenant_id=seeded["tenant_id"],
        customer_id=payload["customer_id"],
        surface=payload["surface"],
        limit=payload["limit"],
        exclude_product_ids=payload["exclude_product_ids"],
    )

    cached = clean_redis.get(key)
    assert cached is not None