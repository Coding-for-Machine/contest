from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction


@receiver(post_save, sender='status.LectureStatus', dispatch_uid="lecture_xp_award_v1")
def award_lecture_xp(sender, instance, created, **kwargs):
    if not created or not instance.is_completed:
        return
    transaction.on_commit(lambda pk=instance.pk: _do_award(pk))


def _do_award(lecture_status_id: int):
    from status.models import LectureStatus, UserStats
    from status.services import mark_lesson_task_completed

    ls = LectureStatus.objects.select_related("lecture", "user").get(pk=lecture_status_id)
    UserStats.add_xp(user=ls.user, xp_amount=ls.lecture.xp)

    if ls.lecture.lesson_id:
        mark_lesson_task_completed(user_id=ls.user_id, lesson_id=ls.lecture.lesson_id)