from __future__ import annotations

from typing import Any, Annotated

import msgspec
from django_bolt import Router, Request, Depends
from django_bolt.param_functions import Query          # <-- to'g'ri import yo'li
from django_bolt.exceptions import HTTPException

from baseuser.authenticate import get_current_user_option
from baseuser.models import BaseUser
from .models import Notification

# Router konstruktorida faqat prefix/middleware/auth/guards bo'ladi,
# "tags" esa har bir route'da alohida beriladi (pastda ko'rsatilgan)
api_notification = Router()


class NotificationOut(msgspec.Struct):
    id: int
    type: str
    title: str
    message: str
    link: str | None
    is_read: bool
    created_at: str
    meta: dict[str, Any]


class NotificationListResponse(msgspec.Struct):
    count: int
    unread_count: int
    data: list[NotificationOut]


class MarkReadIn(msgspec.Struct):
    ids: list[int] | None = None


@api_notification.get("/", tags=["notifications"])
async def list_notifications(
    request: Request,
    limit: Annotated[int, Query()] = 20,
    offset: Annotated[int, Query()] = 0,
    request_user: BaseUser | None = Depends(get_current_user_option),
) -> NotificationListResponse:
    if not request_user:
        raise HTTPException(status_code=401, detail="Tizimga kiring")

    queryset = Notification.objects.filter(user=request_user).order_by("-created_at")

    total = await queryset.acount()
    unread = await queryset.filter(is_read=False).acount()

    notifications: list[NotificationOut] = []

    async for n in queryset[offset : offset + limit]:
        notifications.append(
            NotificationOut(
                id=n.id,
                type=n.type or "",
                title=n.title or "",
                message=n.message or "",
                link=n.link or None,
                is_read=n.is_read,
                created_at=(
                    n.created_at.strftime("%Y-%m-%d %H:%M")
                    if n.created_at
                    else ""
                ),
                meta=n.meta if isinstance(n.meta, dict) else {},
            )
        )

    return NotificationListResponse(
        count=total,
        unread_count=unread,
        data=notifications,
    )


@api_notification.post("/read/", tags=["notifications"])
async def mark_read(
    request: Request,
    payload: MarkReadIn,
    request_user: BaseUser | None = Depends(get_current_user_option),
) -> dict[str, Any]:
    if not request_user:
        raise HTTPException(status_code=401, detail="Tizimga kiring")

    if payload.ids:
        await Notification.objects.filter(
            user=request_user, id__in=payload.ids
        ).aupdate(is_read=True)
    else:
        await Notification.objects.filter(
            user=request_user, is_read=False
        ).aupdate(is_read=True)

    unread = await Notification.objects.filter(
        user=request_user, is_read=False
    ).acount()

    return {"ok": True, "unread_count": unread}


@api_notification.delete("/{id}/", tags=["notifications"])
async def delete_notification(
    request: Request,
    id: int,
    request_user: BaseUser | None = Depends(get_current_user_option),
) -> dict[str, Any]:
    if not request_user:
        raise HTTPException(status_code=401, detail="Tizimga kiring")

    deleted, _ = await Notification.objects.filter(
        user=request_user, id=id
    ).adelete()

    if not deleted:
        raise HTTPException(status_code=404, detail="Bildirishnoma topilmadi")

    unread = await Notification.objects.filter(
        user=request_user, is_read=False
    ).acount()

    return {"ok": True, "unread_count": unread}


@api_notification.delete("/", tags=["notifications"])
async def clear_all_notifications(
    request: Request,
    request_user: BaseUser | None = Depends(get_current_user_option),
) -> dict[str, Any]:
    if not request_user:
        raise HTTPException(status_code=401, detail="Tizimga kiring")

    await Notification.objects.filter(user=request_user).adelete()

    return {"ok": True, "unread_count": 0}