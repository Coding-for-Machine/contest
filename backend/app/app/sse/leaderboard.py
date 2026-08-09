from .redis_client import sync_redis
# events.py ichidagi barcha zaruriy tuzilmalarni import qilamiz
from .events import Channel, SubmissionEvent, LeaderboardEntry
from status.models import UserStats
from contests.models import ContestRegistration

TOP_N = 20


def _publish(channel: str, event) -> None:
    """Kanal nomini toza string ko'rinishida Redis pub/sub'ga chiqaradi."""
    sync_redis.publish(str(channel), event.to_json())


def publish_global_leaderboard() -> None:
    """Global platforma reytingini yangilaydi va Redisga chiqaradi."""
    top = UserStats.objects.select_related("user").order_by("-xp")[:TOP_N]
    
    # ─── ✅ TUZATILDI: Oddiy dict o'rniga LeaderboardEntry obyekti yaratiladi ───
    entries = [
        LeaderboardEntry(
            rank=i + 1,
            user_id=s.user_id,
            username=s.user.username if s.user else f"User_{s.user_id}",
            xp=s.xp
        )
        for i, s in enumerate(top)
    ]
    
    # Statik kanallar uchun .value ishlatiladi (events.py docstring'ida yozilganidek)
    channel = Channel.LEADERBOARD.value
    event = SubmissionEvent.leaderboard(entries)
    
    _publish(channel, event)


def publish_contest_leaderboard(contest_id: int) -> None:
    """Muayyan musobaqa reytingini yangilaydi va Redisga chiqaradi."""
    top = ContestRegistration.objects.filter(contest_id=contest_id).select_related("user").order_by("-total_xp_earned")[:TOP_N]
    
    # ─── ✅ TUZATILDI: Bu yerda ham LeaderboardEntry ishlatiladi ───
    entries = [
        LeaderboardEntry(
            rank=i + 1,
            user_id=r.user_id,
            username=r.user.username if r.user else f"User_{r.user_id}",
            xp=r.total_xp_earned
        )
        for i, r in enumerate(top)
    ]
    
    # Dinamik kanallar uchun events.py dagi .format() metodi chaqiriladi
    channel = Channel.CONTEST_LEADERBOARD.format(contest_id=contest_id)
    event = SubmissionEvent.contest_leaderboard(contest_id, entries)
    
    _publish(channel, event)
