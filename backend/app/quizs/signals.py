# app/quizs/signals.py
import logging
import base64
import io
import qrcode
from django.db import models
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings

from .models import TestSession, Test, CertificateTemplate, Certificate

logger = logging.getLogger(__name__)


def calculate_percentage(session: TestSession) -> float:
    """Sessiyaning foiz natijasini hisoblaydi: (score / max_mumkin_ball) * 100."""
    total_possible = session.test.questions.aggregate(total=Sum('xp'))['total'] or 0
    if total_possible <= 0:
        return 0.0
    return (session.score / total_possible) * 100


def _issue_independent_test_certificate(session: TestSession, percentage: float) -> Certificate | None:
    """Mustaqil (kursga bog'lanmagan) test uchun sertifikat berish."""
    test = session.test
    user = session.user

    # O'tish foizini testning o'zidan tekshiramiz
    if percentage < test.min_pass_percentage:
        logger.info(
            "❌ Ball yetarli emas: %.1f%% < %s%% (test='%s', user=%s)",
            percentage, test.min_pass_percentage, test.title, user.id
        )
        return None

    # ⚡️ YANGI TOZA ARXITEKTURA: 'template' maydoni defaults ichidan olib tashlandi
    certificate, created = Certificate.objects.get_or_create(
        user=user,
        test_session=session,
        test=test,
    )
    if created:
        logger.info("🎉 Mustaqil test sertifikati yaratildi: %s (user=%s)", certificate.certificate_code, user.id)
    return certificate if created else None


def _all_course_tests_passed(user, course) -> bool:
    """Foydalanuvchi kursdagi BARCHA faol testlarni muvaffaqiyatli o'tganmi tekshiradi."""
    course_tests = Test.objects.filter(lesson__modul__course=course, is_active=True)
    total_tests = course_tests.count()

    if total_tests == 0:
        return False

    for test_item in course_tests:
        max_score = test_item.questions.aggregate(total=Sum('xp'))['total'] or 0
        if max_score <= 0:
            return False

        best_session = (
            TestSession.objects
            .filter(user=user, test=test_item, status=TestSession.Status.COMPLETED)
            .order_by('-score')
            .first()
        )
        if best_session is None:
            return False

        test_percentage = (best_session.score / max_score) * 100
        if test_percentage < test_item.min_pass_percentage:
            return False

    return True


def _issue_course_certificate(session: TestSession) -> Certificate | None:
    """Kursdagi barcha testlarni yopganda, kurs uchun to'g'ridan-to'g'ri sertifikat berish."""
    test = session.test
    user = session.user
    lesson = test.lesson

    if not lesson or not lesson.modul or not lesson.modul.course:
        logger.warning(
            "⚠️ Test '%s' lesson/modul/course bog'lanishi to'liq emas, kurs sertifikati tekshirilmadi.",
            test.title,
        )
        return None

    course = lesson.modul.course

    # Barcha testlarni topshirganini tekshirish
    if not _all_course_tests_passed(user, course):
        logger.info("ℹ️ Kursdagi barcha testlar hali o'tilmagan: kurs='%s', user=%s", course.title, user.id)
        return None

    # ⚡️ YANGI TOZA ARXITEKTURA: 'template' maydoni defaults ichidan olib tashlandi
    certificate, created = Certificate.objects.get_or_create(
        user=user,
        course=course,
        test_session=session,
    )
    if created:
        logger.info("🎉 Kurs sertifikati yaratildi: %s (user=%s, kurs='%s')", certificate.certificate_code, user.id, course.title)
    return certificate if created else None


@receiver(post_save, sender=TestSession)
def handle_test_session_completion(sender, instance: TestSession, created: bool, **kwargs):
    """🎯 TEST SESSIYASI 'completed' holatiga o'tganda ishlaydigan signal."""
    # Faqat yakunlangan sessiyalar uchun ishlaymiz
    if instance.status != TestSession.Status.COMPLETED:
        return

    if not instance.test:
        return

    user = instance.user
    logger.info("📊 Sessiya qayta ishlanmoqda: id=%s, user=%s", instance.id, user.id)

    percentage = calculate_percentage(instance)
    logger.info("   📈 Natija: score=%.2f -> %.1f%%", instance.score, percentage)

    try:
        if instance.test.lesson:
            _issue_course_certificate(instance)
        else:
            _issue_independent_test_certificate(instance, percentage)
    except Exception:
        logger.exception("❌ Sertifikat yaratishda xatolik: session=%s, user=%s", instance.id, user.id)
