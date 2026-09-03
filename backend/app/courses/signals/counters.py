import logging

from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver

from courses.models import (
    Course,
    Lesson,
    Modul,
    Lecture,
    CourseTest,
    CourseQuestion,
)
from contests.models import Contest
from problems.models import Problem

from courses.api.cache import (
    delete_course_detail_static,
    delete_course_list_static,
)

logger = logging.getLogger(__name__)


# ======================================================================
# COUNTERS
# ======================================================================

def update_course_counts(course_id):
    """
    Kursdagi:
    - jami modullar
    - jami darslar
    - jami testlar

    sonini yangilaydi.
    """

    Course.objects.filter(id=course_id).update(
        total_modules_count=Modul.objects.filter(
            course_id=course_id
        ).count(),

        total_lessons_count=Lesson.objects.filter(
            modul__course_id=course_id
        ).count(),

        total_test_count=CourseTest.objects.filter(
            modul__course_id=course_id
        ).count(),
    )


def update_lesson_tasks(lesson_id):
    """
    Darsdagi jami:
    - Problem
    - CourseQuestion
    - Lecture

    sonini yangilaydi.
    """

    total_tasks = (
        Problem.objects.filter(
            lesson_id=lesson_id
        ).count()
        +
        CourseQuestion.objects.filter(
            lesson_id=lesson_id
        ).count()
        +
        Lecture.objects.filter(
            lesson_id=lesson_id
        ).count()
    )

    Lesson.objects.filter(id=lesson_id).update(
        total_tasks_count=total_tasks
    )


def update_contest_questions(contest_id):
    Contest.objects.filter(id=contest_id).update(
        questions_count=Problem.objects.filter(
            contest_id=contest_id
        ).count()
    )


def update_test_question_count(test_id):
    """
    CourseTest ichidagi savollar sonini yangilaydi.
    """

    CourseTest.objects.filter(id=test_id).update(
        question_count=CourseQuestion.objects.filter(
            test_id=test_id
        ).count()
    )


# ======================================================================
# COURSE
# ======================================================================

@receiver(post_save, sender=Course, dispatch_uid="course_saved_v1")
def course_saved(sender, instance, **kwargs):
    try:
        delete_course_list_static()

        if instance.slug:
            delete_course_detail_static(instance.slug)

    except Exception:
        logger.exception("course_saved")


@receiver(post_delete, sender=Course, dispatch_uid="course_deleted_v1")
def course_deleted(sender, instance, **kwargs):
    try:
        delete_course_list_static()

        if instance.slug:
            delete_course_detail_static(instance.slug)

    except Exception:
        logger.exception("course_deleted")


@receiver(pre_delete, sender=Course, dispatch_uid="course_pre_delete_v1")
def course_pre_delete(sender, instance, **kwargs):
    try:
        if instance.slug:
            delete_course_detail_static(instance.slug)

    except Exception:
        logger.exception("course_pre_delete")


# ======================================================================
# PROBLEM
# ======================================================================

@receiver(post_save, sender=Problem, dispatch_uid="problem_saved_v1")
def problem_saved(sender, instance, **kwargs):
    try:
        if instance.lesson_id:
            update_lesson_tasks(instance.lesson_id)

        if instance.contest_id:
            update_contest_questions(instance.contest_id)

    except Exception:
        logger.exception("problem_saved")


@receiver(post_delete, sender=Problem, dispatch_uid="problem_deleted_v1")
def problem_deleted(sender, instance, **kwargs):
    try:
        if instance.lesson_id:
            update_lesson_tasks(instance.lesson_id)

        if instance.contest_id:
            update_contest_questions(instance.contest_id)

    except Exception:
        logger.exception("problem_deleted")


# ======================================================================
# COURSE QUESTION
# ======================================================================

@receiver(
    post_save,
    sender=CourseQuestion,
    dispatch_uid="course_question_saved_v1",
)
def course_question_saved(sender, instance, **kwargs):
    try:
        if instance.lesson_id:
            update_lesson_tasks(instance.lesson_id)

        if instance.test_id:
            update_test_question_count(instance.test_id)

    except Exception:
        logger.exception("course_question_saved")


@receiver(
    post_delete,
    sender=CourseQuestion,
    dispatch_uid="course_question_deleted_v1",
)
def course_question_deleted(sender, instance, **kwargs):
    try:
        if instance.lesson_id:
            update_lesson_tasks(instance.lesson_id)

        if instance.test_id:
            update_test_question_count(instance.test_id)

    except Exception:
        logger.exception("course_question_deleted")


# ======================================================================
# LECTURE
# ======================================================================

@receiver(
    post_save,
    sender=Lecture,
    dispatch_uid="lecture_saved_v1",
)
def lecture_saved(sender, instance, **kwargs):
    try:
        if instance.lesson_id:
            update_lesson_tasks(instance.lesson_id)

    except Exception:
        logger.exception("lecture_saved")


@receiver(
    post_delete,
    sender=Lecture,
    dispatch_uid="lecture_deleted_v1",
)
def lecture_deleted(sender, instance, **kwargs):
    try:
        if instance.lesson_id:
            update_lesson_tasks(instance.lesson_id)

    except Exception:
        logger.exception("lecture_deleted")


# ======================================================================
# LESSON
# ======================================================================

@receiver(
    post_save,
    sender=Lesson,
    dispatch_uid="lesson_saved_v1",
)
def lesson_saved(sender, instance, **kwargs):
    try:
        update_course_counts(instance.modul.course_id)

    except Exception:
        logger.exception("lesson_saved")


@receiver(
    post_delete,
    sender=Lesson,
    dispatch_uid="lesson_deleted_v1",
)
def lesson_deleted(sender, instance, **kwargs):
    try:
        update_course_counts(instance.modul.course_id)

    except Exception:
        logger.exception("lesson_deleted")


# ======================================================================
# MODULE
# ======================================================================

@receiver(
    post_save,
    sender=Modul,
    dispatch_uid="modul_saved_v1",
)
def modul_saved(sender, instance, **kwargs):
    try:
        update_course_counts(instance.course_id)

    except Exception:
        logger.exception("modul_saved")


@receiver(
    post_delete,
    sender=Modul,
    dispatch_uid="modul_deleted_v1",
)
def modul_deleted(sender, instance, **kwargs):
    try:
        update_course_counts(instance.course_id)

    except Exception:
        logger.exception("modul_deleted")


# ======================================================================
# COURSE TEST
# ======================================================================

@receiver(
    post_save,
    sender=CourseTest,
    dispatch_uid="course_test_saved_v1",
)
def course_test_saved(sender, instance, **kwargs):
    try:
        update_course_counts(instance.modul.course_id)

        # Test yaratilganda mavjud savollar sonini ham sync qilish
        update_test_question_count(instance.id)

    except Exception:
        logger.exception("course_test_saved")


@receiver(
    post_delete,
    sender=CourseTest,
    dispatch_uid="course_test_deleted_v1",
)
def course_test_deleted(sender, instance, **kwargs):
    try:
        update_course_counts(instance.modul.course_id)

    except Exception:
        logger.exception("course_test_deleted")


# signals.py — kurs/lesson/enrollment o'zgarganda cache invalidatsiya
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from courses.models import Course, Lesson, Lecture, Enrollment
from courses.api import cache as course_cache

@receiver([post_save, post_delete], sender=Course)
def course_changed(sender, instance, **kwargs):
    course_cache.delete_course_list_static()
    course_cache.delete_course_detail_static(instance.slug)

@receiver([post_save, post_delete], sender=Lesson)
def lesson_changed(sender, instance, **kwargs):
    course_cache.delete_course_detail_static(instance.modul.course.slug)

@receiver([post_save, post_delete], sender=Lecture)
def lecture_changed(sender, instance, **kwargs):
    course_cache.delete_course_detail_static(instance.lesson.modul.course.slug)

@receiver([post_save, post_delete], sender=Enrollment)
def enrollment_changed(sender, instance, **kwargs):
    course_cache.delete_course_user_cache(instance.course.slug, instance.user_id)
    course_cache.delete_course_detail_static(instance.course.slug)