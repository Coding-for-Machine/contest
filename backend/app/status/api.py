from django_bolt import Router, Request
from .models import UserStats

api_status = Router(tags=["Status api"])


@api_status.get("/leaderbar")
async def get_leaderbar(request: Request):
    """
    Global reyting (Leaderboard) ro'yxatini qaytaruvchi eng mukammal asinxron endpoint.
    Kuchli 20 talikni jami XP bo'yicha saralab qaytaradi.
    """
    leaderboard_data = []
    level_choices = dict(UserStats.Level.choices)

    async for status in UserStats.objects.select_related("user").order_by("-xp")[:20]:
        
        display_name = status.user.username if status.user.username else str(status.user.telegram_id)

        leaderboard_data.append({
            "username": display_name,
            "level": level_choices.get(status.level, status.level),
            "xp": status.xp,
        })

    return {
        "success": True,
        "leaderboard": leaderboard_data
    }
