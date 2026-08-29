from __future__ import annotations

import logging
import msgspec
from django.core.cache import cache

logger = logging.getLogger(__name__)

# ==========================================================
# MSGSPEC ENCODER / DECODER
# ==========================================================
# msgspec juda tez, lekin xatoliklarni ushlab qolish uchun try-except kerak
encoder = msgspec.json.Encoder()
decoder = msgspec.json.Decoder()

# ==========================================================
# CACHE PREFIX
# ==========================================================
COURSE_LIST_STATIC_KEY = "course:list:static"
COURSE_DETAIL_STATIC_KEY = "courses:det:{slug}:static"
COURSE_USER_PROGRESS_KEY = "courses:{slug}:user:{user_id}:progress"

# ==========================================================
# TTL (Time To Live)
# ==========================================================
STATIC_TTL = 60 * 60  # 24 soat
USER_TTL = 60 #* 60    # 1 soat (Keshni to'g'ri o'chirsak, TTLni uzaytirish mumkin)

# ==========================================================
# LOW LEVEL FUNCTIONS
# ==========================================================
def cache_set(key: str, value, ttl: int) -> None:
    try:
        encoded = encoder.encode(value)
        cache.set(key, encoded, ttl)
    except Exception as e:
        logger.error(f"Keshga yozishda xatolik. Kalit: {key}, Xatolik: {e}")

def cache_get(key: str):
    data = cache.get(key)
    if not data:
        return None
    try:
        # Ma'lumotni xavfsiz dekodlash
        return decoder.decode(data)
    except msgspec.DecodeError as e:
        logger.error(f"Keshni o'qishda dekodlash xatoligi. Kalit: {key}, Xatolik: {e}")
        # Agar kesh buzilgan bo'lsa, uni o'chirib tashlaymiz
        cache.delete(key)
        return None

def cache_delete(key: str) -> None:
    cache.delete(key)

# ==========================================================
# COURSE LIST STATIC
# ==========================================================
def get_course_list_static():
    return cache_get(COURSE_LIST_STATIC_KEY)

def set_course_list_static(data):
    cache_set(COURSE_LIST_STATIC_KEY, data, STATIC_TTL)

def delete_course_list_static():
    cache_delete(COURSE_LIST_STATIC_KEY)

# ==========================================================
# COURSE DETAIL STATIC
# ==========================================================
def get_course_detail_static(slug: str):
    key = COURSE_DETAIL_STATIC_KEY.format(slug=slug)
    return cache_get(key)

def set_course_detail_static(slug: str, data):
    key = COURSE_DETAIL_STATIC_KEY.format(slug=slug)
    cache_set(key, data, STATIC_TTL)

def delete_course_detail_static(slug: str):
    key = COURSE_DETAIL_STATIC_KEY.format(slug=slug)
    cache_delete(key)

# ==========================================================
# USER PROGRESS CACHE
# ==========================================================
def get_course_user_cache(slug: str, user_id: int):
    key = COURSE_USER_PROGRESS_KEY.format(slug=slug, user_id=user_id)
    return cache_get(key)

def set_course_user_cache(slug: str, user_id: int, data):
    key = COURSE_USER_PROGRESS_KEY.format(slug=slug, user_id=user_id)
    cache_set(key, data, USER_TTL)

def delete_course_user_cache(slug: str, user_id: int):
    key = COURSE_USER_PROGRESS_KEY.format(slug=slug, user_id=user_id)
    cache_delete(key)



HERO_CACHE_KEY = "course:hero:v1"
HERO_CACHE_TTL = 300  # 5 daqiqa


def get_hero_course_cache() -> dict | None:
    return cache.get(HERO_CACHE_KEY)


def set_hero_course_cache(data: dict, timeout: int = HERO_CACHE_TTL) -> None:
    cache.set(HERO_CACHE_KEY, data, timeout=timeout)


def invalidate_hero_course_cache() -> None:
    """Yangi Enrollment yaratilganda albatta chaqirish shart emas
    (5 daqiqalik TTL o'zi yetarli darajada yangi holatni ko'rsatadi),
    lekin admin panelda kurs faolligini o'zgartirganda chaqiring."""
    cache.delete(HERO_CACHE_KEY)