# submissions/signals.py
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Submission


@receiver(post_save, sender=Submission, dispatch_uid="submission_xp_award_v1")
def handle_problem_submission_reward(sender, instance, created, **kwargs):
    if not created or not instance.status:
        return
    transaction.on_commit(lambda pk=instance.pk: _try_award_submission_xp(pk))


def _try_award_submission_xp(submission_id: int):
    from status.models import UserStats
    from status.services import mark_lesson_task_completed

    submission = Submission.objects.select_related("problem", "user").get(pk=submission_id)
    xp_amount = getattr(submission.problem, "xp", None) or 0
    if xp_amount <= 0:
        return

    with transaction.atomic():
        # 🔒 KALIT QADAM: UserStats qatorini AVVAL bloklaymiz.
        # Shu foydalanuvchi uchun boshqa parallel signal handler'lar
        # shu yerda navbatga turadi — natijada quyidagi tekshiruv
        # ketma-ket (serial) bajariladi, race-condition bo'lmaydi.
        UserStats.objects.select_for_update().get_or_create(user=submission.user)

        has_previous_ac = (
            Submission.objects.filter(
                user_id=submission.user_id,
                problem_id=submission.problem_id,
                status=True,
            )
            .exclude(pk=submission.pk)
            .exists()
        )
        if has_previous_ac:
            return  # bu masala uchun XP allaqachon berilgan

        UserStats.add_xp(user=submission.user, xp_amount=xp_amount)

    if submission.problem.lesson_id:
        mark_lesson_task_completed(user_id=submission.user_id, lesson_id=submission.problem.lesson_id)