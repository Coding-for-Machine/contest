from .redis_client import get_redis

MAX_CONNECTIONS_PER_USER = 2
CONNECTION_TTL = 3600  # zombie counterlardan himoya

async def acquire_connection_slot(user_id: int) -> bool:
    r = get_redis()
    key = f"sse_conn_count_{user_id}"
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, CONNECTION_TTL)
    if count > MAX_CONNECTIONS_PER_USER:
        await r.decr(key)
        return False
    return True

async def release_connection_slot(user_id: int):
    r = get_redis()
    key = f"sse_conn_count_{user_id}"
    remaining = await r.decr(key)
    if remaining <= 0:
        await r.delete(key)