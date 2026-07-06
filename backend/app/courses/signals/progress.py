"""
Foydalanuvchi progressini kuzatish:
  LessonStatus → Enrollment.finished_darslar_soni
  TestSession  → Enrollment.finished_test_soni
  100% bo'lsa  → Certificate avtomat yaratiladi
"""
import logging

from django.apps import apps
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from courses.cache import delete_course_user

logger = logging.getLogger(__name__)


# ── Graduation helper ─────────────────────────────────────────────────────────

def _check_and_graduate(
    enrollment,
    total_lessons: int,
    total_tests: int,
    update_fields: dict,
) -> None:
    """Kurs 100% bitirildimi tekshiradi va sertifikatga navbatga qo'yadi"""
    finished_lessons = min(
        update_fields.get('finished_darslar_soni', enrollment.finished_darslar_soni),
        total_lessons,
    )
    finished_tests = min(
        update_fields.get('finished_test_soni', enrollment.finished_test_soni),
        total_tests,
    )

    update_fields['finished_darslar_soni'] = finished_lessons
    update_fields['finished_test_soni']    = finished_tests

    is_now_completed = (
        total_lessons > 0
        and finished_lessons >= total_lessons
        and finished_tests   >= total_tests
    )

    if is_now_completed and not enrollment.is_completed:
        update_fields['is_completed'] = True
        update_fields['completed_at'] = timezone.now()
        _schedule_certificate(enrollment.user_id, enrollment.course_id)

    elif not is_now_completed and enrollment.is_completed:
        update_fields['is_completed'] = False
        update_fields['completed_at'] = None


def _schedule_certificate(user_id: int, course_id: int) -> None:
    """Kurs 100% bitganda atomik tranzaksiya yakunida Certificate yaratadi"""
    def _create():
        try:
            Certificate = apps.get_model('certificate', 'Certificate')
            cert, created = Certificate.objects.get_or_create(
                user_id=user_id,
                course_id=course_id,
                defaults={'status': 'pending'},
            )
            if created:
                logger.info(f"Certificate yaratildi (pending): user={user_id}, course={course_id}")
            else:
                logger.info(f"Certificate allaqachon mavjud: user={user_id}, course={course_id}")
        except Exception as e:
            logger.error(f"_schedule_certificate xato: user={user_id}, course={course_id}: {e}", exc_info=True)

    transaction.on_commit(_create)


# ── LessonStatus Signal ───────────────────────────────────────────────────────

@receiver(post_save, sender='status.LessonStatus')
def on_lesson_status_save(sender, instance, **kwargs):
    """Dars tugallanganda enrollment progressini yangilaydi va keshni o'chiradi"""
    if not instance.is_completed:
        return
    if not (instance.user_id and instance.lesson_id):
        return

    def _run(user_id=instance.user_id, lesson_id=instance.lesson_id):
        try:
            LessonStatus = apps.get_model('status',   'LessonStatus')
            Enrollment   = apps.get_model('courses',  'Enrollment')
            Lesson       = apps.get_model('courses',  'Lesson')

            # `_base` funksiyasi o'rniga yengil ORM so'rovi (faqat kerakli ustunlar yuklanadi)
            lesson = Lesson.objects.filter(id=lesson_id).select_related('modul__course').only(
                'modul__course__id', 'modul__course__slug', 
                'modul__course__total_lessons_count', 'modul__course__total_test_count'
            ).first()

            if not (lesson and lesson.modul and lesson.modul.course):
                return

            course = lesson.modul.course

            enrollment = Enrollment.objects.filter(user_id=user_id, course_id=course.id).first()
            if not enrollment:
                return

            # Unikal yakunlangan darslar soni
            finished_lessons = LessonStatus.objects.filter(
                user_id=user_id,
                is_completed=True,
                lesson__modul__course_id=course.id,
            ).count()

            update_fields = {'finished_darslar_soni': finished_lessons}

            _check_and_graduate(
                enrollment,
                course.total_lessons_count or 0,
                course.total_test_count or 0,
                update_fields,
            )

            Enrollment.objects.filter(id=enrollment.id).update(**update_fields)

            if course.slug:
                delete_course_user(course.slug, user_id)

        except Exception as e:
            logger.error(f"on_lesson_status_save xato: {e}", exc_info=True)

    transaction.on_commit(_run)


# ── TestSession Signal ────────────────────────────────────────────────────────

@receiver(post_save, sender='quizs.TestSession')
def on_test_session_save(sender, instance, **kwargs):
    """Test yakunlanganda enrollment progressini yangilaydi va keshni o'chiradi"""
    if instance.status != 'completed':
        return
    if not (instance.user_id and instance.test_id):
        return

    def _run(user_id=instance.user_id, test_id=instance.test_id):
        try:
            TestSession = apps.get_model('quizs',    'TestSession')
            Enrollment  = apps.get_model('courses',  'Enrollment')
            Test        = apps.get_model('quizs',    'Test')

            # `_base` funksiyasi o'rniga yengil select_related va only filtri
            test = Test.objects.filter(id=test_id).select_related('modul__course').only(
                'modul__course__id', 'modul__course__slug', 
                'modul__course__total_lessons_count', 'modul__course__total_test_count'
            ).first()

            if not (test and test.modul and test.modul.course):
                logger.info(f"Mustaqil test yakunlandi (test_id={test_id}), progress o'zgarmadi.")
                return

            course = test.modul.course

            enrollment = Enrollment.objects.filter(user_id=user_id, course_id=course.id).first()
            if not enrollment:
                return

            # Unikal yakunlangan testlar soni
            finished_tests = (
                TestSession.objects
                .filter(
                    user_id=user_id,
                    status='completed',  # String status xavfsizligi
                    test__modul__course_id=course.id,
                )
                .values('test_id')
                .distinct()
                .count()
            )

            update_fields = {'finished_test_soni': finished_tests}

            _check_and_graduate(
                enrollment,
                course.total_lessons_count or 0,
                course.total_test_count or 0,
                update_fields,
            )

            Enrollment.objects.filter(id=enrollment.id).update(**update_fields)

            if course.slug:
                delete_course_user(course.slug, user_id)

        except Exception as e:
            logger.error(f"on_test_session_save xato: {e}", exc_info=True)

    transaction.on_commit(_run)
