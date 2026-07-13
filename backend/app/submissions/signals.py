# submissions/signals.py
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Submission


@receiver(post_save, sender=Submission, dispatch_uid="submission_xp_award_v1")
def handle_problem_submission_reward(sender, instance, created, **kwargs):
    # Faqat yangi yaratilgan submissionlar uchun ishlaydi
    if not created:
        return
    
    # Tranzaksiya to'liq database-ga yozilib bo'lgandan keyin sinxron funksiyani chaqiramiz
    transaction.on_commit(lambda: _process_submission_statistics(instance.pk))


def _process_submission_statistics(submission_id: int):
    from status.models import UserStats
    from status.services import mark_lesson_task_completed
    from contests.models import ContestRegistration, Contest
    from problems.models import Problem

    # 1. Submission ma'lumotlarini bitta SQL so'rovda select_related orqali olamiz
    submission = Submission.objects.select_related("problem", "user").get(pk=submission_id)
    xp_amount = getattr(submission.problem, "xp", None) or 0

    # 2. Toza sinxron tranzaksiya va lock boshlanadi
    with transaction.atomic():
        
        # Foydalanuvchining global statistika qatorini qulflaymiz (Race-condition oldini olish uchun)
        UserStats.objects.select_for_update().get_or_create(user=submission.user)

        # Tekshiramiz: Foydalanuvchi ushbu masalani bundan oldin ham muvaffaqiyatli (True) yechganmi?
        has_previous_ac = (
            Submission.objects.filter(
                user_id=submission.user_id,
                problem_id=submission.problem_id,
                status=True,
            )
            .exclude(pk=submission.pk)
            .exists()
        )

        # ─── 🟢 GLOBAL XP QO'SHISH ───
        if submission.status is True and not has_previous_ac:
            # Global profiliga XP qo'shish (faqat birinchi marta to'g'ri yechganda)
            UserStats.add_xp(user=submission.user, xp_amount=xp_amount)

        # ─── 🏆 MUSOBAQA (CONTEST) NATIJALARINI TO'LIQ QAYTA HISOBLASH ───
        if submission.problem.contest_id:
            contest_id = submission.problem.contest_id
            user_id = submission.user_id

            # Musobaqadagi barcha masalalar ID ro'yxatini va jami sonini olamiz
            contest_problems = Problem.objects.filter(contest_id=contest_id)
            contest_problems_ids = list(contest_problems.values_list("id", flat=True))
            total_problems_count = len(contest_problems_ids)

            # Agar musobaqada hali masala yo'l bo'lsa, hisob-kitob qilmaymiz
            if total_problems_count == 0:
                return

            # Foydalanuvchining ushbu musobaqa masalalariga yuborgan barcha submission'larini filter qilamiz
            user_contest_submissions = Submission.objects.filter(
                user_id=user_id,
                problem_id__in=contest_problems_ids
            )

            # 🛠 AGGREGATION ORQALI ANIQLASH: Har bir masala uchun yechim holati
            # Har bir masala bo'yicha True va False submissionlar sonini bitta so'rovda hisoblaymiz
            problem_stats = user_contest_submissions.values('problem_id').annotate(
                has_true=Count('id', filter=Q(status=True)),
                has_false=Count('id', filter=Q(status=False))
            )

            # Natijalarni hisoblash uchun o'zgaruvchilar
            correct_count = 0
            wrong_count = 0
            total_xp_earned = 0

            # Yechim yuborilgan masalalar ro'yxatini shakllantiramiz
            attempted_problem_ids = set()

            for stat in problem_stats:
                p_id = stat['problem_id']
                attempted_problem_ids.add(p_id)

                if stat['has_true'] > 0:
                    # Agar masalada kamida bitta to'g'ri (True) yechim bo'lsa — bu TO'G'RI yechilgan
                    correct_count += 1
                    # Shu masalaning XP'sini topib umumiy ballga qo'shamiz
                    prob_xp = next((p.xp for p in contest_problems if p.id == p_id), 0) or 0
                    total_xp_earned += prob_xp
                elif stat['has_false'] > 0:
                    # Agar umuman True yechim bo'lmasa, lekin kamida bitta False bo'lsa — bu NOTO'G'RI yechilgan
                    wrong_count += 1

            # Mavjud bo'lmaganlar (Ushbu musobaqa ichida umuman submission yuborilmagan masalalar soni)
            unanswered_count = total_problems_count - len(attempted_problem_ids)

            # 🔒 Ishtirokchining shu musobaqadagi qatorini topamiz va qulflaymiz
            registration, created_reg = ContestRegistration.objects.select_for_update().get_or_create(
                user_id=user_id,
                contest_id=contest_id,
                defaults={
                    "status": ContestRegistration.Status.IN_PROGRESS,
                    "correct_count": correct_count,
                    "wrong_count": wrong_count,
                    "unanswered_count": unanswered_count,
                    "total_xp_earned": total_xp_earned,
                }
            )

            # Agar allaqachon mavjud bo'lsa, yangi hisoblangan aniq qiymatlarni shunchaki yozib qo'yamiz
            if not created_reg and registration.status == ContestRegistration.Status.IN_PROGRESS:
                registration.correct_count = correct_count
                registration.wrong_count = wrong_count
                registration.unanswered_count = unanswered_count
                registration.total_xp_earned = total_xp_earned
                registration.save(update_fields=["correct_count", "wrong_count", "unanswered_count", "total_xp_earned"])

    # 3. Agar darsga (Lesson) tegishli topshiriq bo'lsa va to'g'ri yechilgan bo'lsa, dars progressini yopamiz
    if submission.status is True and not has_previous_ac and submission.problem.lesson_id:
        mark_lesson_task_completed(user_id=submission.user_id, lesson_id=submission.problem.lesson_id)
