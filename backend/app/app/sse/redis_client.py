import redis
import redis.asyncio as aredis
from django.conf import settings

REDIS_URL = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")

# Celery worker SYNC process ichida bir marta ochiladi
sync_redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# django-bolt ASGI process uchun pool (har so'rovda yangi Redis() ochish arzon,
# chunki pool connection'larni qayta ishlatadi)
_async_pool = aredis.ConnectionPool.from_url(REDIS_URL, decode_responses=True)

def get_async_redis() -> aredis.Redis:
    return aredis.Redis(connection_pool=_async_pool)