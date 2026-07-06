import logging
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from courses.models import Enrollment, Course
from courses.cache import delete_course_user

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Enrollment)
def on_enrollment_save(sender, instance, **kwargs):
    """Foydalanuvchi kursni sotib olganda yoki to'lov holati o'zgarganda uning shaxsiy keshini o'chiradi"""
    if not (instance.course_id and instance.user_id):
        return
    try:
        # Faqat slug ustunini yengil SQL so'rov bilan yuklaymiz
        course = Course.objects.filter(id=instance.course_id).only('slug').first()
        if course and course.slug:
            delete_course_user(course.slug, instance.user_id)
    except Exception as e:
        logger.error(f"on_enrollment_save xato (course_id={instance.course_id}, user_id={instance.user_id}): {e}")


@receiver(pre_delete, sender=Enrollment)
def on_enrollment_delete(sender, instance, **kwargs):
    """Kursga a'zolik o'chirilganda foydalanuvchining shaxsiy keshini tozalaydi"""
    if not (instance.course_id and instance.user_id):
        return
    try:
        course = Course.objects.filter(id=instance.course_id).only('slug').first()
        if course and course.slug:
            delete_course_user(course.slug, instance.user_id)
    except Exception as e:
        logger.error(f"on_enrollment_delete xato (course_id={instance.course_id}, user_id={instance.user_id}): {e}")
