# contests/models.py ga qo'shish kerak bo'lgan constraint (misol):
#
# class ContestRegistration(models.Model):
#     ...
#     xp_awarded = models.PositiveIntegerField(default=0)
#     status = models.CharField(...)  # COMPLETED holatini o'z ichiga olgan
#
#     class Meta:
#         constraints = [
#             models.UniqueConstraint(
#                 fields=["user", "contest"],
#                 condition=models.Q(xp_awarded__gt=0),
#                 name="unique_xp_award_per_user_contest",
#             )
#         ]

from django.db import IntegrityError, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from contests.models import ContestRegistration


@receiver(post_save, sender=ContestRegistration, dispatch_uid="contest_xp_award_v1")
def handle_contest_completion_reward(sender, instance, created, **kwargs):
    if instance.status != "completed":
        return
    transaction.on_commit(lambda pk=instance.pk: _try_award_contest_xp(pk))


def _try_award_contest_xp(registration_id: int):
    from status.models import UserStats

    reg = ContestRegistration.objects.select_related("contest", "user").get(pk=registration_id)
    xp_amount = getattr(reg.contest, "xp", None) or 0
    if xp_amount <= 0:
        return

    try:
        with transaction.atomic():
            reg.xp_awarded = xp_amount
            reg.save(update_fields=["xp_awarded"])
    except IntegrityError:
        return

    UserStats.add_xp(user=reg.user, xp_amount=xp_amount)