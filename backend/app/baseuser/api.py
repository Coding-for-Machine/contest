from datetime import timedelta
from django.utils import timezone

from django_bolt import JSON, status, Router
from django.core.cache import cache
from status.models import UserActivityDaily
from .models import BaseUser

api = Router(tags=["User api"])

@api.get("/{tg_id_or_username}")
async def get_user(request, tg_id_or_username: str): # : str yozilsa Swagger-da matn kiritish joyi ochiladi
    clean_value = tg_id_or_username.lstrip('@')
    user = None

    if clean_value.isdigit():
        user = await BaseUser.objects.filter(is_active=True, telegram_id=int(clean_value)).select_related('profile').afirst()

    if not user:
        user = await BaseUser.objects.filter(is_active=True, username__iexact=clean_value).select_related('profile').afirst()

    if not user:
        return JSON(
            {"detail": "Foydalanuvchi topilmadi"}, 
            status_code=status.HTTP_404_NOT_FOUND
        )

    profile_data = None
    try:
        if user.profile:
            profile_data = {
                "id": user.profile.id,
                "avatar": user.profile.avatar.url if user.profile.avatar else None,
                "bio": user.profile.bio,
                "website": user.profile.website
            }
    except Exception:
        profile_data = None

    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "phone": user.phone,
        "full_name": user.full_name,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "profile": profile_data
    }



@api.get("/heatmap/{telegram_id}")
async def get_user_heatmap(request, telegram_id: int, days: int = 365):
    days = min(days, 730)  # abuse'dan himoya — cheksiz range so'ralmasin

    cache_key = f"heatmap:{telegram_id}:{days}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    user_data = await BaseUser.objects.filter(
        telegram_id=telegram_id, is_active=True
    ).values("id").afirst()

    if not user_data:
        return JSON({"detail": "Foydalanuvchi topilmadi"}, status_code=status.HTTP_404_NOT_FOUND)

    internal_user_id = user_data["id"]
    today = timezone.now().date()
    start_date = today - timedelta(days=days)

    # Faqat kerakli 2 ta ustun, values_list — dict yaratish overhead'isiz
    rows = UserActivityDaily.objects.filter(
        user_id=internal_user_id,
        date__gte=start_date,
        date__lte=today,
    ).order_by("date").values_list("date", "tasks_count")

    heatmap_sparse = {}
    current_streak = 0
    max_streak = 0
    total_active_days = 0
    prev_date = None

    async for d, tasks in rows:
        if tasks > 0:
            heatmap_sparse[d.isoformat()] = tasks
            total_active_days += 1

            # streak faqat ketma-ket kunlarda hisoblanadi (bo'sh kunlar bo'lsa uziladi)
            if prev_date is not None and (d - prev_date).days == 1:
                current_streak += 1
            else:
                current_streak = 1
            max_streak = max(max_streak, current_streak)
            prev_date = d
        else:
            current_streak = 0
            prev_date = d

    # Agar oxirgi faol kun bugundan uzoq bo'lsa, joriy streak = 0
    if prev_date is None or (today - prev_date).days > 1:
        current_streak = 0

    result = {
        "telegram_id": telegram_id,
        "start_date": start_date.isoformat(),
        "end_date": today.isoformat(),
        "total_active_days": total_active_days,
        "current_streak": current_streak,
        "max_streak": max_streak,
        "heatmap": heatmap_sparse,  # faqat faol kunlar — 0 li kunlar yo'q
    }

    cache.set(cache_key, result, timeout=60 * 30)  # 30 daqiqa cache
    return result