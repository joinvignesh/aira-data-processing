# app/core/redis_client.py
import os
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create a connection pool once when the module is loaded
pool = redis.ConnectionPool.from_url(REDIS_URL, decode_responses=True, max_connections=100)
redis_client = redis.Redis(connection_pool=pool)

def get_redis():
    # Simply yield the existing client; do NOT close it.
    yield redis_client