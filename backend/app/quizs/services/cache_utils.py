"""
Kesh boshqaruvi.

MUHIM DIZAYN QARORI: bitta RaschCalibration versiyasining item beta'lari
YARATILGANDAN KEYIN HECH QACHON O'ZGARMAYDI (immutable). Shuning uchun
"qaysi kalibratsiya faol" degan ko'rsatgichni keshlash bilan "shu
kalibratsiyaning beta qiymatlarini" keshlash ikki xil, mustaqil muammo:

  1. Beta qiymatlari (calibration_id bo'yicha) — UZOQ TTL, invalidatsiya
     shart emas (chunki o'zgarmaydi).
  2. "Faol kalibratsiya ID"si (subject_id bo'yicha) — QISQA TTL,
     activate_calibration() chaqirilganda albatta invalidatsiya qilinadi.
"""
from typing import Optional

from django.core.cache import cache

BETAS_CACHE_TIMEOUT = 60 * 60 * 24  # 24 soat — immutable ma'lumot uchun xavfsiz
ACTIVE_POINTER_CACHE_TIMEOUT = 60 * 30  # 30 daqiqa


def _betas_cache_key(calibration_id: int) -> str:
    return f"rasch:calibration:{calibration_id}:betas"


def _active_pointer_cache_key(subject_id: int) -> str:
    return f"rasch:subject:{subject_id}:active_calibration_id"


def get_cached_calibration_betas(calibration_id: int) -> Optional[dict]:
    return cache.get(_betas_cache_key(calibration_id))


def set_cached_calibration_betas(calibration_id: int, betas: dict) -> None:
    cache.set(_betas_cache_key(calibration_id), betas, timeout=BETAS_CACHE_TIMEOUT)


def get_cached_active_calibration_id(subject_id: int) -> Optional[int]:
    return cache.get(_active_pointer_cache_key(subject_id))


def set_cached_active_calibration_id(subject_id: int, calibration_id: int) -> None:
    cache.set(_active_pointer_cache_key(subject_id), calibration_id, timeout=ACTIVE_POINTER_CACHE_TIMEOUT)


def invalidate_active_pointer_cache(subject_id: int) -> None:
    """activate_calibration() ichida, transaction.on_commit() orqali chaqiriladi."""
    cache.delete(_active_pointer_cache_key(subject_id))


def schedule_recalibration_check(subject_id) -> None:
    """Har bir sessiyadan keyin arzon (DB count) tekshiruvni navbatga qo'yadi."""
    try:
        from ..tasks import maybe_trigger_recalibration
        maybe_trigger_recalibration.delay(str(subject_id))
    except ImportError:
        pass