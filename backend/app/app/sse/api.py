import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterable

from django_bolt import Router, Depends, Request
from django_bolt.responses import ServerSentEvent, EventSourceResponse

from baseuser.authenticate import get_current_user_from_url
from baseuser.models import BaseUser
from contests.models import ContestRegistration
from .events import Channel
from .redis_client import get_async_redis

logger = logging.getLogger(__name__)
sse_api = Router(tags=["SSE"])

MAX_STREAM_SECONDS = 60 * 20


async def _active_contest_channels(user_id: int) -> list[str]:
    try:
        contest_ids = [
            cid async for cid in ContestRegistration.objects.filter(
                user_id=user_id,
                status=ContestRegistration.Status.IN_PROGRESS,
                contest__status="ongoing",
            ).values_list("contest_id", flat=True)
        ]
        return [Channel.CONTEST_LEADERBOARD.format(contest_id=cid) for cid in contest_ids]
    except Exception:
        logger.exception("Contest kanallarini olishda xato: user_id=%s", user_id)
        return []


class EventPublisher:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self._redis = get_async_redis()
        self._pubsub = self._redis.pubsub()

    async def stream(self) -> AsyncIterable[ServerSentEvent]:
        logger.info("SSE stream START user_id=%s", self.user_id)
        
        channels = [
            Channel.USER.format(user_id=self.user_id),
            Channel.LEADERBOARD.value,
        ]
        channels += await _active_contest_channels(self.user_id)

        logger.info("SSE channels: %s", channels)
        await self._pubsub.subscribe(*channels)
        logger.info("SSE subscribed OK")

        start_time = asyncio.get_event_loop().time()
        last_heartbeat = start_time

        try:
            # Django Bolt 0.8.3 da comment parametri mavjud
            yield ServerSentEvent(comment="connected")
            logger.info("SSE sent connected")

            while True:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= MAX_STREAM_SECONDS:
                    yield ServerSentEvent(
                        event="timeout",
                        data={"reason": "stream_timeout"},
                    )
                    return

                try:
                    message = await self._pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=5.0,
                    )
                except Exception:
                    logger.exception("Redis get_message xatosi")
                    await asyncio.sleep(1)
                    continue

                if message is None:
                    now = asyncio.get_event_loop().time()
                    if now - last_heartbeat >= 15:
                        yield ServerSentEvent(comment="heartbeat")
                        last_heartbeat = now
                    continue

                if message.get("type") != "message":
                    continue

                try:
                    raw_data = message["data"]
                    if isinstance(raw_data, bytes):
                        raw_data = raw_data.decode("utf-8")

                    payload = json.loads(raw_data)
                    event_name = str(payload.get("event", "message"))
                    event_id = str(payload.get("id", ""))
                    
                    # Django Bolt avtomatik JSON serialize qiladi
                    event_data = payload.get("data", {})

                    logger.info(
                        "SSE yield: event=%s id=%s",
                        event_name,
                        event_id,
                    )

                    yield ServerSentEvent(
                        event=event_name,
                        id=event_id,
                        data=event_data,
                    )

                except Exception:
                    logger.exception("SSE event parse/yield xatosi")
                    continue

        except asyncio.CancelledError:
            logger.info("SSE stream cancelled user_id=%s", self.user_id)
            raise
        finally:
            logger.info("SSE stream FINALLY user_id=%s", self.user_id)
            with contextlib.suppress(Exception):
                await self._pubsub.unsubscribe()
                await self._pubsub.aclose()


@sse_api.get("/stream")
async def global_stream(
    request: Request,
    request_user: BaseUser = Depends(get_current_user_from_url),
):
    logger.info("SSE REQUEST from user_id=%s", request_user.id)
    publisher = EventPublisher(user_id=request_user.id)
    return EventSourceResponse(publisher.stream())