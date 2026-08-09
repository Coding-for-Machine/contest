"""
Umumiy, sync-safe event moduli.

Nima uchun alohida fayl: `tasks.py` (Celery worker) SYNC context'da ishlaydi,
`sse/publisher.py` (django-bolt) esa ASYNC. Ikkalasi ham bir xil EventType/
Channel/SubmissionEvent'dan foydalanishi kerak, aks holda event nomlari ikki
joyda qo'lda yozilib, ertami-kechmi bir-biridan chetlashib ketadi. Shu modulda
hech qanday async/Redis-ga bog'liq kod yo'q — faqat toza struct'lar,
shu sababli uni ham Celery, ham django-bolt tomondan xavfsiz import qilish
mumkin.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

import msgspec


# ============================================================
# EVENT TURLARI VA KANALLAR
# ============================================================

class EventType(str, Enum):
    QUEUED = "queued"                            # submission navbatga qo'yildi
    TESTCASE = "testcase"                        # bitta yashirin test natijasi
    RESULT = "result"                            # testcase'siz natija
    FINAL = "final"                              # submission yakuniy natijasi
    ERROR = "error"                              # tizim xatosi
    NOTIFICATION = "notification"                # yangi bildirishnoma
    LEADERBOARD = "leaderboard"                  # global reyting
    CONTEST_LEADERBOARD = "contest_leaderboard"  # contest reytingi


class Channel(str, Enum):
    """Redis pub/sub kanal shablonlari.

    `.format(**kwargs)` — shablondagi `{}` joylarini to'ldirib, tayyor
    kanal nomini qaytaradi. Statik kanallar uchun `.value` ishlatiladi.
    """

    USER = "user:{user_id}"
    CONTEST_LEADERBOARD = "contest_leaderboard:{contest_id}"
    LEADERBOARD = "leaderboard"

    def format(self, **kwargs: Any) -> str:
        return self.value.format(**kwargs)


# ============================================================
# WIRE-FORMAT STRUKTURALAR
# ============================================================

class Event(msgspec.Struct):
    """Redisga yoziladigan/undan o'qiladigan wire-format."""

    event: str
    id: str
    data: dict[str, Any]

    def to_json(self) -> str:
        return msgspec.json.encode(self).decode("utf-8")


class LeaderboardEntry(msgspec.Struct):
    """Reyting qatoridagi yozuv. Agar foydalanuvchi o'chirilgan yoki
    XP hisoblanmagan bo'lsa, ba'zi maydonlar None bo'lishi mumkin."""

    rank: int
    user_id: int
    username: str | None = None
    xp: int | None = None


# ============================================================
# EVENT FABRIKALARI
# ============================================================

class SubmissionEvent:
    """Submission hayot sikli eventlari."""

    # -------------------- Shaxsiy submission oqimi --------------------

    @classmethod
    def queued(cls, task_id: str) -> Event:
        return Event(
            event=EventType.QUEUED.value,
            id=str(task_id),
            data={"task_id": task_id},
        )

    @classmethod
    def testcase(
        cls,
        task_id: str,
        *,
        index: int,
        lang: str,
        ver: str,
        input: str,
        expected_output: str,
        output: str,
        status: str,
        memory: int | None = None,
        cpu_time: float | None = None,
        wall_time: float | None = None,
        message: str = "",
    ) -> Event:
        return Event(
            event=EventType.TESTCASE.value,
            id=str(task_id),
            data={
                "task_id": task_id,
                "index": index,
                "lang": lang,
                "ver": ver,
                "input": input,
                "expected_output": expected_output,
                "output": output,
                "status": status,
                "memory": memory,
                "cpu_time": cpu_time,
                "wall_time": wall_time,
                "message": message,
            },
        )

    @classmethod
    def result(
        cls,
        task_id: str,
        *,
        lang: str,
        ver: str,
        output: str,
        memory: int | None = None,
        cpu_time: float | None = None,
        wall_time: float | None = None,
        message: str = "",
    ) -> Event:
        return Event(
            event=EventType.RESULT.value,
            id=str(task_id),
            data={
                "task_id": task_id,
                "lang": lang,
                "ver": ver,
                "output": output,
                "memory": memory,
                "cpu_time": cpu_time,
                "wall_time": wall_time,
                "message": message,
            },
        )

    @classmethod
    def final(cls, submission, task_id: str | None = None) -> Event:
        """Yakuniy natija. `task_id` None bo'lishi mumkin (masalan,
        admin paneldan qo'shilgan submissionlar uchun)."""
        return Event(
            event=EventType.FINAL.value,
            id=str(task_id) if task_id is not None else "unknown",
            data={
                "task_id": task_id,
                "submission_id": submission.id,
                "status": getattr(submission, "status", None),
                "verdict": getattr(submission, "verdict", None),
                "passed_count": getattr(submission, "passed_test_count", None),
                "total_count": getattr(submission, "total_test_count", None),
                "time": getattr(submission, "execution_time", None),
                "memory": getattr(submission, "execution_memory", None),
                "lang": (
                    submission.language.name
                    if getattr(submission, "language", None)
                    else ""
                ),
                "created_at": (
                    submission.submitted_at.strftime("%Y-%m-%d %H:%M")
                    if getattr(submission, "submitted_at", None)
                    else ""
                ),
            },
        )

    @classmethod
    def error(cls, ref_id: str, message: str) -> Event:
        return Event(
            event=EventType.ERROR.value,
            id=str(ref_id),
            data={"message": message},
        )

    # -------------------- Reyting oqimlari --------------------

    @classmethod
    def leaderboard(cls, entries: list[LeaderboardEntry]) -> Event:
        return Event(
            event=EventType.LEADERBOARD.value,
            id="global",
            data={"entries": [msgspec.structs.asdict(e) for e in entries]},
        )

    @classmethod
    def contest_leaderboard(
        cls,
        contest_id: int | str,
        entries: list[LeaderboardEntry],
    ) -> Event:
        return Event(
            event=EventType.CONTEST_LEADERBOARD.value,
            id=str(contest_id),
            data={
                "contest_id": contest_id,
                "entries": [msgspec.structs.asdict(e) for e in entries],
            },
        )


class NotificationEvent:
    """Bildirishnoma eventlari."""

    @classmethod
    def new(
        cls,
        id: int,
        type: str,
        title: str,
        message: str,
        link: str,
        created_at: str,
    ) -> Event:
        return Event(
            event=EventType.NOTIFICATION.value,
            id=str(id),
            data={
                "id": id,
                "type": type,
                "title": title,
                "message": message,
                "link": link,
                "created_at": created_at,
            },
        )