from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import Submission, LessonStatus
from status.models import UserStats # UserStats qayerda bo'lsa o'sha yo'l

@receiver(post_save, sender=Submission)
def handle_submission_reward(sender, instance, created, **kwargs):
    """
    Submission saqlanganda XP berish va LessonStatusni yangilash
    """
    # Faqat yangi yaratilganda va holati 'True' (Accepted) bo'lganda ishlaydi
    if created and instance.status is True:
        with transaction.atomic():
            # 1. Foydalanuvchi bu masalani oldin yechganmi tekshiramiz (XP takrorlanmasligi uchun)
            previous_success = Submission.objects.filter(
                user=instance.user, 
                problem=instance.problem, 
                status=True
            ).exclude(pk=instance.pk).exists()

            if not previous_success:
                # 2. UserStats-ni yangilash
                stats, _ = UserStats.objects.get_or_create(user=instance.user)
                
                # Problem modelidagi difficulty (1,2,3,4) va points ishlatiladi
                stats.add_progress(
                    difficulty=instance.problem.difficulty,
                    score_earned=instance.problem.points,
                    duration_mins=0 # Agar submissionda vaqt bo'lsa shuni yuboring
                )

                # 3. LessonStatus-ni yangilash (Dars ichidagi masalalar progressi)
                if instance.problem.lesson:
                    lesson_status, _ = LessonStatus.objects.get_or_create(
                        user=instance.user,
                        lesson=instance.problem.lesson
                    )
                    lesson_status.problems.add(instance.problem)

