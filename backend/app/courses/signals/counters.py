import logging
from django.apps import apps
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from courses.tasks import sync_all_counters_task

logger = logging.getLogger(__name__)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _sync_lesson(lesson_id: int) -> None:
    """Dars vazifalarini va kurs counterlarini hisoblash taskini chaqiradi"""
    if lesson_id:
        sync_all_counters_task.delay(lesson_id=lesson_id)


def _sync_course(course_id: int) -> None:
    """Faqat kurs dars/test counterlarini hisoblash taskini chaqiradi"""
    if course_id:
        sync_all_counters_task.delay(course_id=course_id)


# ── Lesson ────────────────────────────────────────────────────────────────────

@receiver(post_save, sender='courses.Lesson')
def on_lesson_save(sender, instance, created, **kwargs):
    """Yangi dars qo'shilganda kurs counterini yangilash"""
    if created and instance.modul_id:
        # Lesson modul orqali o'z kursiga bog'langan, buni dars yaratilgandayoq taskga bersa bo'ladi
        course_id = instance.modul.course_id if instance.modul else None
        _sync_course(course_id)


@receiver(pre_delete, sender='courses.Lesson')
def on_lesson_delete(sender, instance, **kwargs):
    """Dars o'chirilishidan oldin (countdown bilan kechiktirib chaqiriladi)"""
    if instance.modul_id:
        course_id = instance.modul.course_id if instance.modul else None
        if course_id:
            sync_all_counters_task.apply_async(kwargs={'course_id': course_id}, countdown=1)


# ── Test ──────────────────────────────────────────────────────────────────────
@receiver(post_save, sender='quizs.Test')
def on_test_save(sender, instance, **kwargs):
    """
    Test qo'shilganda yoki o'zgarganda faqat taskni chaqiradi.
    Keshni o'chirishni Celery task o'z bo'yniga olgan.
    """
    if not instance.modul_id:
        return
        
    try:
        Modul = apps.get_model('courses', 'Modul')

        # Bitta yengil query orqali faqat course_id ni olamiz
        modul_data = (
            Modul.objects
            .filter(id=instance.modul_id)
            .values('course_id')
            .first()
        )
        
        if modul_data and modul_data['course_id']:
            # Taskni zudlik bilan fonda ishga tushiramiz
            sync_all_counters_task.delay(course_id=modul_data['course_id'])

    except Exception as e:
        logger.error(f"on_test_save xato: {e}", exc_info=True)


@receiver(pre_delete, sender='quizs.Test')
def on_test_delete(sender, instance, **kwargs):
    """
    Test o'chirilayotganda taskni 1 soniya kechiktirib chaqiradi.
    DB dan test to'liq o'chgach, Celery counterlarni to'g'rilab, keshni o'chiradi.
    """
    if not instance.modul_id:
        return
        
    try:
        Modul = apps.get_model('courses', 'Modul')

        modul_data = (
            Modul.objects
            .filter(id=instance.modul_id)
            .values('course_id')
            .first()
        )
        
        if modul_data and modul_data['course_id']:
            # countdown=1 orqali test o'chib bo'lishini kutamiz
            sync_all_counters_task.apply_async(
                kwargs={'course_id': modul_data['course_id']},
                countdown=1
            )

    except Exception as e:
        logger.warning(f"on_test_delete xato: {e}", exc_info=True)


# ── Problem ───────────────────────────────────────────────────────────────────

@receiver(post_save, sender='problems.Problem')
def on_problem_save(sender, instance, created, **kwargs):
    if created and instance.lesson_id:
        
        _sync_lesson(instance.lesson_id)


@receiver(post_delete, sender='problems.Problem')
def on_problem_delete(sender, instance, **kwargs):
    _sync_lesson(instance.lesson_id)


# ── Question ──────────────────────────────────────────────────────────────────

@receiver(post_save, sender='quizs.Question')
def on_question_save(sender, instance, created, **kwargs):
    if created and instance.lesson_id:
        _sync_lesson(instance.lesson_id)


@receiver(post_delete, sender='quizs.Question')
def on_question_delete(sender, instance, **kwargs):
    _sync_lesson(instance.lesson_id)


# ── Lecture ───────────────────────────────────────────────────────────────────

@receiver(post_save, sender='courses.Lecture')
def on_lecture_save(sender, instance, created, **kwargs):
    if created and instance.lesson_id:
        _sync_lesson(instance.lesson_id)


@receiver(post_delete, sender='courses.Lecture')
def on_lecture_delete(sender, instance, **kwargs):
    _sync_lesson(instance.lesson_id)

