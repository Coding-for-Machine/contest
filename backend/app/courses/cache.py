import random
from django.core.cache import cache

# ── TTL KONSTANTALARI ────────────────────────────────────────────────────────
STATIC_TTL_BASE = 60 * 60 * 6  # 6 soat
USER_TTL_BASE   = 60 * 5        # 5 daqiqa
JITTER_RANGE    = 60 * 2        # ±2 daqiqa


def _get_jitter_ttl(base_ttl: int) -> int:
    """Thundering herd muammosini oldini olish uchun tasodifiy TTL qaytaradi"""
    low  = max(1, base_ttl - JITTER_RANGE)
    high = base_ttl + JITTER_RANGE
    return random.randint(low, high)


# ── COURSE CACHE KEYS ────────────────────────────────────────────────────────

def _get_course_static_key(slug: str) -> str:
    return f"course:static:{slug}"


def _get_course_user_key(slug: str, user_id: int) -> str:
    return f"course:user:{slug}:{user_id}"


def _get_course_list_key() -> str:
    return "course:list:static"


# ── COURSE CACHE ACTIONS ─────────────────────────────────────────────────────

def get_course_static(slug: str):
    return cache.get(_get_course_static_key(slug))


def set_course_static(slug: str, data: dict) -> None:
    cache.set(_get_course_static_key(slug), data, timeout=_get_jitter_ttl(STATIC_TTL_BASE))


def delete_course_static(slug: str) -> None:
    if slug:
        cache.delete(_get_course_static_key(slug))


def get_course_user(slug: str, user_id: int):
    return cache.get(_get_course_user_key(slug, user_id))


def set_course_user(slug: str, user_id: int, data: dict) -> None:
    cache.set(_get_course_user_key(slug, user_id), data, timeout=_get_jitter_ttl(USER_TTL_BASE))


def delete_course_user(slug: str, user_id: int) -> None:
    if slug and user_id:
        cache.delete(_get_course_user_key(slug, user_id))


def get_course_list_static():
    return cache.get(_get_course_list_key())


def set_course_list_static(data: list) -> None:
    cache.set(_get_course_list_key(), data, timeout=_get_jitter_ttl(STATIC_TTL_BASE))


def delete_course_list_static() -> None:
    cache.delete(_get_course_list_key())


# ── LESSON CACHE KEYS ────────────────────────────────────────────────────────

def _get_lesson_static_key(slug: str) -> str:
    return f"lesson:static:{slug}"


def _get_lesson_user_key(slug: str, user_id: int) -> str:
    return f"lesson:user:{slug}:{user_id}"


# ── LESSON CACHE ACTIONS ─────────────────────────────────────────────────────

def get_lesson_static(slug: str):
    return cache.get(_get_lesson_static_key(slug))


def set_lesson_static(slug: str, data: dict) -> None:
    cache.set(_get_lesson_static_key(slug), data, timeout=_get_jitter_ttl(STATIC_TTL_BASE))


def delete_lesson_static(slug: str) -> None:
    if slug:
        cache.delete(_get_lesson_static_key(slug))


def get_lesson_user(slug: str, user_id: int):
    return cache.get(_get_lesson_user_key(slug, user_id))


def set_lesson_user(slug: str, user_id: int, data: dict) -> None:
    cache.set(_get_lesson_user_key(slug, user_id), data, timeout=_get_jitter_ttl(USER_TTL_BASE))


def delete_lesson_user(slug: str, user_id: int) -> None:
    if slug and user_id:
        cache.delete(_get_lesson_user_key(slug, user_id))
