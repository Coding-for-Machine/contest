from django.db import IntegrityError, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from submissions.models import Submission

@receiver(post_save, sender=Submission, dispatch_uid="submission_xp_award_v5")
def handle_problem_submission_reward(sender, instance, created, **kwargs):
    # Faqat status=True (Hamma testdan o'tgan) bo'lsa mantiq ishlaydi
    if not instance.status:
        return

    # Tranzaksiya to'liq muvaffaqiyatli yakunlangach (commit), XP berish funksiyasini chaqiramiz
    transaction.on_commit(lambda pk=instance.pk: _try_award_submission_xp(pk))


def _try_award_submission_xp(submission_id: int):
    from status.models import UserStats

    try:
        with transaction.atomic():
            submission = Submission.objects.select_for_update().select_related("problem", "user").get(pk=submission_id)
            
            problem = submission.problem
            xp_amount = getattr(problem, "xp", None) or problem.DEFAULT_XP_BY_DIFFICULTY.get(problem.difficulty, 0)
            
            if xp_amount <= 0:
                return

            # ENG ASOSIY SHART: Foydalanuvchining shu masala bo'yicha boshqa Accepted yechimlari bormi?
            # .exclude(pk=submission.pk) yordamida joriy tekshirilayotgan yechimni hisobdan chiqarib tashlaymiz.
            has_prior_accepted = Submission.objects.filter(
                user=submission.user,
                problem=submission.problem,
                status=True
            ).exclude(pk=submission.pk).exists()

            # Agar boshqa to'g'ri yechim topilsa, demak foydalanuvchi allaqachon XP olgan. Funksiyadan chiqamiz.
            if has_prior_accepted:
                return

            # Agar bu eng birinchi muvaffaqiyatli yechim bo'lsa, foydalanuvchiga XP beramiz
            UserStats.add_xp(user=submission.user, xp_amount=xp_amount)
            
    except (Submission.DoesNotExist, IntegrityError):
        return
