# submissions/tasks.py
import math
from celery import shared_task
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from status.models import UserStats, UserActivityDaily, LessonStatus
from courses.models import Enrollment
from problems.models import Problem


@shared_task
def submit_code_task():
    pass

@shared_task
def run_code_task():
    pass

@shared_task
def task_process_problem_submission(submission_id, user_id, problem_id, is_correct):
    """
    Xavfsiz Celery task: Masala qayerdan (Arxiv, Lesson yoki Contest) yechilganidan 
    qat'iy nazar xatosiz ishlaydi. Faqat mavjud bog'liqliklarni yangilaydi.
    """
    # Aylanma import (Circular Import) xatosini oldini olish
    from submissions.models import Submission

    with transaction.atomic():
        # 0. Masala obyektini bazadan olish (Faqat lesson yuklanadi, agar bo'lsa)
        try:
            problem = Problem.objects.select_related('lesson').get(id=problem_id)
        except Problem.DoesNotExist:
            return f"Xatolik: Problem {problem_id} topilmadi."

        # Submission obyektini bazadan olish
        try:
            submission = Submission.objects.get(id=submission_id)
        except Submission.DoesNotExist:
            return f"Xatolik: Submission {submission_id} topilmadi."

        # Foydalanuvchi bu masalani oldin ham to'g'ri yechganmi tekshiramiz (XP takrorlanmasligi uchun)
        should_give_xp = False
        if is_correct:
            previous_success = Submission.objects.filter(
                user_id=user_id,
                problem_id=problem_id,
                status=True
            ).exclude(pk=submission_id).exists()
            
            if not previous_success:
                should_give_xp = True

        # -----------------------------------------------------------------
        # 1. USER STATS (Global XP va Daraja) - DOIM ISHLAYDI (Arxiv holati uchun ham)
        # -----------------------------------------------------------------
        stats, _ = UserStats.objects.get_or_create(user_id=user_id)
        stats = UserStats.objects.select_for_update().get(pk=stats.pk)  # Row-level lock

        # Masalaning XP mukofotini xavfsiz olish
        problem_xp = getattr(problem, 'xp', 0) or 0

        if should_give_xp and problem_xp > 0:
            stats.xp += problem_xp
            stats.level = stats.compute_level()
            stats.save(update_fields=["xp", "level", "updated_at"])

        # -----------------------------------------------------------------
        # 2. USER ACTIVITY DAILY (GitHub Heatmap) - DOIM ISHLAYDI
        # -----------------------------------------------------------------
        today = timezone.now().date()
        activity, _ = UserActivityDaily.objects.get_or_create(user_id=user_id, date=today)
        
        if should_give_xp and problem_xp > 0:
            activity.xp_earned = F('xp_earned') + problem_xp
            
        activity.tasks_count = F('tasks_count') + 1
        
        # Vaqtni hisoblash (execution_time_ms yo'q bo'lsa 0 deb ketiladi)
        execution_time = getattr(submission, 'execution_time_ms', 0) or 0
        duration_mins = math.ceil(execution_time / 60000)
        activity.total_duration = F('total_duration') + duration_mins
        activity.save()

        # -----------------------------------------------------------------
        # 3. LESSON STATUS - FAQAT MASALA LESSON'GA BOG'LANGAN BO'LSA ISHLAYDI
        # -----------------------------------------------------------------
        lesson = getattr(problem, 'lesson', None)
        
        if should_give_xp and lesson is not None:
            lesson_status, _ = LessonStatus.objects.get_or_create(
                user_id=user_id,
                lesson_id=lesson.id
            )
            
            lesson_status.finished_tasks_count = F('finished_tasks_count') + 1
            lesson_status.save()
            lesson_status.refresh_from_db()  # Yangi qiymatni xotiraga yuklash
            
            # Lesson jami vazifalar sonini xavfsiz olish
            total_tasks = getattr(lesson, 'total_tasks_count', 0) or 0
            
            # Dars tugaganini tekshirish
            if total_tasks > 0 and lesson_status.finished_tasks_count >= total_tasks:
                if not lesson_status.is_completed:
                    lesson_status.is_completed = True
                    lesson_status.completed_at = timezone.now()
                    lesson_status.save(update_fields=['is_completed', 'completed_at'])

                    # -------------------------------------------------------------
                    # 4. ENROLLMENT (Kurs progressi) - ZANJIR XAVFSIZ BITTA-BITTA TEKSHIRILADI
                    # -------------------------------------------------------------
                    modul = getattr(lesson, 'modul', None)
                    course = getattr(modul, 'course', None) if modul else None
                    
                    if course is not None:
                        enrollment, _ = Enrollment.objects.get_or_create(
                            user_id=user_id,
                            course_id=course.id
                        )
                        
                        enrollment.finished_darslar_soni = F('finished_darslar_soni') + 1
                        enrollment.save()
                        enrollment.refresh_from_db()
                        
                        # Kurs jami darslar sonini xavfsiz olish
                        total_lessons = getattr(course, 'total_lessons_count', 0) or 0
                        
                        # Kurs to'liq tugaganini tekshirish
                        if total_lessons > 0 and enrollment.finished_darslar_soni >= total_lessons:
                            if not enrollment.is_completed:
                                enrollment.is_completed = True
                                enrollment.completed_at = timezone.now()
                                enrollment.save(update_fields=['is_completed', 'completed_at'])

        # -----------------------------------------------------------------
        # 5. CONTEST REGISTRATION - FAQAT MASALA CONTEST'GA BOG'LANGAN BO'LSA ISHLAYDI
        # -----------------------------------------------------------------
        contest_id = getattr(problem, 'contest_id', None)
        
        if contest_id is not None:
            # Dinamik import (agar boshqa appda bo'lsa xavfsiz bo'lishi uchun)
            from contests.models import ContestRegistration
            
            contest_reg = ContestRegistration.objects.filter(
                user_id=user_id,
                contest_id=contest_id,
                status=ContestRegistration.Status.IN_PROGRESS
            ).select_for_update().first()  # Faqat jarayondagi seans bloklanadi

            if contest_reg is not None:
                # Soniya sarfini hisoblash
                execution_time = getattr(submission, 'execution_time_ms', 0) or 0
                seconds_spent = math.ceil(execution_time / 1000)
                contest_reg.time_spent_seconds = F('time_spent_seconds') + seconds_spent

                if is_correct:
                    if should_give_xp:
                        contest_reg.correct_count = F('correct_count') + 1
                        contest_reg.total_xp_earned = F('total_xp_earned') + problem_xp
                else:
                    contest_reg.wrong_count = F('wrong_count') + 1
                
                contest_reg.save()

    return f"Submission {submission_id} muvaffaqiyatli yakunlandi."
