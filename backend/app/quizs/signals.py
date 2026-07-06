# quiz/signals.py
import os

from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

from .models import Question, UserResponse
from status.models import UserStats, LessonStatus

@receiver(post_save, sender=UserResponse)
def handle_user_response(sender, instance, created, **kwargs):
    """Talaba dars savoliga birinchi marta to'g'ri javob berganida dars counterini oshiradi

    va unga faqat bir marta ball (XP) beradi. Qayta javob berilganda (yangi row
    yaratilganda) dublikat ball berishni to'liq bloklaydi.
    """
    # Faqat yangi javob yozilganda (yangi row qo'shilganda) ishlaydi
    if not created:
        return

    # Savolning darsga tegishli ekanligi va uning bazaviy ballini (xp) bitta so'rovda olamiz
    question_data = (
        Question.objects.filter(id=instance.question_id)
        .values("lesson_id", "xp")
        .first()
    )

    if not question_data:
        return

    lesson_id = question_data.get("lesson_id")
    question_xp = question_data.get("xp") or 0

    # Hozirgi berilgan javob Choice modeli bo'yicha to'g'riligini tekshiramiz
    is_current_correct = (
        instance.choice.is_correct if instance.choice else False
    )

    # AGAR SAVOL DARSLIKKA TEGISHLI BO'LSA VA HOZIRGI JAVOB TO'G'RI BO'LSA
    if lesson_id and is_current_correct:

        # Foydalanuvchi aynan shu savolga ESKI JAVOBLARI ICHIDA to'g'ri javob berganmi?
        already_solved_correctly = (
            UserResponse.objects.filter(
                user_id=instance.user_id,
                question_id=instance.question_id,
                choice__is_correct=True,
            )
            .exclude(id=instance.id)  # Hozirgi yangi yaratilgan javobni hisobga olmaymiz
            .exists()
        )

        # Agar talaba bu savolni o'tmishda umuman to'g'ri topmagan bo'lsa (bu birinchi to'g'ri javob bo'lsa):
        if not already_solved_correctly:
            with transaction.atomic():
                # 1. Darsdagi bajarilgan vazifalar sonini bazada 1 taga oshiramiz
                LessonStatus.objects.update_or_create(
                    user_id=instance.user_id,
                    lesson_id=lesson_id,
                    defaults={
                        "finished_tasks_count": F("finished_tasks_count") + 1
                    },
                )

                # 2. Foydalanuvchining global profiliga savolning XP ballini qo'shamiz
                if question_xp > 0:
                    # select_for_update() poyga holatida ballar ko'payib ketishini bloklaydi
                    stats, _ = (
                        UserStats.objects.select_for_update().get_or_create(
                            user_id=instance.user_id
                        )
                    )
                    stats.xp += question_xp
                    stats.level = stats.compute_level()
                    stats.save(update_fields=["xp", "level", "updated_at"])
