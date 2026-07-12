from django.db import transaction
from django.db.models import F
from django.utils import timezone


def mark_lesson_task_completed(user_id: int, lesson_id: int) -> None:
    """
    Lesson ichidagi istalgan vazifa turi (Problem, Question, Lecture) foydalanuvchi
    tomonidan BIRINCHI MARTA yakunlanganida chaqiriladi. Chaqiruvchi signal
    "bu chindan ham birinchi marta"ligini tekshirgan bo'lishi SHART.
    """
    from status.models import LessonStatus
    from courses.models import Lesson

    with transaction.atomic():
        lesson_status, created = LessonStatus.objects.select_for_update().get_or_create(
            user_id=user_id, lesson_id=lesson_id,
            defaults={"finished_tasks_count": 1},
        )
        if not created:
            lesson_status.finished_tasks_count = F("finished_tasks_count") + 1
            lesson_status.save(update_fields=["finished_tasks_count"])
            lesson_status.refresh_from_db(fields=["finished_tasks_count"])

        if lesson_status.is_completed:
            return

        total_tasks = (
            Lesson.objects.filter(id=lesson_id)
            .values_list("total_tasks_count", flat=True)
            .first() or 0
        )

        if total_tasks > 0 and lesson_status.finished_tasks_count >= total_tasks:
            lesson_status.is_completed = True
            lesson_status.completed_at = timezone.now()
            lesson_status.save(update_fields=["is_completed", "completed_at"])
            # is_completed=True save() → courses/signals/progress.py dagi
            # on_lesson_status_save signalini ishga tushiradi (Enrollment/Certificate)