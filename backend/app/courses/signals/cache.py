import logging
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from courses.models import Course, Enrollment
from courses.cache import delete_course_list_static, delete_course_static, delete_course_user

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Course, dispatch_uid="cache_course_save_v1")
def on_course_save(sender, instance, **kwargs):
    delete_course_list_static()
    if instance.slug:
        delete_course_static(instance.slug)


@receiver(pre_delete, sender=Course, dispatch_uid="cache_course_delete_v1")
def on_course_delete(sender, instance, **kwargs):
    delete_course_list_static()
    if instance.slug:
        delete_course_static(instance.slug)


@receiver(post_save, sender=Enrollment, dispatch_uid="cache_enrollment_save_v1")
def on_enrollment_save(sender, instance, **kwargs):
    if not (instance.course_id and instance.user_id):
        return
    try:
        course = Course.objects.filter(id=instance.course_id).only("slug").first()
        if course and course.slug:
            delete_course_user(course.slug, instance.user_id)
    except Exception as e:
        logger.error(f"on_enrollment_save xato: {e}", exc_info=True)


@receiver(pre_delete, sender=Enrollment, dispatch_uid="cache_enrollment_delete_v1")
def on_enrollment_delete(sender, instance, **kwargs):
    if not (instance.course_id and instance.user_id):
        return
    try:
        course = Course.objects.filter(id=instance.course_id).only("slug").first()
        if course and course.slug:
            delete_course_user(course.slug, instance.user_id)
    except Exception as e:
        logger.error(f"on_enrollment_delete xato: {e}", exc_info=True)