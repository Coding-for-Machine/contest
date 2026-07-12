# apps/status/signals/lesson_status.py
import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.apps import apps
from django.utils import timezone

from courses.cache import invalidate_user


# ── 1. GRADUATION (KURSNI TAMOMLASH VA SERTIFIKAT BERISH) ────────────────────

def _check_graduation(enrollment, total_lessons: int, total_tests: int, update_fields: dict):
    """
    Talabaning jami unikal progressini kurs tarkibidagi jami darslar va testlar 
    soni bilan solishtiradi. Agar 100% bajarilgan bo'lsa:
    1. Kursni yakunlaydi (is_completed=True).
    2. Avtomat unikal Certificate ob'ektini 'pending' statusida yaratadi.
    """
    finished_lessons = update_fields.get('finished_darslar_soni', enrollment.finished_darslar_soni)
    finished_tests = update_fields.get('finished_test_soni', enrollment.finished_test_soni)

    # Hisoblagich jami kurs kontenti sonidan oshib ketmasligini ta'minlash (Guard)
    if finished_lessons > total_lessons:
        finished_lessons = total_lessons
        update_fields['finished_darslar_soni'] = total_lessons

    if finished_tests > total_tests:
        finished_tests = total_tests
        update_fields['finished_test_soni'] = total_tests

    # Kurs to'liq bitganligini aniqlash sharti
    is_now_completed = (finished_lessons >= total_lessons and finished_tests >= total_tests)

    if is_now_completed and not enrollment.is_completed:
        update_fields['is_completed'] = True
        update_fields['completed_at'] = timezone.now()

        # 🎓 AVTOMAT SERTIFIKAT YARATISH TIZIMI
        try:
            Certificate = apps.get_model('courses', 'Certificate')
            
            # Takroriy (dublikat) sertifikat yaratilishidan himoya
            exists = Certificate.objects.filter(user_id=enrollment.user_id, course_id=enrollment.course_id).exists()
            if not exists:
                # Modeldagi save() metodi unikal kodni avtomat generatsiya qiladi (shuning uchun bu yerda ixtiyoriy)
                Certificate.objects.create(
                    user_id=enrollment.user_id,
                    course_id=enrollment.course_id,
                    status='pending'  # Dastlabki kutilmoqda holati
                )
                # Diqqat: Certificate modelining o'zidagi save() metodi orqali 
                # transaction.on_commit triggeri ishlab, Celery taskni avtomat fonga yuboradi!
        except Exception:
            pass

    elif not is_now_completed and enrollment.is_completed:
        update_fields['is_completed'] = False
        update_fields['completed_at'] = None


# ── 2. PROGRES HISOBLASHNING ASIL ICHKI MANTIQI ───────────────────────────────

def run_lesson_progress_calculation(user_id: int, lesson_id: int):
    """
    Baza kommit bo'lgandan keyin ishlaydigan asil mantiq.
    Faqat indekslangan ustunlar ustida tezkor SQL bajaradi.
    """
    try:
        LessonStatus = apps.get_model('status', 'LessonStatus')
        Course = apps.get_model('courses', 'Course')
        Enrollment = apps.get_model('courses', 'Enrollment')

        # A. Dars orqali Kurs ID va kesh parametrlarini bitta queryda yuklaymiz
        course_data = (
            Course.objects
            .filter(modullar__lessons__id=lesson_id)
            .values('id', 'slug', 'total_lessons_count', 'total_test_count')
            .first()
        )
        if not course_data:
            return

        course_id = course_data['id']
        course_slug = course_data['slug']

        # B. Talabaning Enrollment a'zoligini tekshiramiz
        enrollment = Enrollment.objects.filter(user_id=user_id, course_id=course_id).first()
        if not enrollment:
            return

        # C. DUBILKATSIYADAN HIMOYa: Kursga tegishli jami unikal bitirilgan darslar soni
        finished_lessons = LessonStatus.objects.filter(
            user_id=user_id,
            is_completed=True,
            lesson__modul__course_id=course_id,
        ).count()

        update_fields = {'finished_darslar_soni': finished_lessons}

        # Kurs bitganligini va sertifikatni tekshirish
        _check_graduation(
            enrollment,
            course_data['total_lessons_count'],
            course_data['total_test_count'],
            update_fields,
        )

        # SQL darajasida yagona va xavfsiz UPDATE
        Enrollment.objects.filter(id=enrollment.id).update(**update_fields)

        # Foydalanuvchining dars keshini o'chirish
        if course_slug:
            invalidate_user(course_slug, user_id)

    except Exception:
        pass


# ── 3. MAIN TRIGGER SIGNAL ───────────────────────────────────────────────────

@receiver(post_save, sender='status.LessonStatus')
def on_lesson_status_save(sender, instance, created, **kwargs):
    """Foydalanuvchi ma'ruzani bitirganda tranzaksiya tugashini kutib progressni yangilaydi."""
    if not instance.is_completed:
        return
        
    if not (instance.user_id and instance.lesson_id):
        return

    # TIMING PROTECTION: Parametrlarni xavfsiz holatda tranzaksiya tugash nuqtasiga yetkazib beradi
    transaction.on_commit(
        lambda u_id=instance.user_id, l_id=instance.lesson_id: run_lesson_progress_calculation(u_id, l_id)
    )

from status.models import LectureStatus

@receiver(post_save, sender=LectureStatus)
def lecture_xp_add(sender, instance, created, **kwargs):
     if not created or not instance.is_completed:
        return
     transaction.on_commit(lambda: _award_lecture_xp(instance.pk))

def _award_lecture_xp(status_id: int):
    from status.models import UserStats

    ls = LectureStatus.objects.select_related("lecture", "user").get(pk=status_id)
    UserStats.add_xp(user=ls.user, xp_amount=ls.lecture.xp)
