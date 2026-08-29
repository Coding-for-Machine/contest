# status/services.py
"""
Platformadagi BARCHA progress, XP va sertifikat logikasining
YAGONA markazlashtirilgan manbai.

Qoidalar:
    1. Progress uchun yagona haqiqat manbai: LessonStatus / ModuleStatus / CourseStatus.
       Bu uchala model quyidagi maydonlarga EGA EMAS: "progress" (faqat LessonStatus'da bor),
       "last_activity", "updated_at", "created_at". Shu sabab bu fayldagi barcha
       save(update_fields=[...]) chaqiruvlari faqat haqiqatda mavjud maydonlarni ko'rsatadi.
    2. Race-condition mumkin bo'lgan joylarda select_for_update() ishlatiladi —
       hech qachon "o'qi -> tekshir -> yoz" qilinmaydi.
    3. Bu fayldagi barcha funksiyalar SINXRON. Async chaqiruvchi kod
       (courses/api.py) buni sync_to_async() bilan o'raydi.
    4. XP faqat award_xp() orqali beriladi — boshqa hech qanday joyda
       UserStats.xp ga to'g'ridan-to'g'ri yozilmasin.

    !!! MUHIM TUZATISH (bu versiyada) !!!
    Loyihada ALOHIDA "quizs" app YO'Q — savollar, javoblar va test seanslari
    barchasi "courses" appida joylashgan:
        - Savol modeli:        courses.CourseQuestion   (avval: quizs.Question)
        - Javob modeli:        courses.CourseUserResponse (avval: quizs.UserResponse)
        - Test seansi modeli:  courses.CourseTestSession  (avval: quizs.TestSession)
        - Test modeli:         courses.CourseTest         (avval: quizs.Test)
    Bundan tashqari:
        - Lesson'dan savollarga reverse nom "questions" ("quiz_questions" EMAS).
        - CourseTest -> Modul bog'lanishi OneToOneField (related_name="test"),
          ya'ni "modul.tests" (ko'plik) mavjud emas — "modul.test" (birlik) bor,
          shu sababli ro'yxat/queryset kerak bo'lganda to'g'ridan-to'g'ri
          CourseTest.objects.filter(modul_id=...) ishlatiladi.
        - CourseTestSession'da "status" maydoni YO'Q — tugallanganlikni
          "completed_at__isnull=False" orqali tekshirish kerak
          (avvalgi kodda TestSession.Status.COMPLETED ishlatilgan, bu FieldError beradi).

    !!! MUHIM TUZATISH #2 (bu versiyada) !!!
    recalculate_module_status() ichida CourseStatus'ga cascade qilish sharti
    noto'g'ri edi: avval faqat "modul to'liq tugallanganda" (just_completed)
    recalculate_course_status() chaqirilardi. Lekin CourseStatus.completed_lessons/
    completed_tests/completed_problems — bu butun kurs bo'yicha real vaqtli
    (LessonStatus/CourseTestSession/ProblemStatus'dan to'liq qayta hisoblanadigan)
    sonlar, ular modulning har qanday ichki o'zgarishida (masalan, bitta dars
    yangi tugallanganda, modulning o'zi hali to'liq tugamagan bo'lsa ham)
    o'zgarishi kerak. Shu sabab CourseStatus deyarli yangilanmay qolardi —
    faqat modul to'liq tugagan paytda sakrab yangilanardi. Endi bu cascade
    shartsiz (course_id mavjud bo'lsa doim) chaqiriladi.
"""

import logging
from typing import Optional

from django.apps import apps
from django.db import transaction, IntegrityError
from django.db.models import F
from django.utils import timezone

from .models import (
    UserStats,
    LessonStatus,
    ModuleStatus,
    CourseStatus,
    ProblemStatus,
    LectureStatus,
)

logger = logging.getLogger(__name__)


def _get_model(app_label: str, model_name: str):
    """Circular import'lardan qochish uchun app registridan model olish."""
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        logger.error("Model topilmadi: %s.%s", app_label, model_name)
        return None


# ======================================================================
# 1. XP BERISH — yagona kirish nuqtasi
# ======================================================================
def award_xp(user, xp_amount, source="", duration_mins=0):
    if not xp_amount or xp_amount <= 0:
        return False

    UserStats.add_xp(
        user=user,
        xp_amount=xp_amount,
        duration_mins=duration_mins,
    )

    logger.info(
        "XP awarded",
        extra={
            "user_id": user.id,
            "xp": xp_amount,
            "source": source,
        },
    )

    return True

# ======================================================================
# 2. SERTIFIKAT YARATISH (markazlashtirilgan, idempotent)
# ======================================================================
def create_certificate(
    user_id: int,
    course_id: Optional[int] = None,
    test_id: Optional[int] = None,
    contest_id: Optional[int] = None,
):
    if not any([course_id, test_id, contest_id]):
        return None

    Certificate = _get_model("certificate", "Certificate")
    if not Certificate:
        return None

    filters = {"user_id": user_id}
    if course_id:
        filters["course_id"] = course_id
    if test_id:
        filters["test_id"] = test_id
    if contest_id:
        filters["contest_id"] = contest_id

    try:
        cert, created = Certificate.objects.get_or_create(
            defaults={"status": Certificate.Status.PENDING},
            **filters,
        )
        if created:
            logger.info("Certificate yaratildi: %s | user_id=%s", cert.certificate_code, user_id)
        return cert
    except IntegrityError:
        # Parallel so'rov allaqachon yaratib ulgurgan bo'lishi mumkin — mavjudini qaytaramiz
        return Certificate.objects.filter(**filters).first()
    except Exception:
        logger.exception("Certificate yaratishda xatolik: user_id=%s", user_id)
        return None


def handle_course_status_completion(user_id: int, course_id: int) -> None:
    """CourseStatus is_completed=True bo'lganda chaqiriladi."""
    create_certificate(user_id=user_id, course_id=course_id)


# ======================================================================
# 3. LESSON -> MODULE -> COURSE STATUS ZANJIRI (YAGONA progress tizimi)
# ======================================================================

def mark_lesson_task_completed(user_id: int, lesson_id: int) -> None:
    """
    Lecture/Problem/Question tugatilganda (yoki qayta hisoblash kerak
    bo'lganda) chaqiriladigan YAGONA kirish nuqtasi.
    """
    recalculate_lesson_status(user_id, lesson_id)


def recalculate_lesson_status(user_id: int, lesson_id: int) -> None:
    """
    Darsning progress foizi va tugallanganlik holatini qayta hisoblaydi.
    LessonStatus modelida "progress" maydoni bor (0-100), shuning uchun
    bu yerda hisoblab, saqlaymiz.

    TUZATILDI: "quizs" appi mavjud emas. Savollar va javoblar
    courses.CourseQuestion / courses.CourseUserResponse orqali olinadi.
    Lesson'dan savollarga reverse nom — "questions" ("quiz_questions" emas).
    """
    Lesson = _get_model("courses", "Lesson")
    CourseUserResponse = _get_model("courses", "CourseUserResponse")
    if not Lesson:
        return

    lesson = Lesson.objects.filter(id=lesson_id).select_related("modul").first()
    if not lesson:
        return

    total_lectures = lesson.lectures.filter(is_active=True).count()
    total_problems = lesson.problems.filter(is_active=True).count()
    # CourseQuestion modelida "lesson XOR test" cheklovi bor, shuning uchun
    # lesson=lesson bo'lgan savollar avtomatik ravishda faqat darsga tegishli.
    total_questions = lesson.questions.count()
    total_tasks = total_lectures + total_problems + total_questions

    completed_lectures = LectureStatus.objects.filter(
        user_id=user_id, lecture__lesson=lesson, lecture__is_active=True, is_completed=True,
    ).count()

    completed_problems = ProblemStatus.objects.filter(
        user_id=user_id, problem__lesson=lesson, problem__is_active=True, solved=True,
    ).count()

    # MUHIM: faqat TO'G'RI javob berilgan savollar "tugallangan" hisoblanadi.
    # session__isnull=True — bu dars-ichi mustaqil savol javobi (test seansi emas).
    completed_questions = 0
    if CourseUserResponse:
        completed_questions = (
            CourseUserResponse.objects.filter(
                user_id=user_id,
                question__lesson=lesson,
                session__isnull=True,
                choice__is_correct=True,
            )
            .values("question_id")
            .distinct()
            .count()
        )

    finished = completed_lectures + completed_problems + completed_questions


    with transaction.atomic():
        lesson_status, created = LessonStatus.objects.select_for_update().get_or_create(
            user_id=user_id,
            lesson=lesson,
            defaults={
                "started_at": timezone.now(),
                "finished_tasks_count": finished,
                "is_completed": False,
            },
        )

        if not created:
            lesson_status.finished_tasks_count = finished

        just_completed = False
        if total_tasks > 0 and finished >= total_tasks and not lesson_status.is_completed:
            lesson_status.is_completed = True
            lesson_status.completed_at = timezone.now()
            just_completed = True

        lesson_status.save(update_fields=[
            "finished_tasks_count", "is_completed", "completed_at",
        ])
        modul_id = lesson.modul_id

    if just_completed and modul_id:
        recalculate_module_status(user_id, modul_id)


def recalculate_module_status(user_id: int, modul_id: int) -> None:
    """
    DIQQAT: ModuleStatus modelida "progress" maydoni YO'Q (faqat
    completed_lessons, completed_tests, is_completed bor). Shuning uchun
    bu yerda progress foizi HISOBLANMAYDI va SAQLANMAYDI — foiz kerak
    bo'lsa, uni API darajasida completed/total orqali frontend yoki
    view chiqarib beradi.

    TUZATILDI:
      - "quizs" appi mavjud emas -> courses.CourseTest / courses.CourseTestSession
        ishlatiladi.
      - CourseTest -> Modul bog'lanishi OneToOneField (related_name="test"),
        shuning uchun "modul.tests" (ko'plik) MAVJUD EMAS. To'g'ridan-to'g'ri
        CourseTest.objects.filter(modul_id=...) orqali sanaladi.
      - CourseTestSession'da "status" maydoni yo'q, faqat "completed_at" bor —
        tugallanganlik completed_at__isnull=False orqali tekshiriladi.

    TUZATILDI #2:
      - Avval recalculate_course_status() faqat "just_completed" (modul
        aynan shu chaqiriqda to'liq tugallangan) holatida chaqirilardi.
        Bu xato edi: CourseStatus.completed_lessons/tests/problems butun
        kurs bo'yicha real vaqtli hisoblanadigan sonlar bo'lgani uchun,
        modul hali to'liq tugamagan bo'lsa ham (masalan ichidagi bitta
        dars yangi tugallanganda) course darajasi yangilanishi kerak.
        Shu sabab bu yerda cascade endi shartsiz (course_id mavjud
        bo'lsa doim) chaqiriladi.
    """
    Modul = _get_model("courses", "Modul")
    CourseTest = _get_model("courses", "CourseTest")
    CourseTestSession = _get_model("courses", "CourseTestSession")
    if not Modul:
        return

    modul = Modul.objects.filter(id=modul_id).select_related("course").first()
    if not modul:
        return

    total_lessons = modul.lessons.filter(is_active=True).count()
    total_tests = (
        CourseTest.objects.filter(modul_id=modul_id, is_active=True).count()
        if CourseTest else 0
    )
    total = total_lessons + total_tests

    completed_lessons = LessonStatus.objects.filter(
        user_id=user_id, lesson__modul=modul, lesson__is_active=True, is_completed=True,
    ).count()

    completed_tests = 0
    if CourseTestSession:
        completed_tests = (
            CourseTestSession.objects.filter(
                user_id=user_id,
                test__modul_id=modul_id,
                test__is_active=True,
                completed_at__isnull=False,
            )
            .values("test_id")
            .distinct()
            .count()
        )

    finished = completed_lessons + completed_tests

    with transaction.atomic():
        module_status, created = ModuleStatus.objects.select_for_update().get_or_create(
            user_id=user_id,
            modul=modul,
            defaults={
                "started_at": timezone.now(),
                "completed_lessons": completed_lessons,
                "completed_tests": completed_tests,
                "is_completed": False,
            },
        )

        if not created:
            module_status.completed_lessons = completed_lessons
            module_status.completed_tests = completed_tests

        just_completed = False
        if total > 0 and finished >= total and not module_status.is_completed:
            module_status.is_completed = True
            module_status.completed_at = timezone.now()
            just_completed = True

        module_status.save(update_fields=[
            "completed_lessons", "completed_tests", "is_completed", "completed_at",
        ])
        course_id = modul.course_id

    # CourseStatus sonlari butun kurs bo'yicha real vaqtli qayta hisoblanadi
    # (recalculate_course_status ichida), shuning uchun modul hali to'liq
    # tugamagan bo'lsa ham (just_completed=False) course darajasini
    # yangilash kerak — cascade shartsiz chaqiriladi.
    if course_id:
        recalculate_course_status(user_id, course_id)


def recalculate_course_status(user_id: int, course_id: int) -> None:
    """
    DIQQAT: CourseStatus modelida ham "progress" va "last_activity"
    maydonlari YO'Q. Faqat completed_modules/lessons/tests/problems va
    is_completed bor — shularga yozamiz, boshqasiga yozmaymiz.

    TUZATILDI: "quizs" appi mavjud emas -> courses.CourseTest /
    courses.CourseTestSession ishlatiladi. Tugallanganlik
    completed_at__isnull=False orqali tekshiriladi ("status" maydoni yo'q).
    """
    Course = _get_model("courses", "Course")
    Lesson = _get_model("courses", "Lesson")
    CourseTest = _get_model("courses", "CourseTest")
    CourseTestSession = _get_model("courses", "CourseTestSession")
    Problem = _get_model("problems", "Problem")
    if not Course or not Lesson:
        return

    course = Course.objects.filter(id=course_id).first()
    if not course:
        return

    modul_ids = list(course.modullar.filter(is_active=True).values_list("id", flat=True))

    total_modules = len(modul_ids)
    total_lessons = Lesson.objects.filter(modul_id__in=modul_ids, is_active=True).count()
    total_tests = (
        CourseTest.objects.filter(modul_id__in=modul_ids, is_active=True).count()
        if CourseTest else 0
    )
    total_problems = (
        Problem.objects.filter(lesson__modul_id__in=modul_ids, is_active=True).count()
        if Problem else 0
    )

    completed_modules = ModuleStatus.objects.filter(
        user_id=user_id, modul_id__in=modul_ids, is_completed=True,
    ).count()

    completed_lessons = LessonStatus.objects.filter(
        user_id=user_id, lesson__modul_id__in=modul_ids, lesson__is_active=True, is_completed=True,
    ).count()

    completed_tests = 0
    if CourseTestSession:
        completed_tests = (
            CourseTestSession.objects.filter(
                user_id=user_id,
                test__modul_id__in=modul_ids,
                test__is_active=True,
                completed_at__isnull=False,
            )
            .values("test_id")
            .distinct()
            .count()
        )

    completed_problems = ProblemStatus.objects.filter(
        user_id=user_id,
        problem__lesson__modul_id__in=modul_ids,
        problem__is_active=True,
        solved=True,
    ).count()

    total_items = total_modules + total_lessons + total_tests + total_problems
    finished_items = completed_modules + completed_lessons + completed_tests + completed_problems

    with transaction.atomic():
        course_status, created = CourseStatus.objects.select_for_update().get_or_create(
            user_id=user_id,
            course=course,
            defaults={
                "started_at": timezone.now(),
                "completed_modules": completed_modules,
                "completed_lessons": completed_lessons,
                "completed_tests": completed_tests,
                "completed_problems": completed_problems,
                "is_completed": False,
            },
        )

        if not created:
            course_status.completed_modules = completed_modules
            course_status.completed_lessons = completed_lessons
            course_status.completed_tests = completed_tests
            course_status.completed_problems = completed_problems

        just_completed = False
        if total_items > 0 and finished_items >= total_items and not course_status.is_completed:
            course_status.is_completed = True
            course_status.completed_at = timezone.now()
            just_completed = True

        course_status.save(update_fields=[
            "completed_modules", "completed_lessons", "completed_tests",
            "completed_problems", "is_completed", "completed_at",
        ])

    if just_completed:
        handle_course_status_completion(user_id, course_id)


# ======================================================================
# 4. TEST SEANSI YAKUNLANGANDA
# ======================================================================

def handle_test_session_completed(user_id: int, test_id: int) -> None:
    """
    Test yakunlanganda FAQAT modul progressini qayta hisoblaydi.
    Enrollment'ga yozish yo'q — Enrollment modelida bunday maydonlar yo'q.

    TUZATILDI: "quizs.Test" emas, "courses.CourseTest" ishlatiladi.
    """
    CourseTest = _get_model("courses", "CourseTest")
    if not CourseTest:
        return
    test = CourseTest.objects.filter(id=test_id).select_related("modul").first()
    if not test or not test.modul_id:
        return
    recalculate_module_status(user_id, test.modul_id)


# ======================================================================
# 5. MUSOBAQA: statusni COMPLETED qilish + XP + sertifikat
# ======================================================================

def check_and_complete_registration(registration) -> None:
    """
    ContestRegistration hali IN_PROGRESS bo'lsa va foydalanuvchi
    barcha masalalarga urinib bo'lgan (unanswered_count == 0) yoki
    contest tugagan bo'lsa (end_time o'tgan) — COMPLETED qiladi.
    """
    ContestRegistration = _get_model("contests", "ContestRegistration")
    if not ContestRegistration or registration.status != ContestRegistration.Status.IN_PROGRESS:
        return

    contest = registration.contest
    now = timezone.now()
    all_attempted = registration.unanswered_count == 0
    contest_ended = contest.end_time is not None and now > contest.end_time

    if not (all_attempted or contest_ended):
        return

    registration.status = ContestRegistration.Status.COMPLETED
    registration.save(update_fields=["status", "completed_at"])
    # post_save signal (contests/signals.py) shu yerdan avtomatik ishga tushadi.


def handle_contest_completion(registration_id: int) -> None:
    """
    ContestRegistration COMPLETED bo'lganda XP va sertifikat beradi.
    Race-condition xavfsiz: atomik filter(xp_awarded=0).update(...)
    ishlatiladi — "o'qi -> tekshir -> yoz" emas.
    """
    ContestRegistration = _get_model("contests", "ContestRegistration")
    if not ContestRegistration:
        return

    try:
        reg = ContestRegistration.objects.select_related("contest", "user").get(pk=registration_id)
    except ContestRegistration.DoesNotExist:
        return

    if reg.status != ContestRegistration.Status.COMPLETED:
        return

    xp_amount = getattr(reg.contest, "xp", 0) or 0
    if xp_amount > 0 and reg.xp_awarded == 0:
        try:
            with transaction.atomic():
                updated = ContestRegistration.objects.filter(
                    pk=reg.pk, xp_awarded=0,
                ).update(xp_awarded=xp_amount)
            if updated:
                award_xp(reg.user, xp_amount, source="contest")
        except Exception:
            logger.exception("Contest XP berishda xatolik: registration_id=%s", registration_id)

    create_certificate(user_id=reg.user_id, contest_id=reg.contest_id)