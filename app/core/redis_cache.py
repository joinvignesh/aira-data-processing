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
        exclude_product_ids: list[str] | None,
    ) -> str:
        # 1. Standardize the list (Handle None and Sort)
        clean_excludes = sorted(exclude_product_ids) if exclude_product_ids else []
        
        # 2. Deterministic JSON (No extra spaces)
        # We use separators=(',', ':') to ensure NO whitespace like "[]" vs "[ ]"
        exclude_json = json.dumps(clean_excludes, separators=(',', ':'))
        exclude_hash = hashlib.md5(exclude_json.encode("utf-8")).hexdigest()

        return f"tenant:{tenant_id}:recommend:{customer_id}:{surface}:{limit}:{exclude_hash}"

    def get(self, key: str):
        # 1. Check L1 (Memory) - Instant
        if key in self._l1_cache:
            return self._l1_cache[key]
        
        value = self.redis.get(key)
        if not value:
            return None
            
        decoded = json.loads(value)
        # Update L1 so the next request is instant
        self._l1_cache[key] = decoded
        return decoded

    def set(self, key: str, value: dict):
        self._l1_cache[key] = value
        self.redis.setex(key, self.ttl_seconds, json.dumps(value))