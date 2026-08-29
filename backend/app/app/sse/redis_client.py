import redis
import redis.asyncio as aredis
from django.conf import settings

REDIS_URL = getattr(settings, 'CELERY_BROKER_URL', settings.REDIS_URL)

# Celery (sync) uchun
sync_redis = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
)

# Django Bolt (async) uchun pool
_async_pool = aredis.ConnectionPool.from_url(
    REDIS_URL,
    decode_responses=True,
)

def get_async_redis() -> aredis.Redis:
    return aredis.Redis(connection_pool=_async_pool)