# apps/courses/signals/lesson.py
from django.db.models import F
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from courses.models import Course, Lesson
from courses.cache import invalidate_static


@receiver(post_save, sender=Lesson)
def on_lesson_save(sender, instance, created, **kwargs):
    """Dars qo'shilganda yoki tahrirlanganda Kurs hisoblagichini yangilaydi va keshni o'chiradi."""
    if not instance.modul_id:
        return
    try:
        # Bitta engil query orqali ham Kurs ID sini, ham Slugini aniqlaymiz (JOIN larsiz)
        course_data = Course.objects.filter(modullar__id=instance.modul_id).values("id", "slug").first()
        if not course_data:
            return

        course_id = course_data["id"]
        course_slug = course_data["slug"]

        if created:
            Course.objects.filter(id=course_id).update(
                total_lessons_count=F('total_lessons_count') + 1
            )

        if course_slug:
            invalidate_static(course_slug)
    except Exception:
        pass


@receiver(pre_delete, sender=Lesson)
def on_lesson_delete(sender, instance, **kwargs):
    """Dars o'chirilishidan oldin Kurs hisoblagichini kamaytiradi va keshni o'chiradi (Kaskadga chidamli)."""
    if not instance.modul_id:
        return
    try:
        course_data = Course.objects.filter(modullar__id=instance.modul_id).values("id", "slug").first()
        if not course_data:
            return

        course_id = course_data["id"]
        course_slug = course_data["slug"]

        Course.objects.filter(id=course_id, total_lessons_count__gt=0).update(
            total_lessons_count=F('total_lessons_count') - 1
        )

        if course_slug:
            invalidate_static(course_slug)
    except Exception:
        pass
