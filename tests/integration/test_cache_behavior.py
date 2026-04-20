import hashlib
import json
from app.main import app # Import your FastAPI app
from app.core.redis_client import get_redis # Import the dependency

from tests.integration.seeds import seed_warm_recommendation_scenario


def build_expected_cache_key(tenant_id: str, customer_id: str, surface: str, limit: int, exclude_product_ids: list[str]) -> str:
    # Match the app: sort the list and use NO whitespace in separators
    clean_excludes = sorted(exclude_product_ids) if exclude_product_ids else []
    exclude_json = json.dumps(clean_excludes, separators=(',', ':'))
    exclude_hash = hashlib.md5(exclude_json.encode("utf-8")).hexdigest()
    
    return f"tenant:{tenant_id}:recommend:{customer_id}:{surface}:{limit}:{exclude_hash}"


def test_cache_is_tenant_scoped(client, db_session, clean_redis):
    # --- STEP 1: OVERRIDE REDIS ---
    # Force the app to use the 'clean_redis' (DB 15) fixture
    app.dependency_overrides[get_redis] = lambda: clean_redis

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

    # --- STEP 3: VERIFY ---
    key = build_expected_cache_key(
        tenant_id=seeded["tenant_id"],
        customer_id=payload["customer_id"],
        surface=payload["surface"],
        limit=payload["limit"],
        exclude_product_ids=payload["exclude_product_ids"],
    )

    cached = clean_redis.get(key)
    
    # If this fails, let's see what keys ARE in Redis
    if cached is None:
        print(f"\nDebug - Looked for key: {key}")
        print(f"Debug - Keys actually in Redis: {clean_redis.keys('*')}")
    
    assert cached is not None

    # --- STEP 4: CLEANUP ---
    app.dependency_overrides.clear()