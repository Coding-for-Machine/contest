# ── GLOBAL CONNECTION REGISTRY ────────────────────────────────────────────────
# user_id → Queue (har bir ulanish uchun alohida)
import asyncio
from collections import defaultdict

_user_queues: dict[int, set[asyncio.Queue]] = defaultdict(set)


def push_to_user(user_id: int, event: str, data: dict):
    for q in _user_queues.get(user_id, set()):
        q.put_nowait({"event": event, "data": data})


def push_to_all(event: str, data: dict):
    """Barcha ulangan foydalanuvchilarga broadcast."""
    for queues in _user_queues.values():
        for q in queues:
            q.put_nowait({"event": event, "data": data})