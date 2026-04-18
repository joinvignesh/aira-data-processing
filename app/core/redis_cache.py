# app/core/redis_cache.py

from __future__ import annotations

import hashlib
import json
from redis import Redis


class RecommendationCache:
    def __init__(self, redis_client: Redis, ttl_seconds: int = 120):
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds

    def build_key(
        self,
        tenant_id: str,
        customer_id: str,
        surface: str,
        limit: int,
        exclude_product_ids: list[str],
    ) -> str:
        exclude_hash = hashlib.md5(
            json.dumps(sorted(exclude_product_ids)).encode("utf-8")
        ).hexdigest()

        return f"tenant:{tenant_id}:recommend:{customer_id}:{surface}:{limit}:{exclude_hash}"

    def get(self, key: str):
        value = self.redis.get(key)
        if not value:
            return None
        return json.loads(value)

    def set(self, key: str, value: dict):
        self.redis.setex(key, self.ttl_seconds, json.dumps(value))