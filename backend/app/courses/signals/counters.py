import logging

from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver

from courses.models import Course, Lesson, Modul, Lecture
from contests.models import Contest
from problems.models import Problem
from quizs.models import Question, Test
from courses.api.cache import delete_course_detail_static, delete_course_list_static
logger = logging.getLogger(__name__)


def update_course_counts(course_id):
    Course.objects.filter(id=course_id).update(
        total_modules_count=Modul.objects.filter(course_id=course_id).count(),
        total_lessons_count=Lesson.objects.filter(modul__course_id=course_id).count(),
        total_test_count=Test.objects.filter(modul__course_id=course_id).count(),
    )


def update_lesson_tasks(lesson_id):
    Lesson.objects.filter(id=lesson_id).update(
        total_tasks_count=
            Problem.objects.filter(lesson_id=lesson_id).count()
            + Question.objects.filter(lesson_id=lesson_id).count()
            + Lecture.objects.filter(lesson_id=lesson_id).count()
    )


def update_contest_questions(contest_id):
    Contest.objects.filter(id=contest_id).update(
        questions_count=Problem.objects.filter(contest_id=contest_id).count()
    )

def update_test_question_count(test_id):
    Test.objects.filter(id=test_id).update(
        question_count=Question.objects.filter(test_id=test_id).count()
    )

# ----------------------- Start Courses table ---------------------------
# Kurs yaratilgan ishga tuchivchi logika
@receiver(post_save, sender=Course)
def problem_saved(sender, instance, **kwargs):
    try:
        delete_course_list_static()
        if instance.slug:
            delete_course_detail_static(instance.slug)
    except Exception:
        logger.exception("Courses Saved")

# Kurs o'chirilganda ishga tuchivchi logika
@receiver(post_delete, sender=Course)
def problem_deleted(sender, instance, **kwargs):
    try:
        delete_course_list_static()
        if instance.slug:
                    delete_course_detail_static(instance.slug)
    except Exception:
        logger.exception("courses_deleted")

# o‘chirilishidan oldin ishlaydi.
@receiver(pre_delete, sender=Course)
def course_deleted(sender, instance, **kwargs):
    try:
        delete_course_detail_static(instance.slug)
    except Exception:
        logger.exception("courses_deleted")
# ----------------------- End Courses table ---------------------------

# ----------------------- Start Problems table ---------------------------
# Masala yaratilgan ishga tuchivchi logika
@receiver(post_save, sender=Problem)
def problem_saved(sender, instance, **kwargs):
    try:
        if instance.lesson_id:
            update_lesson_tasks(instance.lesson_id)

        if instance.contest_id:
            update_contest_questions(instance.contest_id)
    except Exception:
        logger.exception("problem_saved")

# Masala o'chirilganda ishga tuchivchi logika
@receiver(post_delete, sender=Problem)
def problem_deleted(sender, instance, **kwargs):
    try:
        if instance.lesson_id:
            update_lesson_tasks(instance.lesson_id)

        if instance.contest_id:
            update_contest_questions(instance.contest_id)
    except Exception:
        logger.exception("problem_deleted")

# ----------------------- End Problems table ---------------------------

@receiver(post_save, sender=Question)
def question_saved(sender, instance, **kwargs):
    try:
        if instance.lesson_id:
            update_lesson_tasks(instance.lesson_id)
    except Exception:
        logger.exception("question_saved")


@receiver(post_delete, sender=Question)
def question_deleted(sender, instance, **kwargs):
    try:
        if instance.lesson_id:
            update_lesson_tasks(instance.lesson_id)
    except Exception:
        logger.exception("question_deleted")

@receiver(post_save, sender=Lecture)
def lecture_saved(sender, instance, **kwargs):
    try:
        if instance.lesson_id:
            update_lesson_tasks(instance.lesson_id)
    except Exception:
        logger.exception("lecture_saved")


@receiver(post_delete, sender=Lecture)
def lecture_deleted(sender, instance, **kwargs):
    try:
        if instance.lesson_id:
            update_lesson_tasks(instance.lesson_id)
    except Exception:
        logger.exception("lecture_deleted")


@receiver(post_save, sender=Lesson)
def lesson_saved(sender, instance, **kwargs):
    try:
        update_course_counts(instance.modul.course_id)
    except Exception:
        logger.exception("lesson_saved")


@receiver(post_delete, sender=Lesson)
def lesson_deleted(sender, instance, **kwargs):
    try:
        update_course_counts(instance.modul.course_id)
    except Exception:
        logger.exception("lesson_deleted")


@receiver(post_save, sender=Test)
def test_saved(sender, instance, **kwargs):
    try:
        update_course_counts(instance.modul.course_id)
    except Exception:
        logger.exception("test_saved")


@receiver(post_delete, sender=Test)
def test_deleted(sender, instance, **kwargs):
    try:
        update_course_counts(instance.modul.course_id)
    except Exception:
        logger.exception("test_deleted")

@receiver(post_save, sender=Modul)
def modul_saved(sender, instance, **kwargs):
    try:
        update_course_counts(instance.course_id)
    except Exception:
        logger.exception("modul_saved")


@receiver(post_delete, sender=Modul)
def modul_deleted(sender, instance, **kwargs):
    try:
        update_course_counts(instance.course_id)
    except Exception:
        logger.exception("modul_deleted")



@receiver(post_save, sender=Question, dispatch_uid="counter_question_test_save_v1")
def on_question_test_save(sender, instance, **kwargs):
    try:
        if instance.test_id:
            update_test_question_count(instance.test_id)

        if instance.lesson_id:
            update_lesson_tasks(instance.lesson_id)

    except Exception:
        logger.exception("on_question_test_save")


@receiver(post_delete, sender=Question, dispatch_uid="counter_question_test_delete_v1")
def on_question_test_delete(sender, instance, **kwargs):
    try:
        if instance.test_id:
            update_test_question_count(instance.test_id)

        if instance.lesson_id:
            update_lesson_tasks(instance.lesson_id)

    except Exception:
        logger.exception("on_question_test_delete")