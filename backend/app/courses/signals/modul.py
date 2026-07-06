import logging
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from courses.models import Modul, Course
from courses.cache import delete_course_static

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Modul)
def on_modul_save(sender, instance, **kwargs):
    """Modul nomi yoki tartibi o'zgarganda tegishli kurs keshini o'chiradi"""
    if not instance.course_id:
        return
    try:
        # Og'ir helperlarsiz, bazadan faqat kerakli slug ustunini yengil SQL so'rov bilan olamiz
        course = Course.objects.filter(id=instance.course_id).only('slug').first()
        if course and course.slug:
            delete_course_static(course.slug)
    except Exception as e:
        logger.error(f"on_modul_save xato (course_id={instance.course_id}): {e}")


@receiver(pre_delete, sender=Modul)
def on_modul_delete(sender, instance, **kwargs):
    """Modul o'chirilishidan oldin kurs keshini tozalaydi"""
    if not instance.course_id:
        return
    try:
        course = Course.objects.filter(id=instance.course_id).only('slug').first()
        if course and course.slug:
            delete_course_static(course.slug)
    except Exception as e:
        logger.error(f"on_modul_delete xato (course_id={instance.course_id}): {e}")
