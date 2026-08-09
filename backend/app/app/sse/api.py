import asyncio
import contextlib
import logging
from collections.abc import AsyncIterable

import msgspec
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
    """User hozir qatnashayotgan (tugamagan) contestlar ro'yxati."""
    contest_ids = [
        cid async for cid in ContestRegistration.objects.filter(
            user_id=user_id,
            status=ContestRegistration.Status.IN_PROGRESS,
            contest__status="ongoing",
        ).values_list("contest_id", flat=True)
    ]
    return [Channel.CONTEST_LEADERBOARD.format(contest_id=cid) for cid in contest_ids]


class EventPublisher:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self._redis = get_async_redis()
        self._pubsub = self._redis.pubsub()

    async def stream(self) -> AsyncIterable[ServerSentEvent]:
        # Kanallarni aniq string ko'rinishida yig'amiz
        channels = [Channel.USER.format(user_id=self.user_id), str(Channel.LEADERBOARD.value)]
        channels += await _active_contest_channels(self.user_id)

        # Redis kanallariga obuna bo'lish
        await self._pubsub.subscribe(*channels)
        
        try:
            yield ServerSentEvent(comment="connected")

            loop = asyncio.get_event_loop()
            deadline = loop.time() + MAX_STREAM_SECONDS

            while True:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    yield ServerSentEvent(event="timeout", data={"reason": "stream_timeout"})
                    return

                # Xabarni olish (Non-blocking asinxron kutish)
                message = await self._pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=min(remaining, 5.0)
                )
                if message is None:
                    await asyncio.sleep(0.1)  # CPU yuklamasini kamaytirish uchun kichik pauza
                    continue

                try:
                    payload = msgspec.json.decode(message["data"])
                    yield ServerSentEvent(
                        event=str(payload["event"]),
                        id=str(payload["id"]),
                        data=payload["data"],
                    )
                except Exception as parse_err:
                    logger.error(f"SSE JSON parse xatosi: {parse_err}")
                    continue

        finally:
            with contextlib.suppress(Exception):
                await self._pubsub.unsubscribe(*channels)
                await self._pubsub.aclose()


@sse_api.get("/stream")
async def global_stream(request: Request, request_user: BaseUser = Depends(get_current_user_from_url)):
    """
    Parametrsiz yagona SSE oqimi.
    `EventSourceResponse` ga generator funksiyaning o'zi (yoki obyekti) uzatiladi.
    """
    publisher = EventPublisher(user_id=request_user.id)
    
    return EventSourceResponse(publisher.stream())
