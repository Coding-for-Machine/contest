"""
Celery tasklari.

TUZATILGAN MUAMMOLAR:
  - Hardcoded "quizs.services..." importi olib tashlandi — endi nisbiy
    import (.services...) ishlatiladi, ilova nomidan qat'i nazar ishlaydi.
  - run_calibration_task endi calibration COMPLETED bo'lgach avtomatik
    publish_calibration_task'ni chaqiradi (avval "pass" bilan hech narsa
    qilinmasdi va kalibratsiya abadiy faollashmay qolardi).

CELERY_BEAT_SCHEDULE (settings.py):

    from celery.schedules import crontab

    CELERY_BEAT_SCHEDULE = {
        "close-expired-sessions": {
            "task": "<app_label>.tasks.close_expired_sessions",
            "schedule": crontab(minute="*/1"),
        },
        "check-recalibration-needed": {
            "task": "<app_label>.tasks.check_recalibration_needed",
            "schedule": crontab(minute=0),
        },
    }

Bu yerdagi <app_label> — sizning ilovangiz nomi (models.py joylashgan papka).
"""
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

CLOSE_EXPIRED_CHUNK_SIZE = 100
AUTO_PUBLISH_ENABLED = True  # False qiling — yuqori xavfli imtihonlar uchun faqat qo'lda (admin) faollashtirish


# ============================================================
# Session lifecycle
# ============================================================

@shared_task(bind=True, max_retries=3)
def score_session_task(self, session_id: str):
    """Bitta sessiyani baholaydi. finish_session API va close_expired_sessions chaqiradi."""
    from .models import TestSession
    from .services.scoring import score_session

    try:
        session = TestSession.objects.get(id=session_id)
    except TestSession.DoesNotExist:
        return

    try:
        score_session(session)
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc, countdown=5)


@shared_task
def close_expired_sessions():
    """Muddati o'tgan sessiyalarni yopadi. Katta hajmni chunk'lab navbatga qo'yadi."""
    from .models import TestSession

    session_ids = list(
        TestSession.objects.filter(
            status=TestSession.Status.IN_PROGRESS, test__end_time__lte=timezone.now(),
        ).values_list("id", flat=True)
    )

    for i in range(0, len(session_ids), CLOSE_EXPIRED_CHUNK_SIZE):
        for sid in session_ids[i:i + CLOSE_EXPIRED_CHUNK_SIZE]:
            score_session_task.delay(str(sid))


# ============================================================
# Calibration lifecycle
# ============================================================

@shared_task
def maybe_trigger_recalibration(subject_id: str):
    """Arzon tekshiruv — faqat DB count so'raydi."""
    from .models import Subject
    from .services.calibration import needs_recalibration

    try:
        subject = Subject.objects.get(id=subject_id)
    except Subject.DoesNotExist:
        return

    if needs_recalibration(subject):
        run_calibration_task.delay(subject_id)


@shared_task
def check_recalibration_needed():
    """Davriy (beat, soatiga bir) — barcha faol fanlarni tekshiradi (backup mexanizm)."""
    from .models import Subject

    for subject in Subject.objects.filter(is_active=True):
        maybe_trigger_recalibration.delay(str(subject.id))


@shared_task(bind=True, max_retries=2)
def run_calibration_task(self, subject_id: str):
    """OG'IR operatsiya — to'liq MML kalibratsiya. Muvaffaqiyatli bo'lsa, publish zanjiriga o'tadi."""
    from .services.calibration import calibrate_subject
    from .models import RaschCalibration

    try:
        calibration = calibrate_subject(int(subject_id))
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc, countdown=60)

    if calibration is None:
        logger.error("Kalibratsiya bajarilmadi (girth o'rnatilmagan bo'lishi mumkin): subject=%s", subject_id)
        return

    if calibration.status == RaschCalibration.Status.COMPLETED:
        if AUTO_PUBLISH_ENABLED:
            publish_calibration_task.delay(calibration.id)
        else:
            logger.info(
                "Kalibratsiya v%d COMPLETED holatida — AUTO_PUBLISH o'chirilgan, "
                "admin panelidan qo'lda faollashtiring.", calibration.version,
            )


@shared_task
def publish_calibration_task(calibration_id: int):
    """
    Sifat nazoratidan o'tkazib, faollashtiradi. Admin panelidagi "Faol qilish"
    action ham AYNAN SHU service funksiyasini (services.publishing.publish_calibration)
    chaqiradi — mantiq ikki joyda yozilmagan.
    """
    from .models import RaschCalibration
    from quizs.services.publishing import publish_calibration

    try:
        calibration = RaschCalibration.objects.get(id=calibration_id)
    except RaschCalibration.DoesNotExist:
        return

    published = publish_calibration(calibration)
    logger.info(
        "Kalibratsiya v%d %s", calibration.version, "FAOLLASHTIRILDI" if published else "RAD ETILDI",
    )