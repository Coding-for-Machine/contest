import logging
from django.core.cache import cache
from django.db.models import F
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver

from courses.models import Course, Lesson, Modul
from contests.models import Contest


logger = logging.getLogger(__name__)


def _bump_lesson_tasks(lesson_id: int, delta: int) -> None:
    if not lesson_id:
        return
    if delta > 0:
        Lesson.objects.filter(id=lesson_id).update(total_tasks_count=F("total_tasks_count") + delta)
    else:
        Lesson.objects.filter(id=lesson_id, total_tasks_count__gt=0).update(
            total_tasks_count=F("total_tasks_count") - abs(delta)
        )


def _bump_contest_questions(contest_id: int, delta: int) -> None:
    """Musobaqadagi savollar sonini (questions_count) xavfsiz yangilovchi funksiya"""
    if not contest_id:
        return
    if delta > 0:
        Contest.objects.filter(id=contest_id).update(questions_count=F("questions_count") + delta)
    else:
        Contest.objects.filter(id=contest_id, questions_count__gt=0).update(
            questions_count=F("questions_count") - abs(delta)
        )


def _course_id_and_slug_by_modul(modul_id: int):
    return Course.objects.filter(modullar__id=modul_id).values("id", "slug").first()


# ── Problem ───────────────────────────────────────────────────────────────
@receiver(post_save, sender="problems.Problem", dispatch_uid="counter_problem_save_v2")
def on_problem_save(sender, instance, created, **kwargs):
    if created:
        if instance.lesson_id:
            _bump_lesson_tasks(instance.lesson_id, +1)
        if instance.contest_id:
            _bump_contest_questions(instance.contest_id, +1)


@receiver(post_delete, sender="problems.Problem", dispatch_uid="counter_problem_delete_v2")
def on_problem_delete(sender, instance, **kwargs):
    if instance.lesson_id:
        _bump_lesson_tasks(instance.lesson_id, -1)
    if instance.contest_id:
        _bump_contest_questions(instance.contest_id, -1)


# ── Question ──────────────────────────────────────────────────────────────
@receiver(post_save, sender="quizs.Question", dispatch_uid="counter_question_lesson_save_v2")
def on_question_save_for_lesson(sender, instance, created, **kwargs):
    if created and instance.lesson_id:
        _bump_lesson_tasks(instance.lesson_id, +1)


@receiver(post_delete, sender="quizs.Question", dispatch_uid="counter_question_lesson_delete_v2")
def on_question_delete_for_lesson(sender, instance, **kwargs):
    if instance.lesson_id:
        _bump_lesson_tasks(instance.lesson_id, -1)


# ── Lecture ───────────────────────────────────────────────────────────────
@receiver(post_save, sender="courses.Lecture", dispatch_uid="counter_lecture_save_v2")
def on_lecture_save(sender, instance, created, **kwargs):
    if created and instance.lesson_id:
        _bump_lesson_tasks(instance.lesson_id, +1)


@receiver(post_delete, sender="courses.Lecture", dispatch_uid="counter_lecture_delete_v2")
def on_lecture_delete(sender, instance, **kwargs):
    if instance.lesson_id:
        _bump_lesson_tasks(instance.lesson_id, -1)


# ── Lesson ────────────────────────────────────────────────────────────────
@receiver(post_save, sender=Lesson, dispatch_uid="counter_lesson_save_v1")
def on_lesson_save(sender, instance, created, **kwargs):
    if not (created and instance.modul_id):
        return
    try:
        data = _course_id_and_slug_by_modul(instance.modul_id)
        if not data:
            return
        Course.objects.filter(id=data["id"]).update(total_lessons_count=F("total_lessons_count") + 1)
        if data["slug"]:
            cache.delete(f"course_detail_{data['slug']}")
    except Exception as e:
        logger.error(f"on_lesson_save xato: {e}", exc_info=True)


@receiver(pre_delete, sender=Lesson, dispatch_uid="counter_lesson_delete_v1")
def on_lesson_delete(sender, instance, **kwargs):
    if not instance.modul_id:
        return
    try:
        data = _course_id_and_slug_by_modul(instance.modul_id)
        if not data:
            return
        Course.objects.filter(id=data["id"], total_lessons_count__gt=0).update(
            total_lessons_count=F("total_lessons_count") - 1
        )
        if data["slug"]:
            cache.delete(f"course_detail_{data['slug']}")
    except Exception as e:
        logger.error(f"on_lesson_delete xato: {e}", exc_info=True)


# ── Test ──────────────────────────────────────────────────────────────────
@receiver(post_save, sender='quizs.Test', dispatch_uid="counter_test_save_v1")
def on_test_save(sender, instance, created, **kwargs):
    if not (created and instance.modul_id):
        return
    try:
        data = _course_id_and_slug_by_modul(instance.modul_id)
        if not data:
            return
        Course.objects.filter(id=data["id"]).update(total_test_count=F("total_test_count") + 1)
        if data["slug"]:
            cache.delete(f"course_detail_{data['slug']}")
    except Exception as e:
        logger.error(f"on_test_save xato: {e}", exc_info=True)


@receiver(pre_delete, sender='quizs.Test', dispatch_uid="counter_test_delete_v1")
def on_test_delete(sender, instance, **kwargs):
    if not instance.modul_id:
        return
    try:
        data = _course_id_and_slug_by_modul(instance.modul_id)
        if not data:
            return
        Course.objects.filter(id=data["id"], total_test_count__gt=0).update(
            total_test_count=F("total_test_count") - 1
        )
        if data["slug"]:
            cache.delete(f"course_detail_{data['slug']}")
    except Exception as e:
        logger.warning(f"on_test_delete xato: {e}", exc_info=True)


# ── Modul ───────────────────────────────────────────────────────────────────
@receiver(post_save, sender=Modul, dispatch_uid="counter_modul_save_v1")
def on_modul_save(sender, instance, **kwargs):
    if not instance.course_id:
        return
    try:
        course = Course.objects.filter(id=instance.course_id).only("slug").first()
        if course and course.slug:
            cache.delete(f"course_detail_{course.slug}")
    except Exception as e:
        logger.error(f"on_modul_save xato: {e}", exc_info=True)


@receiver(pre_delete, sender=Modul, dispatch_uid="counter_modul_delete_v1")
def on_modul_delete(sender, instance, **kwargs):
    if not instance.course_id:
        return
    try:
        course = Course.objects.filter(id=instance.course_id).only("slug").first()
        if course and course.slug:
            cache.delete(f"course_detail_{course.slug}")
    except Exception as e:
        logger.error(f"on_modul_delete xato: {e}", exc_info=True)