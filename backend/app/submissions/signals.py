# submissions/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from status.models import UserStats, LessonStatus
from submissions.models import Submission
from contests.models import ContestRegistration


@receiver(post_save, sender=Submission)
def handle_problem_submission_reward(sender, instance, created, **kwargs):
    if created and instance.status==True:
        
        has_previous_accepted = (
            Submission.objects.filter(
                user=instance.user,
                problem = instance.problem,
                status=True
            ).exists()
        )
        if has_previous_accepted:
            return
        duration_mins = getattr(instance, "execution_time_ms", 0)
        UserStats.add_xp(
            user=instance.user,
            xp_amount=instance.problem.px,
            duration_mins=(duration_mins/60)*10,
        )
        if instance.contest:
            ContestRegistration.objects.get(contest=instance.contest, user=instance.user)
            pass
        if instance.lesson:
            LessonStatus.objects.update_or_create(
                
            )
            # finished_tasks_count add
            pass