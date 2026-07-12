"""
Foydalanuvchi progressini kuzatish — YAGONA manba:
  LessonStatus → Enrollment.finished_darslar_soni
  TestSession  → Enrollment.finished_test_soni
  100% bo'lsa  → Certificate avtomat yaratiladi (race-safe get_or_create bilan)
"""
import logging

from django.apps import apps
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from courses.cache import delete_course_user

logger = logging.getLogger(__name__)


def _check_and_graduate(enrollment, total_lessons: int, total_tests: int, update_fields: dict) -> None:
    finished_lessons = min(
        update_fields.get('finished_darslar_soni', enrollment.finished_darslar_soni),
        total_lessons,
    )
    finished_tests = min(
        update_fields.get('finished_test_soni', enrollment.finished_test_soni),
        total_tests,
    )
    update_fields['finished_darslar_soni'] = finished_lessons
    update_fields['finished_test_soni'] = finished_tests

    is_now_completed = (
        total_lessons > 0
        and finished_lessons >= total_lessons
        and finished_tests >= total_tests
    )

    if is_now_completed and not enrollment.is_completed:
        update_fields['is_completed'] = True
        update_fields['completed_at'] = timezone.now()
        _schedule_certificate(enrollment.user_id, enrollment.course_id)
    elif not is_now_completed and enrollment.is_completed:
        update_fields['is_completed'] = False
        update_fields['completed_at'] = None


def _schedule_certificate(user_id: int, course_id: int) -> None:
    """Race-safe: get_or_create() DB darajasida atomik. Bir vaqtda ikkita
    tranzaksiya kelsa ham faqat bitta Certificate yaratiladi (unique_together talab qilinadi)."""
    def _create():
        try:
            Certificate = apps.get_model('certificate', 'Certificate')
            cert, created = Certificate.objects.get_or_create(
                user_id=user_id,
                course_id=course_id,
                defaults={'status': 'pending'},
            )
            logger.info(
                f"Certificate {'yaratildi' if created else 'allaqachon mavjud'}: "
                f"user={user_id}, course={course_id}"
            )
        except Exception as e:
            logger.error(f"_schedule_certificate xato: user={user_id}, course={course_id}: {e}", exc_info=True)

    transaction.on_commit(_create)


@receiver(post_save, sender='status.LessonStatus', dispatch_uid="progress_lesson_status_v1")
def on_lesson_status_save(sender, instance, **kwargs):
    if not instance.is_completed:
        return
    if not (instance.user_id and instance.lesson_id):
        return

    def _run(user_id=instance.user_id, lesson_id=instance.lesson_id):
        try:
            LessonStatus = apps.get_model('status', 'LessonStatus')
            Enrollment = apps.get_model('courses', 'Enrollment')
            Lesson = apps.get_model('courses', 'Lesson')

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

            finished_lessons = LessonStatus.objects.filter(
                user_id=user_id, is_completed=True, lesson__modul__course_id=course.id,
            ).count()

            update_fields = {'finished_darslar_soni': finished_lessons}
            _check_and_graduate(enrollment, course.total_lessons_count or 0, course.total_test_count or 0, update_fields)
            Enrollment.objects.filter(id=enrollment.id).update(**update_fields)

            if course.slug:
                delete_course_user(course.slug, user_id)
        except Exception as e:
            logger.error(f"on_lesson_status_save xato: {e}", exc_info=True)

    transaction.on_commit(_run)


@receiver(post_save, sender='quizs.TestSession', dispatch_uid="progress_test_session_v1")
def on_test_session_save(sender, instance, **kwargs):
    if instance.status != 'completed':
        return
    if not (instance.user_id and instance.test_id):
        return

    def _run(user_id=instance.user_id, test_id=instance.test_id):
        try:
            TestSession = apps.get_model('quizs', 'TestSession')
            Enrollment = apps.get_model('courses', 'Enrollment')
            Test = apps.get_model('quizs', 'Test')

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

            finished_tests = (
                TestSession.objects.filter(
                    user_id=user_id, status='completed', test__modul__course_id=course.id,
                ).values('test_id').distinct().count()
            )

            update_fields = {'finished_test_soni': finished_tests}
            _check_and_graduate(enrollment, course.total_lessons_count or 0, course.total_test_count or 0, update_fields)
            Enrollment.objects.filter(id=enrollment.id).update(**update_fields)

            if course.slug:
                delete_course_user(course.slug, user_id)
        except Exception as e:
            logger.error(f"on_test_session_save xato: {e}", exc_info=True)

    transaction.on_commit(_run)