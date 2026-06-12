# status/api.py  — to'liq yechim
# ──────────────────────────────────────────────────────────────────────────────
# Endpoints:
#   GET /status              → UserStats (xp, level, streak, easy/med/hard count)
#   GET /status/calendar     → oylik yoki oraliq activity (calendar heatmap uchun)
#   GET /status/history      → so'nggi N kunlik daily activity list
# ──────────────────────────────────────────────────────────────────────────────

from datetime import date, timedelta
from typing import Optional, List

from django.db.models import Sum, Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router, Schema
from ninja.errors import HttpError

from baseuser.authenticate import JWTAuth
from .models import UserStats, UserActivityDaily

api = Router(tags=["Status"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class UserStatsOut(Schema):
    xp: int
    level: int
    current_streak: int
    easy_count: int
    medium_count: int
    hard_count: int
    test_count: int
    total_solved: int
    last_activity: Optional[date] = None


class DailyActivityOut(Schema):
    date: date
    xp_earned: int
    problems_count: int
    total_duration: int          # sekundlarda


class CalendarOut(Schema):
    start_date: date
    end_date: date
    days: List[DailyActivityOut]


# ─── Endpoints ────────────────────────────────────────────────────────────────

@api.get("/status", response=UserStatsOut, auth=JWTAuth())
def get_user_stats(request):
    """
    Foydalanuvchining umumiy statistikasi.
    UserStats — OneToOne, shuning uchun get_or_create ishlatamiz.
    """
    stats, _ = UserStats.objects.get_or_create(
        user__telegram_id=request.auth.telegram_id,
        defaults={"user": request.auth},   # auth obyekti — BaseUser instance
    )
    return UserStatsOut(
        xp=stats.xp,
        level=stats.level,
        current_streak=stats.current_streak,
        easy_count=stats.easy_count,
        medium_count=stats.medium_count,
        hard_count=stats.hard_count,
        test_count=stats.test_count,
        total_solved=stats.total_solved,
        last_activity=stats.last_activity,
    )


@api.get("/status/calendar", response=CalendarOut, auth=JWTAuth())
def get_calendar(
    request,
    start: Optional[date] = None,   # ?start=2025-04-01
    end: Optional[date] = None,     # ?end=2025-04-30
):
    """
    Calendar heatmap uchun: berilgan oraliqda har kunlik activity.

    - start/end berilmasa → joriy oyning 1-sanasidan bugunga qadar.
    - Faoliyat bo'lmagan kunlar javobga KIRMAYDI (frontend 0 deb ko'rsatadi).
    - start → end oralig'i 366 kundan oshmasligi kerak (abuse oldini olish).
    """
    today = timezone.localdate()
    start = start or today.replace(day=1)
    end = end or today

    if (end - start).days > 366:
        raise HttpError(400, "Date range cannot exceed 366 days.")
    if start > end:
        raise HttpError(400, "start must be before end.")

    qs = (
        UserActivityDaily.objects
        .filter(
            user__telegram_id=request.auth.telegram_id,
            date__range=(start, end),
        )
        .order_by("date")
        .values("date", "xp_earned", "problems_count", "total_duration")
    )

    days = [DailyActivityOut(**row) for row in qs]
    return CalendarOut(start_date=start, end_date=end, days=days)


@api.get("/status/history", response=List[DailyActivityOut], auth=JWTAuth())
def get_activity_history(request, days: int = 30):
    """
    So'nggi N kunlik activity ro'yxati (default: 30 kun).
    Maksimal 365 kun.
    """
    if days < 1 or days > 365:
        raise HttpError(400, "days must be between 1 and 365.")

    since = timezone.localdate() - timedelta(days=days - 1)

    qs = (
        UserActivityDaily.objects
        .filter(
            user__telegram_id=request.auth.telegram_id,
            date__gte=since,
        )
        .order_by("-date")
        .values("date", "xp_earned", "problems_count", "total_duration")
    )

    return [DailyActivityOut(**row) for row in qs]