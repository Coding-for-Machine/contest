from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from baseuser.models import BaseUser
from status.models import ProblemStatus
from status.services import (
    award_xp,
    mark_lesson_task_completed,
)

User = get_user_model()


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
        if problem.lesson_id:
                    mark_lesson_task_completed(
                        user_id=user_id,
                        lesson_id=problem.lesson_id,
                    )
        if problem_status.solved:
            return

        problem_status.solved = True
        problem_status.solved_at = timezone.now()
        problem_status.save(
            update_fields=[
                "solved",
                "solved_at",
            ]
        )

    try:
        user = BaseUser.objects.get(id=user_id)
    except:
        pass
    award_xp(
        user=user,
        xp_amount=problem.xp,
        source="problem_solved",
    )