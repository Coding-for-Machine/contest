# certificates/tasks.py

import logging
from django.db import transaction

import qrcode
from celery import shared_task
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import F
from weasyprint import HTML

from courses.models import Enrollment
from status.models import LessonStatus, UserActivityDaily, UserStats

from .models import Question

logger = logging.getLogger(__name__)

@shared_task
def task_process_lesson_question(response_id, user_id, question_id, lesson_id, is_correct):
    """
    Celery task: Talaba dars ichidagi savolga to'g'ri javob berganida XP beradi,
    Heatmapni yangilaydi va dars/kurs progressini oshiradi.
    """
    from .models import UserResponse

    with transaction.atomic():
        try:
            question = Question.objects.select_related('lesson').get(id=question_id)
        except Question.DoesNotExist:
            return f"Xatolik: Question {question_id} topilmadi."

        should_give_xp = False
        if is_correct:
            # Foydalanuvchi bu dars savoliga oldin ham to'g'ri javob berganmi tekshiramiz
            previous_correct = UserResponse.objects.filter(
                user_id=user_id,
                question_id=question_id,
                choice__is_correct=True
            ).exclude(pk=response_id).exists()

            if not previous_correct:
                should_give_xp = True

        # 1. USER STATS (Global XP va Daraja)
        stats, _ = UserStats.objects.get_or_create(user_id=user_id)
        stats = UserStats.objects.select_for_update().get(pk=stats.pk)
        question_xp = getattr(question, 'xp', 0) or 0

        if should_give_xp and question_xp > 0:
            stats.xp += question_xp
            stats.level = stats.compute_level()
            stats.save(update_fields=["xp", "level", "updated_at"])

        # 2. USER ACTIVITY DAILY
        today = timezone.now().date()
        activity, _ = UserActivityDaily.objects.get_or_create(user_id=user_id, date=today)
        if should_give_xp and question_xp > 0:
            activity.xp_earned = F('xp_earned') + question_xp
        activity.tasks_count = F('tasks_count') + 1  # Kalendarda faollik katakchasi doim +1 oshadi
        activity.save()

        # 3. LESSON STATUS VA ENROLLMENT
        lesson = question.lesson
        if should_give_xp and lesson is not None:
            lesson_status, _ = LessonStatus.objects.get_or_create(user_id=user_id, lesson_id=lesson_id)
            lesson_status.finished_tasks_count = F('finished_tasks_count') + 1
            lesson_status.save()
            lesson_status.refresh_from_db()

            total_tasks = getattr(lesson, 'total_tasks_count', 0) or 0

            # Dars to'liq tugaganini tekshirish
            if total_tasks > 0 and lesson_status.finished_tasks_count >= total_tasks:
                if not lesson_status.is_completed:
                    lesson_status.is_completed = True
                    lesson_status.completed_at = timezone.now()
                    lesson_status.save(update_fields=['is_completed', 'completed_at'])

                    # 4. Enrollment (Kurs progressi)
                    modul = getattr(lesson, 'modul', None)
                    course = getattr(modul, 'course', None) if modul else None
                    
                    if course is not None:
                        enrollment, _ = Enrollment.objects.get_or_create(user_id=user_id, course_id=course.id)
                        enrollment.finished_darslar_soni = F('finished_darslar_soni') + 1
                        enrollment.save()
                        enrollment.refresh_from_db()

                        total_lessons = getattr(course, 'total_lessons_count', 0) or 0
                        if total_lessons > 0 and enrollment.finished_darslar_soni >= total_lessons:
                            if not enrollment.is_completed:
                                enrollment.is_completed = True
                                enrollment.completed_at = timezone.now()
                                enrollment.save(update_fields=['is_completed', 'completed_at'])

    return f"Lesson response {response_id} processed."