import os
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

def get_redis():
    client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    try:
        yield client
    finally:
        client.close()
