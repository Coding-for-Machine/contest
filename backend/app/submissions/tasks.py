# submissions/tasks.py
import math
from celery import shared_task
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from status.models import UserStats, UserActivityDaily, LessonStatus
from courses.models import Enrollment
from problems.models import Problem

# tasks.py
"""
Celery vazifalari (tasks) — kodni Piston orqali bajarish va natijani
Redis pub/sub kanaliga uzatish ishi shu yerda amalga oshiriladi.

UMUMIY OQIM (yana bir bor eslatma uchun):

  1. Foydalanuvchi "Ishga tushirish"/"Yuborish" bosadi
  2. Frontend POST /run yoki /submit yuboradi
  3. Router (router.py) darhol task_id generatsiya qilib, shu ikkita
     funksiyadan birini Celery navbatiga qo'yadi (.apply_async) va
     {"queued": True, "task_id": ...} javobini DARHOL qaytaradi
  4. Celery worker (bu fayldagi funksiyalar) navbatdan vazifani oladi,
     HAR BIR TESTCASE uchun PistonStreamService'ni chaqiradi
  5. Har bir testcase tugagach, natija Redisga PUBLISH qilinadi
     (kanal: "sse:user:{user_id}")
  6. Django Bolt'dagi SSE endpoint (sse.py) shu kanalni doim tinglab
     turadi va kelgan xabarni brauzerga "data: ...\n\n" qatori sifatida
     uzatadi
  7. Brauzerdagi global RCEvents (main.js) buni qabul qilib, task_id
     bo'yicha to'g'ri sahifaga/funksiyaga yo'naltiradi

Nega natija to'g'ridan-to'g'ri HTTP javobida qaytarilmaydi?
Chunki testcase'lar birma-bir, sekundlab davom etishi mumkin — agar HTTP
so'rov ochiq turib kutsa, brauzer/server timeout xavfi, va foydalanuvchi
"osilib qoldimi?" deb o'ylaydi. Shuning uchun POST DARHOL javob beradi
("navbatga qo'ydim"), natija esa alohida, asinxron kanal (SSE) orqali
bosqichma-bosqich keladi — foydalanuvchi har bir testcase o'tganini
JONLI (real-time) ko'radi.
"""

import json
from celery import shared_task
from asgiref.sync import async_to_sync
from django_redis import get_redis_connection

from problems.models import Problem, Language
from submissions.models import Submission
from .services import PistonStreamService


# ============================================================
# YORDAMCHI FUNKSIYALAR
# ============================================================

def _publish(user_id: int, event: dict) -> None:
    """
    Redisga bitta event PUBLISH qiladi.

    Kanal nomi "sse:user:{user_id}" — ya'ni har bir foydalanuvchining
    BARCHA natijalari (run ham, submit ham, kelajakda boshqa turdagi
    bildirishnomalar ham) shu bitta kanalga tushadi. Buni frontenddagi
    global RCEvents bitta SSE ulanish orqali tinglaydi va ichidagi
    "task_id" maydoniga qarab kimga tegishli ekanini aniqlaydi.

    django_redis'dagi `get_redis_connection("default")` — Django
    settings.py'dagi CACHES["default"] konfiguratsiyasidan foydalanadi,
    ya'ni alohida Redis ulanish sozlamasi yozish shart emas.
    """
    redis_conn = get_redis_connection("default")
    redis_conn.publish(f"sse:user:{user_id}", json.dumps(event))


def _extract_verdict_code(result_str: str) -> str:
    """
    PistonStreamService qaytargan stringdan verdikt kodini ajratib oladi.

    Misol: "IJRO: [AC]\\n[Natija]:\\n0 1"  →  "AC"
           "KOMPILYATSIYA: [CE]\\n..."      →  "CE"

    Bu funksiya faqat kvadrat qavs ichidagi ikki harfli kodni qidiradi —
    format `services.py`da tasvirlangan qolipga qat'iy amal qiladi deb
    ishonadi (agar servis formatini o'zgartirsangiz, bu yerni ham
    yangilash kerak bo'ladi).
    """
    if "[" in result_str and "]" in result_str:
        return result_str.split("[", 1)[1].split("]", 1)[0]
    return "XX"  # format kutilganidek bo'lmasa — xavfsiz tomonga (tizim xatosi) og'amiz


def _extract_actual_output(result_str: str) -> str:
    """
    "[Natija]:\\n" belgisidan keyingi qismni — ya'ni dasturning HAQIQIY
    stdout chiqishini — ajratib oladi. Bu qiymat keyin kutilgan
    (`expected`) chiqish bilan solishtiriladi.

    Agar "[Natija]:" umuman bo'lmasa (masalan CE/RE/TO holatlarida),
    bo'sh string qaytadi — chunki bunday holatlarda solishtirish
    umuman ma'nosiz (dastur natija bermagan).
    """
    if "[Natija]:" in result_str:
        return result_str.split("[Natija]:\n", 1)[-1].strip()
    return ""


def _get_piston_language(language_id: int) -> Language | None:
    """
    Bizning Language modelimizdagi ID bo'yicha Piston kutgan til nomi va
    versiyasini topadi.

    🛠️ MOSLASH KERAK: `language.piston_name` — bu sizning Language
    modelingizda mavjud bo'lmasligi mumkin. Agar sizda alohida maydon
    yo'q bo'lsa, quyidagicha oddiy xaritalash (mapping) yozing:

        PISTON_NAME_MAP = {"Pyhton": "python", "C++": "cpp", "Java": "java"}
        piston_name = PISTON_NAME_MAP.get(language.name, language.name.lower())
    """
    return Language.objects.filter(id=language_id).first()


def _run_single_testcase(language: Language, code: str, stdin: str, expected_output: str | None) -> tuple[str, bool]:
    """
    Bitta testcase'ni bajaradi va (xom_verdikt_string, o'tdimi) juftligini
    qaytaradi.

    "O'tdimi" (passed) shu yerda hisoblanadi, `services.py` EMAS — chunki
    faqat shu yerda testcase'ning "kutilgan chiqishi" (expected_output)
    mavjud. `PistonStreamService` esa faqat "dastur toza ishladimi"
    (AC/CE/RE/TO/SG) darajasida javob beradi, kutilgan natija bilan
    solishtirish uning vazifasi emas (single responsibility).
    """
    result_str = async_to_sync(PistonStreamService.process_and_stream_code)(
        language=language.piston_name,   # 🛠️ yuqoridagi eslatmaga qarang
        version=language.version,
        source_code=code,
        stdin=stdin,
    )

    is_ac = _extract_verdict_code(result_str) == "AC"

    if expected_output is None:
        # Kutilgan chiqish berilmagan bo'lsa (nazariy holat) — faqat AC/emasligiga qaraymiz
        passed = is_ac
    else:
        actual_output = _extract_actual_output(result_str)
        passed = is_ac and actual_output == expected_output.strip()

    return result_str, passed


# ============================================================
# 1) RUN — foydalanuvchi tomonidan yuborilgan NAMUNAVIY testcase'lar
#    ustida ishlaydi. Natija bazaga YOZILMAYDI — faqat foydalanuvchiga
#    jonli ko'rsatish uchun.
# ============================================================
@shared_task
def run_code_task(
    task_id: str,
    user_id: int,
    mode: str,              # "run" — hozircha faqat log/aniqlik uchun saqlanadi
    language_id: int,
    code: str,
    testcases: list[dict],  # [{"input": "...", "output": "..."}, ...]
) -> None:
    """
    RUN vazifasi.

    Celery bu funksiyani `router.py`dagi
        run_code_task.apply_async(task_id=task_id, kwargs={...})
    chaqiruvi orqali navbatga qo'yadi va biroz vaqtdan so'ng (worker bo'sh
    bo'lganda) bajaradi. Funksiya HECH NARSA "return" QILMAYDI — chunki
    natijalar HTTP javobi orqali emas, Redis PUBLISH orqali ketadi.
    """
    language = _get_piston_language(language_id)

    if not language:
        # Til topilmasa — darhol "done" (yakuniy) event yuboramiz, xatolik bilan.
        # Frontend buni ko'rib, foydalanuvchiga xabar beradi va tugmani qayta yoqadi.
        _publish(user_id, {
            "task_id": task_id,
            "type": "done",
            "error": "Til topilmadi",
            "all_passed": False,
            "total": 0,
            "passed_count": 0,
        })
        return

    total = len(testcases)
    passed_count = 0

    for idx, tc in enumerate(testcases):
        result_str, passed = _run_single_testcase(
            language=language,
            code=code,
            stdin=tc["input"],
            expected_output=tc.get("output"),
        )
        passed_count += int(passed)

        # HAR BIR testcase tugagach — DARHOL PUBLISH qilinadi. Bu orqali
        # foydalanuvchi 5 ta testni bittalab, jonli o'tayotganini ko'radi
        # (hammasi tugaguncha kutib turmaydi).
        _publish(user_id, {
            "task_id": task_id,
            "type": "run_result",
            "index": idx,           # frontendda qaysi test-case tugmasini yangilash kerakligini bilish uchun
            "total": total,
            "passed": passed,
            "result": result_str,   # ← xom verdikt-string, frontend parseVerdictString() bilan o'qiydi
        })

    # Barcha testcase'lar tugagach — YAKUNIY ("done") event. Frontend aynan
    # shu eventni ko'rib, "stream tugadi, natijani umumlashtir" deb tushunadi.
    _publish(user_id, {
        "task_id": task_id,
        "type": "done",
        "passed_count": passed_count,
        "total": total,
        "all_passed": total > 0 and passed_count == total,
    })


# ============================================================
# 2) SUBMIT — bazadagi YASHIRIN testlar ustida ishlaydi, va yakunda
#    natija Submission jadvaliga yoziladi (shu orqali "yechilgan"
#    holati keyinchalik /problems/{slug} javobida `solved: true`
#    sifatida qaytadi).
# ============================================================
@shared_task
def submit_code_task(
    task_id: str,
    user_id: int,
    mode: str,               # "submit"
    problem_id: int,
    language_id: int,
    code: str,
) -> None:
    """
    SUBMIT vazifasi — RUN'dan ikkita jiddiy farqi bor:

    1) Testcase'larni FRONTEND emas, BACKEND o'zi bazadan oladi — aks
       holda foydalanuvchi brauzer konsolidan yashirin testlarni ko'rib
       qolardi.
    2) Har bir testcase natijasi PUBLISH qilinganda, input/output
       TAFSILOTLARI YUBORILMAYDI — faqat verdikt kodi (masalan "[AC]"
       yoki "[WA]"). Aks holda foydalanuvchi RUN natijasidan farqli
       o'laroq, yashirin testning javobini bilib olardi.
    """
    language = _get_piston_language(language_id)
    problem = Problem.objects.filter(id=problem_id, is_active=True).first()

    if not language or not problem:
        _publish(user_id, {
            "task_id": task_id,
            "type": "done",
            "error": "Masala yoki til topilmadi",
            "all_passed": False,
            "total": 0,
            "passed_count": 0,
        })
        return

    # 🛠️ MOSLASH KERAK: yashirin testcase'lar qaysi modelda/related_name
    # bilan saqlanganiga qarab shu qatorni to'g'rilang. Masalan agar
    # modelingiz `Testcase` deb nomlangan va `problem` FK orqali bog'langan
    # bo'lsa: `problem.testcases.values("input", "output")`
    hidden_testcases = list(problem.testcases.values("input", "output"))

    total = len(hidden_testcases)
    passed_count = 0

    for idx, tc in enumerate(hidden_testcases):
        result_str, passed = _run_single_testcase(
            language=language,
            code=code,
            stdin=tc["input"],
            expected_output=tc["output"],
        )
        passed_count += int(passed)

        # ⚠️ Diqqat: bu yerda `result_str` (to'liq, stdout'ni ham o'z ichiga
        # olgan) EMAS, faqat verdikt KODINI o'z ichiga olgan qisqa string
        # yuborilyapti — sabab yuqoridagi docstring'da tushuntirilgan.
        _publish(user_id, {
            "task_id": task_id,
            "type": "submission_result",
            "index": idx,
            "total": total,
            "passed": passed,
            "result": f"IJRO: [{_extract_verdict_code(result_str)}]",
        })

    all_passed = total > 0 and passed_count == total

    # Natijani doimiy saqlaymiz — kelajakda "Yechimlar" (submission history)
    # tabida, va /problems/{slug}dagi "solved" maydonida shu yozuv ishlatiladi.
    Submission.objects.create(
        user_id=user_id,
        problem_id=problem_id,
        language_id=language_id,
        status=all_passed,
        verdict="AC" if all_passed else "WA",
        passed_test_count=passed_count,
        total_test_count=total,
        # 🛠️ Agar modelingizda `execution_time`/`execution_memory` kabi
        # MAJBURIY (NOT NULL) maydonlar bo'lsa, shu yerga ham qiymat
        # qo'shishingiz kerak bo'ladi. PistonStreamService hozircha vaqt/
        # xotira ma'lumotini alohida qaytarmaydi (faqat verdikt-string) —
        # agar bu kerak bo'lsa, `_run_single_testcase` funksiyasini
        # kengaytirib, Piston javobidagi `run.cpu_time`/`run.wall_time`ni
        # ham qaytarish kerak bo'ladi.
    )

    _publish(user_id, {
        "task_id": task_id,
        "type": "done",
        "passed_count": passed_count,
        "total": total,
        "all_passed": all_passed,
    })
@shared_task
def task_process_problem_submission(submission_id, user_id, problem_id, is_correct):
    """
    Xavfsiz Celery task: Masala qayerdan (Arxiv, Lesson yoki Contest) yechilganidan 
    qat'iy nazar xatosiz ishlaydi. Faqat mavjud bog'liqliklarni yangilaydi.
    """
    # Aylanma import (Circular Import) xatosini oldini olish
    from submissions.models import Submission

    with transaction.atomic():
        # 0. Masala obyektini bazadan olish (Faqat lesson yuklanadi, agar bo'lsa)
        try:
            problem = Problem.objects.select_related('lesson').get(id=problem_id)
        except Problem.DoesNotExist:
            return f"Xatolik: Problem {problem_id} topilmadi."

        # Submission obyektini bazadan olish
        try:
            submission = Submission.objects.get(id=submission_id)
        except Submission.DoesNotExist:
            return f"Xatolik: Submission {submission_id} topilmadi."

        # Foydalanuvchi bu masalani oldin ham to'g'ri yechganmi tekshiramiz (XP takrorlanmasligi uchun)
        should_give_xp = False
        if is_correct:
            previous_success = Submission.objects.filter(
                user_id=user_id,
                problem_id=problem_id,
                status=True
            ).exclude(pk=submission_id).exists()
            
            if not previous_success:
                should_give_xp = True

        # -----------------------------------------------------------------
        # 1. USER STATS (Global XP va Daraja) - DOIM ISHLAYDI (Arxiv holati uchun ham)
        # -----------------------------------------------------------------
        stats, _ = UserStats.objects.get_or_create(user_id=user_id)
        stats = UserStats.objects.select_for_update().get(pk=stats.pk)  # Row-level lock

        # Masalaning XP mukofotini xavfsiz olish
        problem_xp = getattr(problem, 'xp', 0) or 0

        if should_give_xp and problem_xp > 0:
            stats.xp += problem_xp
            stats.level = stats.compute_level()
            stats.save(update_fields=["xp", "level", "updated_at"])

        # -----------------------------------------------------------------
        # 2. USER ACTIVITY DAILY (GitHub Heatmap) - DOIM ISHLAYDI
        # -----------------------------------------------------------------
        today = timezone.now().date()
        activity, _ = UserActivityDaily.objects.get_or_create(user_id=user_id, date=today)
        
        if should_give_xp and problem_xp > 0:
            activity.xp_earned = F('xp_earned') + problem_xp
            
        activity.tasks_count = F('tasks_count') + 1
        
        # Vaqtni hisoblash (execution_time_ms yo'q bo'lsa 0 deb ketiladi)
        execution_time = getattr(submission, 'execution_time_ms', 0) or 0
        duration_mins = math.ceil(execution_time / 60000)
        activity.total_duration = F('total_duration') + duration_mins
        activity.save()

        # -----------------------------------------------------------------
        # 3. LESSON STATUS - FAQAT MASALA LESSON'GA BOG'LANGAN BO'LSA ISHLAYDI
        # -----------------------------------------------------------------
        lesson = getattr(problem, 'lesson', None)
        
        if should_give_xp and lesson is not None:
            lesson_status, _ = LessonStatus.objects.get_or_create(
                user_id=user_id,
                lesson_id=lesson.id
            )
            
            lesson_status.finished_tasks_count = F('finished_tasks_count') + 1
            lesson_status.save()
            lesson_status.refresh_from_db()  # Yangi qiymatni xotiraga yuklash
            
            # Lesson jami vazifalar sonini xavfsiz olish
            total_tasks = getattr(lesson, 'total_tasks_count', 0) or 0
            
            # Dars tugaganini tekshirish
            if total_tasks > 0 and lesson_status.finished_tasks_count >= total_tasks:
                if not lesson_status.is_completed:
                    lesson_status.is_completed = True
                    lesson_status.completed_at = timezone.now()
                    lesson_status.save(update_fields=['is_completed', 'completed_at'])

                    # -------------------------------------------------------------
                    # 4. ENROLLMENT (Kurs progressi) - ZANJIR XAVFSIZ BITTA-BITTA TEKSHIRILADI
                    # -------------------------------------------------------------
                    modul = getattr(lesson, 'modul', None)
                    course = getattr(modul, 'course', None) if modul else None
                    
                    if course is not None:
                        enrollment, _ = Enrollment.objects.get_or_create(
                            user_id=user_id,
                            course_id=course.id
                        )
                        
                        enrollment.finished_darslar_soni = F('finished_darslar_soni') + 1
                        enrollment.save()
                        enrollment.refresh_from_db()
                        
                        # Kurs jami darslar sonini xavfsiz olish
                        total_lessons = getattr(course, 'total_lessons_count', 0) or 0
                        
                        # Kurs to'liq tugaganini tekshirish
                        if total_lessons > 0 and enrollment.finished_darslar_soni >= total_lessons:
                            if not enrollment.is_completed:
                                enrollment.is_completed = True
                                enrollment.completed_at = timezone.now()
                                enrollment.save(update_fields=['is_completed', 'completed_at'])

        # -----------------------------------------------------------------
        # 5. CONTEST REGISTRATION - FAQAT MASALA CONTEST'GA BOG'LANGAN BO'LSA ISHLAYDI
        # -----------------------------------------------------------------
        contest_id = getattr(problem, 'contest_id', None)
        
        if contest_id is not None:
            # Dinamik import (agar boshqa appda bo'lsa xavfsiz bo'lishi uchun)
            from contests.models import ContestRegistration
            
            contest_reg = ContestRegistration.objects.filter(
                user_id=user_id,
                contest_id=contest_id,
                status=ContestRegistration.Status.IN_PROGRESS
            ).select_for_update().first()  # Faqat jarayondagi seans bloklanadi

            if contest_reg is not None:
                # Soniya sarfini hisoblash
                execution_time = getattr(submission, 'execution_time_ms', 0) or 0
                seconds_spent = math.ceil(execution_time / 1000)
                contest_reg.time_spent_seconds = F('time_spent_seconds') + seconds_spent

                if is_correct:
                    if should_give_xp:
                        contest_reg.correct_count = F('correct_count') + 1
                        contest_reg.total_xp_earned = F('total_xp_earned') + problem_xp
                else:
                    contest_reg.wrong_count = F('wrong_count') + 1
                
                contest_reg.save()

    return f"Submission {submission_id} muvaffaqiyatli yakunlandi."
