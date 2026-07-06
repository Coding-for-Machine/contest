import redis.asyncio as redis
from django.conf import settings

redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=500,
)

def get_redis() -> redis.Redis:
    return redis.Redis(connection_pool=redis_pool)