# certificates/tasks.py

import logging
from celery import shared_task
from celery.exceptions import Retry

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    name="certificates.tasks.generate_certificate_pdf",
)
def generate_certificate_pdf(self, certificate_id: str):
    """
    Sertifikat generatsiya - optimallashtirilgan
    """
    from .models import Certificate
    
    try:
        cert = Certificate.objects.select_related(
            "user",
            "course",
            "test",
            "test_session",
            "contest",
            "contest_registration",
        ).get(pk=certificate_id)
        
        update_fields = {}
        
        # QR generatsiya
        if not cert.qr_code_image:
            try:
                cert._generate_qr()
                update_fields["qr_code_image"] = cert.qr_code_image
                logger.info(f"[CERT] QR yaratildi: {certificate_id}")
            except Exception as e:
                logger.error(f"[CERT] QR xatolik: {e}", exc_info=True)
                # QR muhim emas, davom etish mumkin
        
        # PDF generatsiya
        if not cert.pdf_file:
            try:
                cert._generate_pdf()
                update_fields["pdf_file"] = cert.pdf_file
                logger.info(f"[CERT] PDF yaratildi: {certificate_id}")
            except Exception as e:
                logger.error(f"[CERT] PDF xatolik: {e}", exc_info=True)
                # PDF muhim, retry kerak
                raise
        
        # Saqlash
        if update_fields:
            Certificate.objects.filter(pk=certificate_id).update(**update_fields)
            logger.info(
                "[CERT] %s saqlandi. Maydonlar: %s",
                certificate_id,
                list(update_fields.keys())
            )
        
        return {"status": "success", "certificate_id": certificate_id}
        
    except Certificate.DoesNotExist:
        logger.error(f"[CERT] Topilmadi: {certificate_id}")
        return {"status": "error", "message": "Certificate not found"}
        
    except Exception as exc:
        logger.exception(f"[CERT] Xatolik {certificate_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=15,
    name="certificates.tasks.regenerate_certificate",
)
def regenerate_certificate(self, certificate_id: str):
    """Sertifikatni qayta generatsiya qilish"""
    from .models import Certificate
    
    try:
        cert = Certificate.objects.get(pk=certificate_id)
        
        # Eski fayllarni o'chirish
        if cert.qr_code_image:
            try:
                cert.qr_code_image.delete(save=False)
                logger.info(f"[CERT] Eski QR o'chirildi: {certificate_id}")
            except Exception as e:
                logger.warning(f"[CERT] QR o'chirishda xatolik: {e}")
            cert.qr_code_image = None
        
        if cert.pdf_file:
            try:
                cert.pdf_file.delete(save=False)
                logger.info(f"[CERT] Eski PDF o'chirildi: {certificate_id}")
            except Exception as e:
                logger.warning(f"[CERT] PDF o'chirishda xatolik: {e}")
            cert.pdf_file = None
        
        # Yangi fayllar
        cert._generate_qr()
        cert._generate_pdf()
        
        cert.save(update_fields=['qr_code_image', 'pdf_file'])
        logger.info(f"[CERT] Qayta yaratildi: {certificate_id}")
        
        return {"status": "success", "certificate_id": certificate_id}
        
    except Certificate.DoesNotExist:
        logger.error(f"[CERT] Topilmadi: {certificate_id}")
        return {"status": "error", "message": "Certificate not found"}
        
    except Exception as exc:
        logger.exception(f"[CERT] Regenerate xatolik: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=5,
    name="certificates.tasks.bulk_regenerate_certificates",
)
def bulk_regenerate_certificates(self, certificate_ids: list):
    """Bir nechta sertifikatni qayta generatsiya qilish"""
    success, failed = 0, 0
    
    for cert_id in certificate_ids:
        try:
            regenerate_certificate.delay(cert_id)
            success += 1
        except Exception as exc:
            logger.error(f"[CERT] Navbatga qo'shib bo'lmadi {cert_id}: {exc}")
            failed += 1
    
    logger.info(
        "[CERT] Bulk: %d navbatga qo'yildi, %d xato (jami %d)",
        success, failed, len(certificate_ids),
    )
    
    return {"queued": success, "failed": failed}