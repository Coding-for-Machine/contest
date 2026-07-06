from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from courses.models import Course
from courses.cache import delete_course_list_static, delete_course_static


@receiver(post_save, sender=Course)
def on_course_save(sender, instance, **kwargs):
    delete_course_list_static()
    if instance.slug:
        delete_course_static(instance.slug)


@receiver(pre_delete, sender=Course)
def on_course_delete(sender, instance, **kwargs):
    delete_course_list_static()
    if instance.slug:
        delete_course_static(instance.slug)
