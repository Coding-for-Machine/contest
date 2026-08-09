from django.db import transaction
from django.utils import timezone

from status.models import ProblemStatus
from status.services import (
    award_xp,
    mark_lesson_task_completed,
)

def handle_accepted_submission(user_id, problem):
    with transaction.atomic():
        problem_status, created = (
            ProblemStatus.objects
            .select_for_update()
            .get_or_create(
                user_id=user_id,
                problem=problem,
                defaults={
                    "solved": False,
                }
            )
        )

        # Oldin yechilgan bo'lsa XP bermaymiz
        if problem_status.solved:
            return


        problem_status.solved = True
        problem_status.completed_at = timezone.now()
        problem_status.save(
            update_fields=[
                "solved",
                "completed_at",
            ]
        )


    # XP faqat birinchi AC uchun
    award_xp(
        user_id,
        problem.xp,
        source="problem_solved",
    )


    # Lesson -> Module -> Course chain
    if problem.lesson_id:
        mark_lesson_task_completed(
            user_id=user_id,
            lesson_id=problem.lesson_id,
        )