"""
Kalibratsiyani faollashtirish (publish) — sifat nazorati bilan.

TUZATILGAN MUAMMOLAR:
  1. Eski kodda "hozirgi faol" kalibratsiya bilan solishtirish o'rniga
     xato ravishda status=RETIRED (allaqachon almashtirilgan, ESKI)
     kalibratsiya bilan solishtirilar edi. Endi to'g'ridan-to'g'ri
     ACTIVE (yoki is_active=True) qidiriladi.
  2. `comparison['mean_beta_diff']` KeyError edi — to'g'ri kalit
     (`mean_abs_aligned_diff`) ishlatiladi.
  3. Admin panel va Celery task ENDI BITTA funksiyani chaqiradi — mantiq
     ikki joyda takrorlanmaydi, ikkisi bir xil sifat nazoratidan o'tadi.
"""
import logging

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# Sifat mezonlari
MAX_FLAGGED_RATIO = 0.15  # 15% dan ko'p savol muammoli bo'lsa — rad etiladi


def activate_calibration(calibration) -> None:
    """
    Calibrationni ACTIVE qiladi. Oldingi faol kalibratsiya RETIRED bo'ladi.
    Bu funksiya sifat tekshiruvisiz, TO'G'RIDAN-TO'G'RI faollashtiradi —
    sifat tekshiruvi uchun publish_calibration() dan foydalaning.
    """
    from .cache_utils import invalidate_active_pointer_cache
    from ..models import RaschCalibration

    with transaction.atomic():
        RaschCalibration.objects.filter(
            subject=calibration.subject, is_active=True
        ).exclude(pk=calibration.pk).update(is_active=False, status=RaschCalibration.Status.RETIRED)

        calibration.is_active = True
        calibration.status = RaschCalibration.Status.ACTIVE
        calibration.activated_at = timezone.now()
        calibration.save(update_fields=["is_active", "status", "activated_at"])

        transaction.on_commit(lambda: invalidate_active_pointer_cache(calibration.subject_id))

    logger.info("Kalibratsiya FAOL qilindi: %s v%d", calibration.subject.name, calibration.version)


def quality_check(calibration) -> dict:
    """
    Kalibratsiyani nashr qilishga tayyorligini tekshiradi.
    Qaytaradi: {"passed": bool, "reason": str, "comparison": dict | None}
    """
    from .calibration import compare_calibrations
    from ..models import RaschCalibration

    if calibration.status != RaschCalibration.Status.COMPLETED:
        return {"passed": False, "reason": f"Status COMPLETED emas: {calibration.status}", "comparison": None}

    if not calibration.converged:
        return {"passed": False, "reason": "Kalibratsiya yaqinlashmagan (not converged).", "comparison": None}

    item_count = max(calibration.item_count, 1)
    flagged_count = calibration.item_parameters.filter(flagged_for_review=True).count()
    flagged_ratio = flagged_count / item_count

    if flagged_ratio > MAX_FLAGGED_RATIO:
        return {
            "passed": False,
            "reason": f"Muammoli savollar ko'p: {flagged_ratio:.1%} (chegara: {MAX_FLAGGED_RATIO:.0%}).",
            "comparison": None,
        }

    # === TUZATISH: hozirgi FAOL (ACTIVE) kalibratsiya bilan solishtiramiz, RETIRED emas ===
    current_active = (
        calibration.subject.rasch_calibrations
        .filter(status=RaschCalibration.Status.ACTIVE, is_active=True)
        .exclude(pk=calibration.pk)
        .order_by("-version")
        .first()
    )

    if current_active is None:
        # Bootstrap holati — bu fan uchun birinchi kalibratsiya, solishtiradigan hech narsa yo'q.
        return {"passed": True, "reason": "Birinchi kalibratsiya (bootstrap) — solishtirish shart emas.", "comparison": None}

    comparison = compare_calibrations(current_active, calibration)
    if not comparison.get("stable", False):
        return {
            "passed": False,
            "reason": (
                f"Kalibratsiya beqaror: correlation={comparison.get('correlation')}, "
                f"mean_abs_diff={comparison.get('mean_abs_aligned_diff')}, "
                f"reason={comparison.get('reason', '')}"
            ),
            "comparison": comparison,
        }

    return {"passed": True, "reason": "Barcha sifat mezonlaridan o'tdi.", "comparison": comparison}


def publish_calibration(calibration) -> bool:
    """
    Sifat nazoratidan o'tkazadi va faollashtiradi. Admin panel ("Faol qilish"
    action) va Celery task (auto-publish) IKKALASI HAM shu funksiyani
    chaqirishi kerak — shunda mantiq ikki joyda takrorlanmaydi.

    Qaytaradi: True — faollashtirildi, False — rad etildi.
    """
    from ..models import RaschCalibration

    result = quality_check(calibration)

    if not result["passed"]:
        calibration.status = RaschCalibration.Status.REJECTED
        calibration.rejection_reason = result["reason"]
        calibration.save(update_fields=["status", "rejection_reason"])
        logger.warning("Kalibratsiya nashr qilinmadi (v%d): %s", calibration.version, result["reason"])
        return False

    activate_calibration(calibration)
    return True