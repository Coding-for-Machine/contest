import json
from .redis_client import get_redis

# Kesh portlashidan himoya: barcha faol musobaqalar ID ro'yxatini 2 daqiqa keshlaymiz
GLOBAL_CONTESTS_CACHE_KEY = "global_active_contest_ids"
CONTESTS_CACHE_TTL = 120  # 2 daqiqa


async def get_user_active_contest_ids(user_id: int) -> list[int]:
    """
    Tizimdagi ayni vaqtda faol bo'lgan (boshlangan yoki tugamagan) barcha musobaqalar 
    ID ro'yxatini Redis'dan juda tezkor qaytaradi (PostgreSQL yuklamasini nolga tushiradi).
    """
    r = get_redis()
    
    # 1. Birinchi navbatda barcha faol contest ID larini keshdan qidiramiz
    cached_ids = await r.get(GLOBAL_CONTESTS_CACHE_KEY)
    
    if cached_ids is not None:
        # Agar keshda bo'lsa, stringni qayta listga o'giramiz
        return json.loads(cached_ids)
        
    # 2. 🛑 Agar Redis keshida bo'lmasa (Cold Start), bazadan (PostgreSQL) faqat bir marta o'qiymiz
    # Ziddiyatlarni oldini olish uchun modelni funksiya ichida dynamic import qilamiz
    from django.utils import timezone
    from django.apps import apps
    
    Contest = apps.get_model('problems', 'Contest') # yoki musobaqa modelingiz qaysi app'da bo'lsa o'sha nom
    now = timezone.now()
    
    # Faol musobaqalar: boshlanish vaqti o'tgan va tugash vaqti hali kelmaganlar
    # ".values_list('id', flat=True)" mantiqi bazadan ortiqcha Model obyektlarini yuklamaydi
    active_contest_ids = list(
        Contest.objects.filter(
            is_active=True,
            start_time__lte=now,
            end_time__gte=now
        ).values_list('id', flat=True)
    )
    
    # 3. Aniqlangan ID larni keyingi ulanishlar tez o'qishi uchun Redis keshiga yozib qo'yamiz
    await r.set(
        GLOBAL_CONTESTS_CACHE_KEY, 
        json.dumps(active_contest_ids), 
        ex=CONTESTS_CACHE_TTL
    )
    
    return active_contest_ids
