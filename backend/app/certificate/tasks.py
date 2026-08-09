import logging

from celery import shared_task, group
from celery.exceptions import MaxRetriesExceededError

logger = logging.getLogger(__name__)


# ============================================================
# GENERATE CERTIFICATE FILES (ASOSIY TASK)
# ============================================================

@shared_task(
    bind=True,
    max_retries=3,
    retry_backoff=True,       # 60s, 120s, 240s... eksponensial
    retry_backoff_max=600,
    retry_jitter=True,
    acks_late=True,           # crash bo'lsa qayta navbatga tushadi
    soft_time_limit=300,
    time_limit=360,
)
def generate_certificate_files(self, certificate_id):
    """
    Certificate uchun QR va PDF yaratadi.
    """
    certificate = None

    try:
        from .models import Certificate

        certificate = (
            Certificate.objects
            .select_related("user", "template", "course", "test", "contest")
            .get(id=certificate_id)
        )

        # Agar allaqachon tayyor bo'lsa
        if certificate.status == Certificate.Status.COMPLETED:
            logger.info(f"Certificate already completed: {certificate.id}")
            return {
                "status": "already_completed",
                "certificate_id": str(certificate.id),
            }

        # Asosiy generatsiya oqimi
        certificate.generate_files()

        logger.info(f"Certificate generated: {certificate.id}")

        return {
            "status": "completed",
            "certificate_id": str(certificate.id),
        }

    except Certificate.DoesNotExist:
        logger.error(f"Certificate not found: {certificate_id}")
        return {"status": "not_found"}

    except Exception as exc:
        logger.error(
            f"Certificate generation failed: {certificate_id}",
            exc_info=True,
        )

        if certificate is not None:
            try:
                certificate.generation_failed(exc)
            except Exception as e:
                logger.exception(f"Failed to set generation_failed status: {e}")

        # Retry qilish
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for certificate: {certificate_id}")
            raise exc


# ============================================================
# REGENERATE CERTIFICATE
# ============================================================

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=360,
)
def regenerate_certificate(self, certificate_id):
    """
    Mavjud sertifikatni qayta generatsiya qiladi.
    """
    from .models import Certificate

    certificate = None

    try:
        certificate = Certificate.objects.get(id=certificate_id)

        # Model ichidagi method orqali tozalash va qayta boshlash
        certificate.reset_for_regeneration()

        # Asosiy generatsiya oqimi
        certificate.generate_files()

        logger.info(f"Certificate regenerated: {certificate_id}")
        return {
            "status": "completed",
            "certificate_id": str(certificate_id),
        }

    except Certificate.DoesNotExist:
        logger.error(f"Certificate not found: {certificate_id}")
        return {"status": "not_found"}

    except Exception as exc:
        logger.error(
            f"Certificate regeneration failed: {certificate_id}",
            exc_info=True,
        )

        if certificate is not None:
            try:
                certificate.generation_failed(exc)
            except Exception as e:
                logger.exception(f"Failed to set generation_failed status: {e}")

        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for regeneration: {certificate_id}")
            raise exc


# ============================================================
# BULK GENERATE CERTIFICATES (DEADLOCK MUAMMO YO'Q)
# ============================================================

@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def bulk_generate_certificates(self, certificate_ids):
    """
    Bir nechta sertifikatlarni parallel generatsiya qiladi.
    .get() ISHLATILMAYDI — deadlock xavfi yo'q.
    """
    if not certificate_ids:
        return {"status": "empty", "queued": 0}

    # group() orqali parallel tasklar yaratish
    jobs = [
        generate_certificate_files.s(cert_id)
        for cert_id in certificate_ids
    ]

    # Barchasini navbatga qo'shish
    group(jobs).apply_async()

    logger.info(f"Bulk generation queued: {len(certificate_ids)} certificates")
    return {
        "status": "queued",
        "total": len(certificate_ids),
    }


# ============================================================
# BULK REGENERATE CERTIFICATES
# ============================================================

@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def bulk_regenerate_certificates(self, certificate_ids):
    """
    Bir nechta sertifikatlarni parallel qayta generatsiya qiladi.
    """
    if not certificate_ids:
        return {"status": "empty", "queued": 0}

    jobs = [
        regenerate_certificate.s(cert_id)
        for cert_id in certificate_ids
    ]

    group(jobs).apply_async()

    logger.info(f"Bulk regeneration queued: {len(certificate_ids)} certificates")
    return {
        "status": "queued",
        "total": len(certificate_ids),
    }


# ============================================================
# CLEANUP OLD FILES
# ============================================================

@shared_task
def cleanup_old_certificate_files(days=30):
    """
    Eski sertifikat fayllarini tozalash.
    """
    from django.utils import timezone
    from datetime import timedelta
    from .models import Certificate

    threshold = timezone.now() - timedelta(days=days)

    old_certificates = Certificate.objects.filter(
        issued_at__lt=threshold,
        status__in=[Certificate.Status.COMPLETED, Certificate.Status.FAILED]
    )

    deleted_count = 0
    for cert in old_certificates:
        try:
            cert.clear_files()
            cert.save(update_fields=["pdf_file", "qr_code_image"])
            deleted_count += 1
        except Exception as e:
            logger.error(f"Failed to delete files for {cert.id}: {e}")

    logger.info(f"Cleaned up {deleted_count} old certificate files")
    return {"deleted": deleted_count}

@shared_task
def recover_stuck_certificates(stale_minutes=15):
    from django.utils import timezone
    from datetime import timedelta
    from .models import Certificate

    threshold = timezone.now() - timedelta(minutes=stale_minutes)
    stuck = Certificate.objects.filter(
        status=Certificate.Status.PROCESSING,
        issued_at__lt=threshold,
    )
    for cert in stuck:
        regenerate_certificate.delay(str(cert.id))
    return {"recovered": stuck.count()}