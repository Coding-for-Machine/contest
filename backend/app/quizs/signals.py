# quiz/signals.py
from django.db import transaction
from django.db.models import F
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from status.models import LessonStatus, UserStats
from .models import Question, UserResponse, Test


@receiver(post_save, sender=Question)
def increment_question_count(sender, instance, created, **kwargs):
    """Savol qo'shilganda yoki tahrirlanganda Test modelidagi question_count

    hisoblagichini poyga holatlaridan (race condition) himoyalangan holda yangilaydi.
    """
    if created:
        # 1. Yangi savol muvaffaqiyatli kiritilgandan keyin unga tegishli test counterini oshiramiz
        if instance.test_id:
            # select_for_update() va transaction.atomic() parallel so'rovlarda
            # bir vaqtda counter urilishini navbatga qo'yadi (Atomiklikni ta'minlaydi)
            with transaction.atomic():
                test = Test.objects.select_for_update().filter(id=instance.test_id).first()
                if test:
                    test.question_count = F("question_count") + 1
                    test.save(update_fields=["question_count"])
    else:
        # 2. Mavjud savol tahrirlanib, uning Testi boshqasiga o'zgartirilsa (Xavfsizlik chorasi)
        # Savolning aynan o'zgarishdan oldingi holatini bazadan toza olamiz
        old_instance = Question.objects.filter(id=instance.id).first()
        
        if old_instance and old_instance.test_id != instance.test_id:
            with transaction.atomic():
                # Eski biriktirilgan testdan 1 ta ayiramiz (0 dan pastga tushib ketmasligini tekshirib)
                if old_instance.test_id:
                    old_test = Test.objects.select_for_update().filter(id=old_instance.test_id).first()
                    if old_test and old_test.question_count > 0:
                        old_test.question_count = F("question_count") - 1
                        old_test.save(update_fields=["question_count"])
                        
                # Yangi biriktirilgan testga 1 ta qo'shamiz
                if instance.test_id:
                    new_test = Test.objects.select_for_update().filter(id=instance.test_id).first()
                    if new_test:
                        new_test.question_count = F("question_count") + 1
                        new_test.save(update_fields=["question_count"])


@receiver(post_delete, sender=Question)
def decrement_question_count(sender, instance, **kwargs):
    """Savol o'chirilganda test ichidagi savollar soni minusga tushib ketmasligini

    ta'minlagan holda counterdan 1 tani xavfsiz kamaytiradi.
    """
    if instance.test_id:
        with transaction.atomic():
            # select_for_update qatorni o'chirish jarayonida bazani bloklab turadi
            test = Test.objects.select_for_update().filter(id=instance.test_id).first()
            if test and test.question_count > 0:
                test.question_count = F("question_count") - 1
                test.save(update_fields=["question_count"])

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
                # 1. Darsdagi bajarilgan vazifalar sonini bazada xavfsiz tarzda 1 taga oshiramiz
                # select_for_update() bu yerda ham poyga (race condition) holatlarini oldini oladi
                lesson_status, status_created = (
                    LessonStatus.objects.select_for_update().get_or_create(
                        user_id=instance.user_id,
                        lesson_id=lesson_id,
                        defaults={"finished_tasks_count": 1},  # Birinchi marta ochilsa boshlang'ich qiymat 1
                    )
                )

                # Agar dars holati bazada allaqachon mavjud bo'lgan bo'lsa, counterga F() qo'shib yangilaymiz
                if not status_created:
                    lesson_status.finished_tasks_count = F("finished_tasks_count") + 1
                    lesson_status.save(update_fields=["finished_tasks_count"])

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
