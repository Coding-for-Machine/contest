# events/api.py
import asyncio
import json
import logging
from collections.abc import AsyncIterable

from django_bolt.responses import EventSourceResponse, ServerSentEvent
from django_bolt import Router, Request, Depends

from baseuser.models import BaseUser
from baseuser.authenticate import get_current_user_option
from .redis_client import get_redis
from .limits import acquire_connection_slot, release_connection_slot
from .publisher import replay_missed_events
from .helpers import get_user_active_contest_ids

logger = logging.getLogger(__name__)
api = Router(tags=["Server Send Events"])


@api.get("/events", response_class=EventSourceResponse)
async def global_sse(
    request: Request,
    request_user: BaseUser | None = Depends(get_current_user_option),
) -> AsyncIterable[ServerSentEvent]:
    
    # 1. Autentifikatsiya tekshiruvi (Generator ichida yield bilan xavfsiz uzatiladi)
    if not request_user:
        yield ServerSentEvent(
            data={"detail": "Tizimga kirish talab qilinadi!"}, 
            event="auth_error"
        )
        return  # Generatorni o'sha joyda to'xtatamiz

    user_id = request_user.id

    # 2. Global ulanish slot limiti tekshiruvi
    if not await acquire_connection_slot(user_id):
        yield ServerSentEvent(
            data={"detail": "Juda ko'p faol ulanish. Maksimal 3 ta tab ochish mumkin."}, 
            event="limit_error"
        )
        return
    yield ServerSentEvent(
            data={"detail": f"foydalanovchi ulandi: {request.user.telegram_id}"}, 
            event="limit_error"
        )
    # 3. Agar tekshiruvlardan o'tsa, Redis Pub/Sub mantiqi shu yerda davom etadi
    redis_conn = get_redis()
    pubsub = redis_conn.pubsub()

    personal_channel = f"user_events_{user_id}"
    contest_channels = [
        f"contest_events_{cid}" for cid in await get_user_active_contest_ids(user_id)
    ]
    all_channels = [personal_channel, *contest_channels]
    last_event_id = request.headers.get("last-event-id")

    try:
        await pubsub.subscribe(*all_channels)
        logger.info("SSE connected: user=%s channels=%s", user_id, all_channels)

        # O'tkazib yuborilgan xabarlarni tarixda qayta tiklash (Reconnect / Replay)
        if last_event_id:
            for event in await replay_missed_events(user_id, last_event_id):
                yield ServerSentEvent(
                    data=event, 
                    event=event["type"], 
                    id=event["event_id"]
                )

        # Ulanish muvaffaqiyatli amalga oshganligi signali
        yield ServerSentEvent(data={"contests": contest_channels}, event="connected")

        # Redis Pub/Sub oqimini cheksiz tinglaymiz va yield qilamiz
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                raw = (
                    message["data"].decode("utf-8")
                    if isinstance(message["data"], bytes)
                    else message["data"]
                )
                data = json.loads(raw)
            except (json.JSONDecodeError, TypeError, AttributeError):
                logger.warning("Invalid SSE payload on %s", message["channel"])
                continue

            channel = message["channel"]
            event_type = data.get("type") or (
                "notification" if channel == personal_channel else "leaderboard_update"
            )

            # To'g'ridan-to'g'ri ServerSentEvent obyektini yield qilamiz
            yield ServerSentEvent(
                data=data, 
                event=event_type, 
                id=str(data.get("event_id", ""))
            )

    except asyncio.CancelledError:
        logger.info("SSE disconnected by client: user=%s", user_id)
        raise

    finally:
        # Hujjat bo'yicha klient uzilganda resurslarni xavfsiz tozalash (Cleanup)
        try:
            await pubsub.unsubscribe(*all_channels)
            await pubsub.close()  # Slotlar qulflanmasligi uchun to'g'ri asinxron close()
        except Exception as e:
            logger.error("SSE cleanup error for user %s: %s", user_id, e)
        
        # Har qanday holatda foydalanuvchi limit slotini aniq ozod qilamiz
        await release_connection_slot(user_id)
