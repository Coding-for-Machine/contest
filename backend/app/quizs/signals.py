from django.db import transaction
from django.db.models import F
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver

from .models import Question, UserResponse, Test


# ── QUESTION COUNTER (Test.question_count) ──────────────────────────────────

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
    if created:
        if instance.test_id:
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


# ── DARSLIK SAVOLIGA TO'G'RI JAVOB → XP (faqat lesson_id bor savollar) ──────

@receiver(post_save, sender=UserResponse, dispatch_uid="userresponse_lesson_xp_v1")
def handle_user_response(sender, instance, created, **kwargs):
    if not created:
        return
    is_correct = instance.choice.is_correct if instance.choice_id and instance.choice else False
    if not is_correct:
        return
    transaction.on_commit(lambda pk=instance.pk: _try_award_question_xp(pk))


def _try_award_question_xp(response_id: int):
    from status.models import UserStats
    from status.services import mark_lesson_task_completed

    response = UserResponse.objects.select_related("user", "question", "choice").get(pk=response_id)
    if not (response.choice and response.choice.is_correct):
        return

    question = response.question
    lesson_id = question.lesson_id
    if not lesson_id:
        return  # Test savoli — XP TestSession.calculate_mathematical_score() orqali beriladi

    question_xp = question.xp or 0

    with transaction.atomic():
        UserStats.objects.select_for_update().get_or_create(user_id=response.user_id)

        already_solved = (
            UserResponse.objects.filter(
                user_id=response.user_id, question_id=response.question_id, choice__is_correct=True,
            ).exclude(id=response.id).exists()
        )
        if already_solved:
            return

        if question_xp > 0:
            UserStats.add_xp(user=response.user, xp_amount=question_xp)

    mark_lesson_task_completed(user_id=response.user_id, lesson_id=lesson_id)