# app/core/redis_cache.py

from __future__ import annotations

import hashlib
import json
from redis import Redis


class RecommendationCache:
    def __init__(self, redis_client: Redis, ttl_seconds: int = 120):
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds
        # L1 Cache: A simple dictionary to store results in local RAM for 1 second
        # This prevents "micro-bursts" of the same request from hitting Redis
        self._l1_cache = {} 

    def build_key(
        self,
        tenant_id: str,
        customer_id: str,
        surface: str,
        limit: int,
        exclude_product_ids: list[str],
    ) -> str:
        # Optimization: Only hash if there are actual IDs to exclude
        if not exclude_product_ids:
            exclude_hash = "none"
        else:
            # Using a tuple for faster hashing in Python
            exclude_hash = hash(tuple(sorted(exclude_product_ids))) 

        return f"v1:{tenant_id}:{customer_id}:{surface}:{limit}:{exclude_hash}"

    def get(self, key: str):
        # 1. Check L1 (Memory) - Instant
        if key in self._l1_cache:
            return self._l1_cache[key]
        
        # 2. Check L2 (Redis)
        value = self.redis.get(key)
        if value:
            decoded = json.loads(value)
            self._l1_cache[key] = decoded # Save to L1
            return decoded
        return None

    def set(self, key: str, value: dict):
        self._l1_cache[key] = value
        self.redis.setex(key, self.ttl_seconds, json.dumps(value))