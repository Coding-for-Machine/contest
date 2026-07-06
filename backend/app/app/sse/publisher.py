import json
import time
import uuid
from .redis_client import get_redis

async def publish_event(channel: str, event_type: str, payload: dict):
    r = get_redis()
    event_id = f"{int(time.time() * 1000)}-{uuid.uuid4().hex[:6]}"
    envelope = {"type": event_type, "event_id": event_id, **payload}

    await r.publish(channel, json.dumps(envelope))

    history_key = f"history_{channel}"
    await r.zadd(history_key, {json.dumps(envelope): time.time()})
    await r.zremrangebyrank(history_key, 0, -101)  # faqat oxirgi 100 ta
    await r.expire(history_key, 3600)

async def replay_missed_events(user_id: int, last_event_id: str) -> list[dict]:
    r = get_redis()
    history_key = f"history_user_events_{user_id}"
    raw_items = await r.zrange(history_key, 0, -1)

    missed, found = [], False
    for raw in raw_items:
        event = json.loads(raw)
        if found:
            missed.append(event)
        if event.get("event_id") == last_event_id:
            found = True
    return missed