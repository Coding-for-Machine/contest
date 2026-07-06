# courses/signals/certificate.py
"""
Certificate signali — FAQAT retry uchun.

generate_certificate_pdf task Certificate.save() ichida
transaction.on_commit orqali avtomatik yuboriladi.

Bu yerda QAYTA yubormaymiz — dublikatsiya bo'ladi.
Faqat status='failed' bo'lganda retry qilamiz.
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='certificate.Certificate')
def on_certificate_save(sender, instance, created, **kwargs):
    """
    FAQAT failed holat uchun retry.

    pending  → Certificate.save() o'zi task yuboradi → bu yerda SKIP
    completed → hech narsa
    processing → hech narsa
    failed    → retry_count < 3 bo'lsa qayta yuboramiz
    """
    if created:
        # Certificate.save() allaqachon task yubordi → SKIP
        return

    if instance.status != 'failed':
        return

    if instance.retry_count >= 3:
        logger.error(
            f"Certificate max retry ({instance.retry_count}) yetdi, "
            f"to'xtatildi: {instance.pk}"
        )
        return

    try:
        from certificate.tasks import generate_certificate_pdf

        # Har retry da kechikish oshadi: 1, 2, 3 daqiqa
        countdown = 60 * (instance.retry_count + 1)

        generate_certificate_pdf.apply_async(
            args=[str(instance.pk)],
            countdown=countdown,
        )

        # retry_count ni oshiramiz
        type(instance).objects.filter(pk=instance.pk).update(
            retry_count=instance.retry_count + 1,
        )

        logger.warning(
            f"Certificate retry #{instance.retry_count + 1} "
            f"({countdown}s keyin): {instance.pk}"
        )

    except Exception as e:
        logger.error(f"on_certificate_save retry xato: {e}", exc_info=True)