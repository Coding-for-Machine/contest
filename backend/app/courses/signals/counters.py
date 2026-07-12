import logging
from django.core.cache import cache
from django.db.models import F
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver

from courses.models import Course, Lesson, Modul

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


# ── Problem ───────────────────────────────────────────────────────────────

@receiver(post_save, sender="problems.Problem", dispatch_uid="counter_problem_save_v2")
def on_problem_save(sender, instance, created, **kwargs):
    if created and instance.lesson_id:
        _bump_lesson_tasks(instance.lesson_id, +1)
    # Kesh — yangi yoki tahrirlangan masala ro'yxatga ta'sir qiladi
    if hasattr(cache, "delete_pattern"):
        cache.delete_pattern("problems_list_*")
    else:
        cache.delete("problems_list")
    cache.delete("problems_total_count")


@receiver(post_delete, sender="problems.Problem", dispatch_uid="counter_problem_delete_v2")
def on_problem_delete(sender, instance, **kwargs):
    _bump_lesson_tasks(instance.lesson_id, -1)
    if hasattr(cache, "delete_pattern"):
        cache.delete_pattern("problems_list_*")
    else:
        cache.delete("problems_list")
    cache.delete("problems_total_count")


# ── Question (faqat lesson_id bo'lganlar — test savollari total_tasks_count'ga kirmaydi) ──

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


# ── Lesson (kurs darslar soni) / Test / Modul — o'zgarishsiz (avvalgi javobdagidek) ──
# ... on_lesson_save, on_lesson_delete, on_test_save, on_test_delete,
# ... on_modul_save, on_modul_delete — avvalgi javobimdan o'zgarishsiz qoladi

def _course_id_and_slug_by_modul(modul_id: int):
    return Course.objects.filter(modullar__id=modul_id).values("id", "slug").first()


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
            pass
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
            pass
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
            pass
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
            pass
    except Exception as e:
        logger.warning(f"on_test_delete xato: {e}", exc_info=True)


# ── Problem (Lesson ichidagi total_tasks_count) ─────────────────────────────

@receiver(post_save, sender='problems.Problem', dispatch_uid="counter_problem_save_v1")
def on_problem_save(sender, instance, created, **kwargs):
    if not (created and instance.lesson_id):
        return
    from courses.models import Lesson as LessonModel
    LessonModel.objects.filter(id=instance.lesson_id).update(total_tasks_count=F("total_tasks_count") + 1)


@receiver(pre_delete, sender='problems.Problem', dispatch_uid="counter_problem_delete_v1")
def on_problem_delete(sender, instance, **kwargs):
    if not instance.lesson_id:
        return
    from courses.models import Lesson as LessonModel
    LessonModel.objects.filter(id=instance.lesson_id, total_tasks_count__gt=0).update(
        total_tasks_count=F("total_tasks_count") - 1
    )


# ── Question (Lesson ichidagi total_tasks_count'ga ta'siri, Test ichidagi question_count) ──
# ESLATMA: Test.question_count uchun quizs/signals.py da ALLAQACHON select_for_update()
# bilan yozilgan xavfsiz signal bor — bu yerda takrorlanmaydi.

@receiver(post_save, sender='quizs.Question', dispatch_uid="counter_question_lesson_save_v1")
def on_question_save_for_lesson(sender, instance, created, **kwargs):
    if not (created and instance.lesson_id):
        return
    from courses.models import Lesson as LessonModel
    LessonModel.objects.filter(id=instance.lesson_id).update(total_tasks_count=F("total_tasks_count") + 1)


@receiver(pre_delete, sender='quizs.Question', dispatch_uid="counter_question_lesson_delete_v1")
def on_question_delete_for_lesson(sender, instance, **kwargs):
    if not instance.lesson_id:
        return
    from courses.models import Lesson as LessonModel
    LessonModel.objects.filter(id=instance.lesson_id, total_tasks_count__gt=0).update(
        total_tasks_count=F("total_tasks_count") - 1
    )


# ── Modul (kesh tozalash) ───────────────────────────────────────────────────

@receiver(post_save, sender=Modul, dispatch_uid="counter_modul_save_v1")
def on_modul_save(sender, instance, **kwargs):
    if not instance.course_id:
        return
    try:
        course = Course.objects.filter(id=instance.course_id).only("slug").first()
        if course and course.slug:
            pass
    except Exception as e:
        logger.error(f"on_modul_save xato: {e}", exc_info=True)


@receiver(pre_delete, sender=Modul, dispatch_uid="counter_modul_delete_v1")
def on_modul_delete(sender, instance, **kwargs):
    if not instance.course_id:
        return
    try:
        course = Course.objects.filter(id=instance.course_id).only("slug").first()
        if course and course.slug:
            pass
    except Exception as e:
        logger.error(f"on_modul_delete xato: {e}", exc_info=True)