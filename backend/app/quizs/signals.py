import logging
from django.db import transaction
from django.db.models import F
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver

from .models import Question, UserResponse, Test

logger = logging.getLogger(__name__)


# ── TEST QUESTION COUNTER ───────────────────────────────────────────────

@receiver(pre_save, sender=Question, dispatch_uid="capture_old_test_id_v1")
def capture_old_test_id(sender, instance, **kwargs):
    if instance.id:
        try:
            instance._old_test_id = Question.objects.only("test_id").get(id=instance.id).test_id
        except Question.DoesNotExist:
            instance._old_test_id = None
    else:
        instance._old_test_id = None


@receiver(post_save, sender=Question, dispatch_uid="increment_question_count_v1")
def increment_question_count(sender, instance, created, **kwargs):
    if created and instance.test_id:
        with transaction.atomic():
            test = Test.objects.select_for_update().filter(id=instance.test_id).first()
            if test:
                test.question_count = F("question_count") + 1
                test.save(update_fields=["question_count"])
        return

    old_test_id = getattr(instance, "_old_test_id", None)
    if old_test_id == instance.test_id:
        return

    with transaction.atomic():
        if old_test_id:
            old_test = Test.objects.select_for_update().filter(id=old_test_id).first()
            if old_test and old_test.question_count > 0:
                old_test.question_count = F("question_count") - 1
                old_test.save(update_fields=["question_count"])
        if instance.test_id:
            new_test = Test.objects.select_for_update().filter(id=instance.test_id).first()
            if new_test:
                new_test.question_count = F("question_count") + 1
                new_test.save(update_fields=["question_count"])


@receiver(post_delete, sender=Question, dispatch_uid="decrement_question_count_v1")
def decrement_question_count(sender, instance, **kwargs):
    if not instance.test_id:
        return
    with transaction.atomic():
        test = Test.objects.select_for_update().filter(id=instance.test_id).first()
        if test and test.question_count > 0:
            test.question_count = F("question_count") - 1
            test.save(update_fields=["question_count"])


# ── DARS SAVOLIGA TO'G'RI JAVOB → XP ───────────────────────────────────

@receiver(post_save, sender=UserResponse, dispatch_uid="lesson_question_xp_v2")
def handle_user_response(sender, instance, created, **kwargs):
    if not created or not instance.choice_id or not instance.choice.is_correct:
        return

    transaction.on_commit(lambda pk=instance.pk: _award_question(pk))


def _award_question(response_id: int):
    from status.models import UserStats
    from status.services import mark_lesson_task_completed

    try:
        response = UserResponse.objects.select_related("user", "question", "choice").get(pk=response_id)
    except UserResponse.DoesNotExist:
        return

    question = response.question
    if not question.lesson_id:
        return

    with transaction.atomic():
        first_correct = not UserResponse.objects.filter(
            user_id=response.user_id,
            question_id=response.question_id,
            choice__is_correct=True,
        ).exclude(pk=response.pk).exists()

        if not first_correct:
            return

        if question.xp:
            UserStats.add_xp(user=response.user, xp_amount=question.xp)

        mark_lesson_task_completed(
            user_id=response.user_id,
            lesson_id=question.lesson_id,
        )