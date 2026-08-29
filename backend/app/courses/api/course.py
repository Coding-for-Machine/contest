# courses/api.py
import copy
import logging
from datetime import timedelta

from django.db.models.functions import Cast
import msgspec
from asgiref.sync import sync_to_async
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q, Case, Count, ExpressionWrapper, FloatField, Prefetch, Value, When
from django.utils import timezone

from django_bolt import Router, Depends, Request, JSON
from django_bolt.exceptions import HTTPException
from django_bolt.middleware import rate_limit

from courses.access import ensure_course_access
from problems.models import Challenge, Function, Hint, Language, Problem, Tags, TestCase
from submissions.models import Submission
from baseuser.models import BaseUser
from baseuser.authenticate import get_current_user_option, get_current_user

from courses.models import (
    Course, Lecture, Modul, Lesson, Enrollment,
    CourseTest, CourseQuestion, CourseChoice,
    CourseTestSession, CourseUserResponse,
)

from .cache import (
    get_course_list_static,
    set_course_list_static,
    get_course_detail_static,
    set_course_detail_static,
)
from status.models import (
    CourseStatus,
    LectureStatus,
    LessonStatus,
    ModuleStatus,
    ProblemStatus,
    UserStats,
)
from status.services import award_xp, mark_lesson_task_completed, recalculate_module_status

logger = logging.getLogger(__name__)
api = Router(tags=["Courses"])

# ==========================================================
# JSON KALIT QISQARTMALARI (trafikni tejash uchun)
# ==========================================================
# Ro'yxat qaytaruvchi endpointlarda (courses, modules, lessons,
# lectures, questions...) bir xil kalitlar minglab marta
# takrorlanadi, shuning uchun ular qisqartirilgan holda yuboriladi.
#
#   id     -> id (o'zgarishsiz)
#   t      -> title
#   s      -> slug
#   desc   -> description
#   p      -> price
#   dp     -> discount_price
#   img    -> thumbnail url
#   vid    -> video obyekti {hls, img, dur}
#   hls    -> hls_url
#   dur    -> duration (video uchun soniya, test uchun daqiqa — kontekstga qarab)
#   o      -> order
#   tl     -> total_lessons
#   tt     -> total_tests (modul darajasida: 0 yoki 1, chunki test OneToOne)
#   test   -> modul ichidagi test obyekti {id, t, s, dur, min_pct}
#             (CourseTest -> Modul OneToOne, shuning uchun modul boshiga
#             bittadan ortiq test bo'lishi mumkin emas). To'liq test
#             ma'lumoti (video, best_result, active_session) alohida
#             "/modul/{modul_id}/test/" endpoint orqali olinadi, chunki
#             u foydalanuvchiga bog'liq va statik keshga tushmaydi.
#   min_pct -> min_pass_percentage
#   ls     -> lessons (ro'yxat)
#   mods   -> modules (ro'yxat)
#   lecs   -> lectures (ro'yxat)
#   probs  -> problems (ro'yxat)
#   qs     -> questions (ro'yxat)
#   txt    -> savol matni
#   dif    -> difficulty
#   rt     -> reading_time
#   hv     -> has_video
#   paid   -> is_paid
#   done   -> is_completed
#   cl     -> completed_lessons
#   ct     -> completed_tests
#   ft     -> finished_tasks
#   ea     -> enrolled_at
#   us     -> user_status
#   ms     -> module_status
# ==========================================================


# ==========================================================
# YORDAMCHI: ProblemStatus (birinchi marta yechilganda)
# ==========================================================

def _mark_problem_solved(user_id: int, problem_id: int) -> bool:
    """True qaytaradi agar hozirgina birinchi marta yechilgan bo'lsa."""
    with transaction.atomic():
        ps, created = ProblemStatus.objects.select_for_update().get_or_create(
            user_id=user_id,
            problem_id=problem_id,
            defaults={
                "started_at": timezone.now(),
                "solved": True,
                "solved_at": timezone.now(),
            },
        )
        if not created and not ps.solved:
            ps.solved = True
            ps.solved_at = timezone.now()
            ps.save(update_fields=["solved", "solved_at"])
            return True
        return created


# ==========================================================
# QUERIES (N+1 oldini olish)
# ==========================================================

def _course_list_qs():
    return (
        Course.objects.filter(is_active=True)
        .select_related("intro_video")
        .only(
            "id", "title", "slug", "price", "discount_price",
            "total_lessons_count", "total_test_count",
            "intro_video__thumbnail",
        )
        .order_by("-id")
    )



def _course_detail_qs(slug: str):
    """O'ZGARDI: .only() ro'yxatiga 'level' va 'total_modules_count' qo'shildi."""
    lesson_qs = (
        Lesson.objects.filter(is_active=True)
        .only("id", "title", "slug", "order", "total_tasks_count", "modul_id")
        .order_by("order", "id")
    )
    module_qs = (
        Modul.objects.filter(is_active=True)
        .only("id", "title", "slug", "order", "course_id")
        .prefetch_related(Prefetch("lessons", queryset=lesson_qs))
        .order_by("order", "id")
    )
    return (
        Course.objects.filter(slug=slug, is_active=True)
        .select_related("intro_video")
        .prefetch_related(Prefetch("modullar", queryset=module_qs))
        .only(
            "id", "title", "slug", "description", "price", "discount_price",
            "level", "total_lessons_count", "total_test_count", "total_modules_count",
            "intro_video__hls_url", "intro_video__thumbnail", "intro_video__duration",
        )
    )


def _students_count_cache_key(course_id: int) -> str:
    return f"course_students_count:{course_id}"


async def _get_students_count(course_id: int) -> int:
    """Kursga yozilganlar soni — 5 daqiqa keshlanadi (og'ir COUNT() emas)."""
    key = _students_count_cache_key(course_id)
    count = cache.get(key)
    if count is None:
        count = await Enrollment.objects.filter(course_id=course_id).acount()
        cache.set(key, count, timeout=300)
    return count



# ==========================================================
# 1. KURSLAR RO'YXATI
# ==========================================================

@api.get("/")
@rate_limit(rps=10, burst=20)
async def course_list(
    request: Request,
    user: BaseUser | None = Depends(get_current_user_option),
):
    """Kurslar ro'yxati. Static kesh + user progress countlari."""
    courses = get_course_list_static()

    if courses is None:
        qs = _course_list_qs()
        courses = []
        async for c in qs:
            courses.append({
                "id": c.id,
                "t": c.title,
                "s": c.slug,
                "p": float(c.price),
                "dp": float(c.discount_price) if c.discount_price else None,
                "img": (
                    c.intro_video.thumbnail.url
                    if c.intro_video and c.intro_video.thumbnail else None
                ),
                "tl": c.total_lessons_count,
                "tt": c.total_test_count,
            })
        set_course_list_static(courses)

    result = copy.deepcopy(courses)

    if not user:
        return result

    course_ids = [c["id"] for c in result]

    enrollments = {}
    async for e in Enrollment.objects.filter(user=user, course_id__in=course_ids).only("course_id", "is_paid"):
        enrollments[e.course_id] = e.is_paid

    statuses = {}
    async for s in CourseStatus.objects.filter(user=user, course_id__in=course_ids).only(
        "course_id", "completed_lessons", "completed_tests", "is_completed"
    ):
        statuses[s.course_id] = s

    for c in result:
        cid = c["id"]
        c["paid"] = enrollments.get(cid, False)
        st = statuses.get(cid)
        c["cl"] = st.completed_lessons if st else 0
        c["ct"] = st.completed_tests if st else 0
        c["done"] = st.is_completed if st else False

    return result

# courses/api.py

from .cache import get_hero_course_cache, set_hero_course_cache


# ==========================================================
# 0. BOSH SAHIFA HERO — ENG KO'P FOYDALANUVCHI YOZILGAN KURS
# ==========================================================

@api.get("/hero/")
@rate_limit(rps=10, burst=20)
async def get_hero_course(request: Request):
    """
    Bosh sahifadagi hero banner: Enrollment soni bo'yicha eng
    ko'p foydalanuvchiga ega faol kurs. Model'da alohida flag
    yo'q — har doim haqiqiy statistikadan hisoblanadi.

    5 daqiqa keshlanadi (login holatidan qat'i nazar bir xil
    natija, shu sababli foydalanuvchiga bog'liq emas).
    """
    data = get_hero_course_cache()
    if data is not None:
        return data

    top = await (
        Enrollment.objects
        .filter(course__is_active=True)
        .values("course_id")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
        .afirst()
    )

    if not top:
        return JSON(None, status_code=204)

    course = await (
        Course.objects.filter(id=top["course_id"])
        .select_related("intro_video")
        .only(
            "id", "title", "slug", "description", "price", "discount_price",
            "total_lessons_count", "total_test_count",
            "intro_video__hls_url", "intro_video__thumbnail", "intro_video__duration",
        )
        .afirst()
    )

    if not course:
        return JSON(None, status_code=204)

    data = {
        "id": course.id,
        "t": course.title,
        "s": course.slug,
        "desc": course.description,
        "p": float(course.price),
        "dp": float(course.discount_price) if course.discount_price else None,
        "vid": {
            "hls": course.intro_video.hls_url if course.intro_video else None,
            "img": (
                course.intro_video.thumbnail.url
                if course.intro_video and course.intro_video.thumbnail else None
            ),
            "dur": course.intro_video.duration if course.intro_video else None,
        },
        "tl": course.total_lessons_count,
        "tt": course.total_test_count,
        "students": top["cnt"],
    }
    set_hero_course_cache(data)
    return data



# ==========================================================
# 2. KURS DETALI
# ==========================================================
@api.get("/{slug}")
@rate_limit(rps=10, burst=20)
async def course_detail(
    request: Request,
    slug: str,
    user: BaseUser | None = Depends(get_current_user_option),
):
    """
    Kurs detali: modullar, darslar, video, user status.

    MUHIM: Statik kurs strukturasi (modullar/darslar nomi, tartibi va h.k.)
    keshlanadi (STATIC_TTL, kamdan-kam o'zgaradi). Lekin user progress
    (lesson/module/test statuslari) HECH QACHON keshlanmaydi — bu doimo
    o'zgarib turadigan ma'lumot va eskirgan holat ko'rsatish (masalan
    tugatilgan darsni "tugallanmagan" deb ko'rsatish) mantiqan noto'g'ri.
    Shuning uchun user progress har safar to'g'ridan-to'g'ri bazadan
    hisoblanadi.
    """
    # -----------------------------------------------------------------
    # 1) STATIK MA'LUMOTLAR — barcha userlar uchun bir xil, keshlanadi
    # -----------------------------------------------------------------
    data = get_course_detail_static(slug)

    if data is None:
        course = await _course_detail_qs(slug).afirst()
        if not course:
            raise HTTPException(404, "Kurs topilmadi")

        modules = []
        async for module in course.modullar.all():
            lessons = []
            async for lesson in module.lessons.all():
                lessons.append({
                    "id": lesson.id,
                    "t": lesson.title,
                    "s": lesson.slug,
                    "o": lesson.order,
                    "tk": lesson.total_tasks_count,
                })

            test_obj = await (
                CourseTest.objects
                .filter(modul_id=module.id, is_active=True)
                .only("id", "title", "slug", "duration", "min_pass_percentage")
                .afirst()
            )

            test_data = None
            if test_obj:
                test_data = {
                    "id": test_obj.id,
                    "t": test_obj.title,
                    "s": test_obj.slug,
                    "dur": test_obj.duration,
                    "min_pct": test_obj.min_pass_percentage,
                }

            modules.append({
                "id": module.id,
                "t": module.title,
                "s": module.slug,
                "o": module.order,
                "tl": len(lessons),
                "tt": 1 if test_data else 0,
                "test": test_data,
                "ls": lessons,
            })

        data = {
            "id": course.id,
            "t": course.title,
            "s": course.slug,
            "desc": course.description,
            "level": course.level,
            "p": float(course.price),
            "dp": float(course.discount_price) if course.discount_price else None,
            "vid": {
                "hls": course.intro_video.hls_url if course.intro_video else None,
                "img": (
                    course.intro_video.thumbnail.url
                    if course.intro_video and course.intro_video.thumbnail else None
                ),
                "dur": course.intro_video.duration if course.intro_video else None,
            },
            "tl": course.total_lessons_count,
            "tt": course.total_test_count,
            "tm": course.total_modules_count,
            "mods": modules,
        }
        set_course_detail_static(slug, data)

    # Statik nusxani olish (user/dinamik ma'lumotlar qo'shilishidan oldin)
    result = copy.deepcopy(data)

    # O'quvchilar soni — statik keshdan mustaqil, o'zining 5 daqiqalik keshi bilan
    result["students"] = await _get_students_count(result["id"])

    # -----------------------------------------------------------------
    # 2) ANONIM USER — locking va test statusisiz, faqat asosiy ma'lumot
    # -----------------------------------------------------------------
    if not user:
        first_lesson = True
        for i, m in enumerate(result["mods"]):
            m["locked"] = i > 0
            for l in m["ls"]:
                l["locked"] = not first_lesson
                first_lesson = False
        return result

    # -----------------------------------------------------------------
    # 3) LOGIN QILGAN USER — progress + enrollment + test natijalari
    #    HAR SAFAR BAZADAN, KESHSIZ.
    # -----------------------------------------------------------------
    course_id = result["id"]

    lesson_ids = [l["id"] for m in result["mods"] for l in m["ls"]]
    module_ids = [m["id"] for m in result["mods"]]
    test_ids = [m["test"]["id"] for m in result["mods"] if m["test"]]

    # --- LessonStatus ---
    lesson_statuses = {}
    async for ls in LessonStatus.objects.filter(
        user=user, lesson_id__in=lesson_ids
    ).only("lesson_id", "is_completed", "finished_tasks_count"):
        lesson_statuses[ls.lesson_id] = {
            "done": ls.is_completed,
            "ft": ls.finished_tasks_count,
        }

    # --- ModuleStatus ---
    module_statuses = {}
    async for ms in ModuleStatus.objects.filter(
        user=user, modul_id__in=module_ids
    ).only("modul_id", "is_completed", "completed_lessons", "completed_tests"):
        module_statuses[ms.modul_id] = {
            "done": ms.is_completed,
            "cl": ms.completed_lessons,
            "ct": ms.completed_tests,
        }

    # --- Modul testlari bo'yicha ENG YAXSHI natija (bitta so'rov, N+1 yo'q) ---
    test_results = {}
    attempted_ids = set()
    if test_ids:
        async for s in (
            CourseTestSession.objects
            .filter(user=user, test_id__in=test_ids, completed_at__isnull=False)
            .order_by("test_id", "-total_xp_earned")
            .only("test_id", "correct_count", "wrong_count", "unanswered_count")
        ):
            if s.test_id in test_results:
                continue
            total = s.correct_count + s.wrong_count + s.unanswered_count
            score_pct = round((s.correct_count / total) * 100) if total else 0
            test_results[s.test_id] = {"score_pct": score_pct}

        # Foydalanuvchi umuman uringanmi (yakunlanmagan bo'lsa ham) — "attempted"
        async for tid in (
            CourseTestSession.objects
            .filter(user=user, test_id__in=test_ids)
            .values_list("test_id", flat=True).distinct()
        ):
            attempted_ids.add(tid)

    # --- CourseStatus ---
    status = await CourseStatus.objects.filter(
        user=user, course_id=course_id
    ).only(
        "completed_lessons", "completed_tests", "is_completed", "started_at"
    ).afirst()

    # --- Enrollment ---
    enrollment = await Enrollment.objects.filter(
        user=user, course_id=course_id
    ).only("is_paid", "created_at").afirst()

    # -----------------------------------------------------------------
    # 4) STATUSLARNI + LOCKING'NI RESPONSE'GA QO'SHISH
    # -----------------------------------------------------------------
    prev_module_done = True   # 1-modul hech qachon qulflanmaydi
    prev_lesson_done = True   # Kursning birinchi lesson'i doim ochiq

    for m in result["mods"]:
        ms = module_statuses.get(m["id"], {"done": False, "cl": 0, "ct": 0})
        m["ms"] = ms
        m["locked"] = not prev_module_done
        prev_module_done = ms["done"]

        for l in m["ls"]:
            st = lesson_statuses.get(l["id"])
            l["us"] = st if st else {"done": False, "ft": 0}
            l["locked"] = not prev_lesson_done
            prev_lesson_done = st["done"] if st else False

        if m["test"]:
            tid = m["test"]["id"]
            best = test_results.get(tid)
            m["test"]["result"] = {
                "attempted": tid in attempted_ids,
                "score_pct": best["score_pct"] if best else None,
                "passed": (best["score_pct"] >= m["test"]["min_pct"]) if best else None,
            }

    result["progress"] = {
        "paid": enrollment.is_paid if enrollment else False,
        "started_at": status.started_at.isoformat() if status and status.started_at else None,
        "cl": status.completed_lessons if status else 0,
        "ct": status.completed_tests if status else 0,
        "done": status.is_completed if status else False,
    }

    return result

# ==========================================================
# 4. DARS DETALI (access lock bilan)
# ==========================================================

@api.get("/lesson/{slug}/")
@rate_limit(rps=50, burst=20)
async def get_lesson(
    request: Request,
    slug: str,
    request_user: BaseUser | None = Depends(get_current_user_option),
):
    """Dars detali: lectures, problems, quizzes + user status + access lock."""
    if not request_user:
        raise HTTPException(401, "Tizimga kirish talab qilinadi")

    lesson = await (
        Lesson.objects
        .filter(slug=slug)
        .select_related("modul", "modul__course")
        .prefetch_related(
            Prefetch(
                "lectures",
                queryset=Lecture.objects.only(
                    "id", "lesson_id", "title", "slug", "order",
                    "xp", "reading_time", "video_id",
                ).order_by("order"),
            ),
            Prefetch(
                "problems",
                queryset=Problem.objects.only(
                    "id", "lesson_id", "title", "slug", "is_active", "xp"
                ).order_by("id"),
            ),
            Prefetch(
                "questions",
                queryset=CourseQuestion.objects.filter(test__isnull=True).only(
                    "id", "lesson_id", "difficulty", "xp", "text"
                ).order_by("id"),
            ),
        )
        .afirst()
    )

    if not lesson:
        raise HTTPException(404, "Dars topilmadi")
    await ensure_course_access(request_user.id, lesson.modul.course)

    # -----------------------------------------------------------------
    # OLDINGI DARS + ACCESS TEKSHIRUVI
    # -----------------------------------------------------------------
    prev_lesson = await (
        Lesson.objects
        .filter(modul__course=lesson.modul.course, is_active=True)
        .filter(
            Q(modul__order__lt=lesson.modul.order)
            | Q(modul__order=lesson.modul.order, order__lt=lesson.order)
        )
        .order_by("-modul__order", "-order")
        .only("id")
        .afirst()
    )

    access = {
        "locked": False,
        "previous_lesson_id": None,
        "previous_lesson_completed": True,
    }

    if prev_lesson:
        prev_done = await LessonStatus.objects.filter(
            user=request_user, lesson=prev_lesson, is_completed=True
        ).aexists()
        access["previous_lesson_id"] = prev_lesson.id
        access["previous_lesson_completed"] = prev_done
        access["locked"] = not prev_done

    # Agar dars qulflangan bo'lsa — 403 qaytarib, sababini ko'rsatamiz
    if access["locked"]:
        return JSON(
            {
                "id": lesson.id,
                "t": lesson.title,
                "s": lesson.slug,
                "access": access,
            },
            status_code=403,
        )

    # -----------------------------------------------------------------
    # STATUS (faqat ochiq lesson uchun)
    # -----------------------------------------------------------------
    lesson_status = await LessonStatus.objects.filter(
        user=request_user, lesson=lesson
    ).only("finished_tasks_count", "is_completed").afirst()

    completed_lectures = {
        pk async for pk in LectureStatus.objects.filter(
            user=request_user, lecture__lesson=lesson, is_completed=True
        ).values_list("lecture_id", flat=True)
    }

    completed_questions = {
        pk async for pk in CourseUserResponse.objects.filter(
            user=request_user,
            question__lesson=lesson,
            session__isnull=True,
            choice__is_correct=True,
        ).values_list("question_id", flat=True).distinct()
    }

    completed_problems = {
        pk async for pk in ProblemStatus.objects.filter(
            user=request_user, problem__lesson=lesson, solved=True
        ).values_list("problem_id", flat=True)
    }

    return {
        "id": lesson.id,
        "t": lesson.title,
        "s": lesson.slug,
        "tk": lesson.total_tasks_count,
        "us": {
            "ft": lesson_status.finished_tasks_count if lesson_status else 0,
            "done": lesson_status.is_completed if lesson_status else False,
        },
        "access": access,
        "lecs": [
            {
                "id": lec.id,
                "t": lec.title,
                "s": lec.slug,
                "o": lec.order,
                "xp": lec.xp,
                "rt": lec.reading_time,
                "hv": lec.video_id is not None,
                "done": lec.id in completed_lectures,
            }
            for lec in lesson.lectures.all()
        ],
        "probs": [
            {
                "id": p.id,
                "t": p.title,
                "s": p.slug,
                "xp": p.xp,
                "done": p.id in completed_problems,
            }
            for p in lesson.problems.all() if p.is_active
        ],
        "qs": [
            {
                "id": q.id,
                "txt": q.text,
                "dif": q.difficulty,
                "xp": q.xp,
                "done": q.id in completed_questions,
            }
            for q in lesson.questions.all()
        ],
    }

# ==========================================================
# 3. KURSGA YOZILISH (TO'LIQ YAXSHILANGAN)
# ==========================================================

@api.post("/{slug}/enroll")
@rate_limit(rps=5, burst=10)
async def enroll_course(
    request: Request,
    slug: str,
    request_user: BaseUser = Depends(get_current_user),
):
    """
    Bepul kurs — to'g'ridan-to'g'ri yozadi + CourseStatus yaratadi.
    Pullik kurs — to'lov ma'lumotini qaytaradi (402).
    """
    # -----------------------------------------------------------------
    # 1) KURSNI OLIB TEKSHIRISH
    # -----------------------------------------------------------------
    course = await Course.objects.filter(
        slug=slug, is_active=True
    ).only("id", "price", "discount_price", "title").afirst()

    if not course:
        raise HTTPException(404, "Kurs topilmadi")

    # -----------------------------------------------------------------
    # 2) ALLAQACHON YOZILGANMI?
    # -----------------------------------------------------------------
    enrollment = await Enrollment.objects.filter(
        user_id=request_user.id, course_id=course.id
    ).afirst()

    if enrollment:
        # Agar allaqachon yozilgan bo'lsa, hozirgi holatini qaytaramiz
        status = await CourseStatus.objects.filter(
            user_id=request_user.id, course_id=course.id
        ).only("is_completed", "started_at", "completed_lessons", "completed_tests").afirst()

        return {
            "enrolled": True,
            "is_paid": enrollment.is_paid,
            "started_at": status.started_at.isoformat() if status and status.started_at else None,
            "course_id": course.id,
        }

    # -----------------------------------------------------------------
    # 3) PULLIK KURS — TO'LOV TALAB QILINADI
    # -----------------------------------------------------------------
    if course.current_price > 0:
        return JSON(
            {
                "payment_req": True,
                "amount": str(course.current_price),
                "course_id": course.id,
                "course_title": course.title,
            },
            status_code=402,
        )

    # -----------------------------------------------------------------
    # 4) BEPUL KURS — YOZISH + COURSESTATUS YARATISH
    # -----------------------------------------------------------------
    try:
        enrollment = await Enrollment.objects.acreate(
            user_id=request_user.id,
            course_id=course.id,
            is_paid=True,
        )
    except Exception as exc:
        logger.exception("Enrollment yaratishda xatolik: user=%s course=%s", request_user.id, course.id)
        raise HTTPException(500, "Kursga yozilishda xatolik yuz berdi")

    # CourseStatus yaratish (yoki olish agar mavjud bo'lsa)
    status = None
    try:
        status, created = await CourseStatus.objects.aget_or_create(
            user_id=request_user.id,
            course_id=course.id,
            defaults={
                "started_at": timezone.now(),
                "is_completed": False,
                "completed_modules": 0,
                "completed_lessons": 0,
                "completed_tests": 0,
                "completed_problems": 0,
            },
        )
        if not created and status.started_at is None:
            status.started_at = timezone.now()
            await status.asave(update_fields=["started_at"])
    except Exception as exc:
        logger.exception("CourseStatus yaratishda xatolik: user=%s course=%s", request_user.id, course.id)
        # CourseStatus xatoligi enrollment'ni bekor qilmaydi, faqat log qilinadi

    # -----------------------------------------------------------------
    # 5) KESHLARNI TOZALASH (muhim!)
    # -----------------------------------------------------------------
    # Kurs ro'yxati keshi (my_courses va course_list uchun)
    cache.delete("course_list_static")
    # User-specific kurs detali keshi
    cache.delete(f"course_user:{slug}:{request_user.id}")
    # Hero keshi ham eskirgan bo'lishi mumkin
    cache.delete("hero_course")

    # -----------------------------------------------------------------
    # 6) JAVOB
    # -----------------------------------------------------------------
    return {
        "enrolled": True,
        "is_paid": enrollment.is_paid,
        "course_id": course.id,
        "course_title": course.title,
        "started_at": status.started_at.isoformat() if status and status.started_at else None,
    }


# ==========================================================
# 5. MA'RUZA DETALI
# ==========================================================

@api.get("/lesson/{slug}/lectures/{lecture_slug}/")
@rate_limit(rps=10, burst=20)
async def get_lecture(
    request: Request,
    slug: str,
    lecture_slug: str,
    request_user: BaseUser | None = Depends(get_current_user_option),
):
    """Bitta ma'ruza haqida ma'lumot."""
    if not request_user:
        raise HTTPException(401, "Tizimga kirish talab qilinadi")

    lecture = await (
        Lecture.objects
        .filter(lesson__slug=slug, slug=lecture_slug)
        .select_related("video", "lesson__modul__course")
        .only(
            "id", "title", "body", "xp", "reading_time",
            "lesson__id", "lesson__modul__id", "lesson__modul__course__id",
            "video__hls_url", "video__video", "video__thumbnail", "video__duration",
        )
        .afirst()
    )
    if not lecture:
        raise HTTPException(404, "Ma'ruza topilmadi")

    await ensure_course_access(request_user.id, lecture.lesson.modul.course)

    lecture_status = await LectureStatus.objects.filter(
        user=request_user,
        lecture=lecture,
    ).afirst()

    if not lecture_status:
        lecture_status = await LectureStatus.objects.acreate(
            user=request_user,
            lecture=lecture,
            started_at=timezone.now(),
        )

    is_completed = lecture_status.is_completed

    return {
        "id": lecture.id,
        "title": lecture.title,
        "body": lecture.body,
        "xp": lecture.xp,
        "reading_time": lecture.reading_time,
        "is_completed": is_completed,
        "video": {
            "hls_url": lecture.video.hls_url if lecture.video else None,
            "url": lecture.video.video.url if lecture.video and lecture.video.video else None,
            "thumbnail": lecture.video.thumbnail.url if lecture.video and lecture.video.thumbnail else None,
            "duration": lecture.video.duration if lecture.video else None,
        },
    }


# ==========================================================
# 6. MA'RUZANI TUGATISH
# ==========================================================

@api.post("/lesson/{slug}/lectures/{lecture_slug}/complete/")
@rate_limit(rps=5, burst=10)
async def complete_lecture(
    request: Request,
    slug: str,
    lecture_slug: str,
    request_user: BaseUser | None = Depends(get_current_user_option),
):
    if not request_user:
        raise HTTPException(401, "Tizimga kirish talab qilinadi")

    lecture = await (
        Lecture.objects
        .filter(lesson__slug=slug, slug=lecture_slug)
        .select_related("lesson__modul__course")
        .only(
            "id", "xp", "reading_time",
            "lesson__id", "lesson__modul__id", "lesson__modul__course__id",
        )
        .afirst()
    )

    if not lecture:
        raise HTTPException(404, "Ma'ruza topilmadi")

    await ensure_course_access(request_user.id, lecture.lesson.modul.course)

    status = await LectureStatus.objects.filter(
        user=request_user,
        lecture=lecture,
    ).afirst()

    if not status:
        raise HTTPException(400, "Avval ma'ruzani oching")

    if status.is_completed:
        return {
            "completed": False,
            "xp": 0,
        }

    now = timezone.now()

    if lecture.reading_time and status.started_at:
        if now - status.started_at < timedelta(minutes=lecture.reading_time):
            raise HTTPException(403, "Ma'ruzani tugatish uchun vaqt yetarli emas")

    status.is_completed = True
    status.completed_at = now

    await status.asave(update_fields=["is_completed", "completed_at"])

    await sync_to_async(mark_lesson_task_completed, thread_sensitive=True)(
        user_id=request_user.id,
        lesson_id=lecture.lesson_id,
    )

    await sync_to_async(award_xp, thread_sensitive=True)(
        user=request_user,
        xp_amount=lecture.xp,
        source="lecture",
        duration_mins=lecture.reading_time or 0,
    )

    return {
        "completed": True,
        "xp": lecture.xp,
    }


# ==========================================================
# 7. DARSDAGI (LESSON) YAKKA QUIZ SAVOLI
# ==========================================================

@api.get("/lesson/{slug}/quizzes/{question_id}/")
@rate_limit(rps=10, burst=20)
async def get_quiz(
    request: Request,
    slug: str,
    question_id: int,
    request_user: BaseUser | None = Depends(get_current_user_option),
):
    if not request_user:
        raise HTTPException(401, "Tizimga kirish talab qilinadi")

    question = await (
        CourseQuestion.objects
        .filter(id=question_id, lesson__slug=slug)
        .select_related("lesson__modul__course")
        .prefetch_related(
            Prefetch("choices", queryset=CourseChoice.objects.only("id", "question_id", "text"))
        )
        .only(
            "id", "text", "difficulty", "xp",
            "lesson__modul__course__id",
            "lesson__modul__course__price",
            "lesson__modul__course__discount_price",
        )
        .afirst()
    )

    if not question:
        raise HTTPException(404, "Savol topilmadi")

    await ensure_course_access(request_user.id, question.lesson.modul.course)

    done = await (
        CourseUserResponse.objects
        .filter(
            user=request_user,
            question_id=question.id,
            session__isnull=True,
            choice__is_correct=True,
        )
        .aexists()
    )

    return {
        "id": question.id,
        "text": question.text,
        "difficulty": question.difficulty,
        "xp": question.xp,
        "done": done,
        "choices": [
            {"id": choice.id, "text": choice.text}
            for choice in question.choices.all()
        ],
    }


# ==========================================================
# 8. DARSDAGI QUIZGA JAVOB BERISH
# ==========================================================

class AnswerIn(msgspec.Struct):
    choice_id: int


@api.post("/lesson/{slug}/quizzes/{question_id}/complete/")
@rate_limit(rps=5, burst=10)
async def complete_quiz(
    request: Request,
    slug: str,
    question_id: int,
    payload: AnswerIn,
    request_user: BaseUser | None = Depends(get_current_user_option),
):
    if not request_user:
        raise HTTPException(401, "Tizimga kirish talab qilinadi")

    question = await (
        CourseQuestion.objects
        .filter(id=question_id, lesson__slug=slug)
        .select_related("lesson__modul__course", "explanation_video")
        .only(
            "id", "lesson_id", "xp", "explanation",
            "lesson__modul__course__id",
            "lesson__modul__course__price",
            "lesson__modul__course__discount_price",
            "explanation_video__hls_url",
            "explanation_video__thumbnail",
            "explanation_video__duration",
        )
        .afirst()
    )

    if not question:
        raise HTTPException(404, "Savol topilmadi")

    await ensure_course_access(request_user.id, question.lesson.modul.course)

    choice = await (
        CourseChoice.objects
        .filter(id=payload.choice_id, question_id=question.id)
        .only("id", "is_correct")
        .afirst()
    )

    if not choice:
        raise HTTPException(400, "Variant topilmadi")

    old = await (
        CourseUserResponse.objects
        .filter(
            user=request_user,
            question_id=question.id,
            session__isnull=True,
            choice__is_correct=True,
        )
        .aexists()
    )

    xp = 0

    if not old:
        await CourseUserResponse.objects.acreate(
            user=request_user,
            question=question,
            choice=choice,
        )

        if choice.is_correct:
            xp = question.xp
            try:
                await sync_to_async(mark_lesson_task_completed, thread_sensitive=True)(
                    user_id=request_user.id,
                    lesson_id=question.lesson_id,
                )
                await sync_to_async(award_xp, thread_sensitive=True)(
                    user=request_user,
                    xp_amount=xp,
                    source="quiz",
                )
            except Exception:
                logger.exception("quiz reward error")

    video = None
    if question.explanation_video:
        video = {
            "url": question.explanation_video.hls_url,
            "img": (
                question.explanation_video.thumbnail.url
                if question.explanation_video.thumbnail else None
            ),
            "time": question.explanation_video.duration,
        }

    return {
        "ans": {
            "id": choice.id,
            "correct": choice.is_correct,
        },
        "xp": xp,
        "exp": question.explanation,
        "video": video,
    }


# ==========================================================
# 9. MODUL TESTI HAQIDA MA'LUMOT (TO'LIQ — video, best_result,
#    active_session bilan). Bu endpoint course_detail'dagi
#    engil "test": {id,t,s,dur,min_pct} obyektini to'ldiradi —
#    foydalanuvchi test sahifasini ochganda shu yerdan to'liq
#    ma'lumot olinadi.
# ==========================================================

@api.get("/modul/{modul_id}/test/")
@rate_limit(rps=10, burst=20)
async def get_test_info(
    request: Request,
    modul_id: int,
    request_user: BaseUser = Depends(get_current_user),
):
    test = await (
        CourseTest.objects
        .filter(modul_id=modul_id, is_active=True)
        .select_related("modul__course", "intro_video")
        .only(
            "id", "title", "slug", "description", "duration",
            "min_pass_percentage", "max_lifelines",
            "modul_id", "modul__course_id",
            "intro_video__hls_url", "intro_video__thumbnail",
        )
        .afirst()
    )
    if not test:
        raise HTTPException(404, "Test topilmadi")

    await ensure_course_access(request_user.id, test.modul.course)

    question_count = await test.questions.acount()

    best_session = await (
        CourseTestSession.objects
        .filter(user=request_user, test=test, completed_at__isnull=False)
        .order_by("-total_xp_earned")
        .only("id", "correct_count", "wrong_count", "unanswered_count", "total_xp_earned", "completed_at")
        .afirst()
    )

    active_session = await (
        CourseTestSession.objects
        .filter(user=request_user, test=test, completed_at__isnull=True)
        .order_by("-started_at")
        .only("id", "started_at")
        .afirst()
    )

    return {
        "id": test.id,
        "title": test.title,
        "slug": test.slug,
        "description": test.description,
        "duration_minutes": test.duration,
        "min_pass_percentage": test.min_pass_percentage,
        "max_lifelines": test.max_lifelines,
        "question_count": question_count,
        "video": {
            "hls_url": test.intro_video.hls_url if test.intro_video else None,
            "thumbnail": (
                test.intro_video.thumbnail.url
                if test.intro_video and test.intro_video.thumbnail else None
            ),
        },
        "best_result": {
            "correct": best_session.correct_count,
            "wrong": best_session.wrong_count,
            "unanswered": best_session.unanswered_count,
            "xp": best_session.total_xp_earned,
            "completed_at": best_session.completed_at.isoformat(),
        } if best_session else None,
        "active_session_id": str(active_session.id) if active_session else None,
    }


# ==========================================================
# 10. TEST SEANSINI BOSHLASH
# ==========================================================

@api.post("/modul/{modul_id}/test/start/")
@rate_limit(rps=5, burst=10)
async def start_test_session(
    request: Request,
    modul_id: int,
    request_user: BaseUser = Depends(get_current_user),
):
    test = await (
        CourseTest.objects
        .filter(modul_id=modul_id, is_active=True)
        .select_related("modul__course")
        .only("id", "duration", "modul_id", "modul__course_id")
        .afirst()
    )
    if not test:
        raise HTTPException(404, "Test topilmadi")

    await ensure_course_access(request_user.id, test.modul.course)

    # Davom etayotgan (yakunlanmagan) seans bo'lsa — o'shani qaytaramiz,
    # aks holda yangisini yaratamiz.
    session = await (
        CourseTestSession.objects
        .filter(user=request_user, test=test, completed_at__isnull=True)
        .order_by("-started_at")
        .afirst()
    )
    if not session:
        session = await CourseTestSession.objects.acreate(
            user=request_user,
            test=test,
        )

    questions = []
    async for q in (
        CourseQuestion.objects
        .filter(test=test)
        .prefetch_related(
            Prefetch("choices", queryset=CourseChoice.objects.only("id", "question_id", "text"))
        )
        .only("id", "test_id", "difficulty", "xp", "text")
        .order_by("id")
    ):
        questions.append({
            "id": q.id,
            "text": q.text,
            "difficulty": q.difficulty,
            "xp": q.xp,
            "choices": [{"id": c.id, "text": c.text} for c in q.choices.all()],
        })

    return {
        "session_id": str(session.id),
        "started_at": session.started_at.isoformat(),
        "duration_minutes": test.duration,
        "questions": questions,
    }


# ==========================================================
# 11. TEST SEANSIDA SAVOLGA JAVOB BERISH
# ==========================================================

class TestAnswerIn(msgspec.Struct):
    question_id: int
    choice_id: int | None = None  # None => javobsiz qoldirish


@api.post("/test-session/{session_id}/answer/")
@rate_limit(rps=10, burst=20)
async def answer_test_question(
    request: Request,
    session_id: str,
    payload: TestAnswerIn,
    request_user: BaseUser = Depends(get_current_user),
):
    session = await (
        CourseTestSession.objects
        .filter(id=session_id, user=request_user)
        .only("id", "test_id", "completed_at")
        .afirst()
    )
    if not session:
        raise HTTPException(404, "Seans topilmadi")
    if session.completed_at is not None:
        raise HTTPException(400, "Bu seans allaqachon yakunlangan")

    question = await CourseQuestion.objects.filter(
        id=payload.question_id, test_id=session.test_id
    ).only("id").afirst()
    if not question:
        raise HTTPException(404, "Savol ushbu testga tegishli emas")

    choice = None
    if payload.choice_id is not None:
        choice = await CourseChoice.objects.filter(
            id=payload.choice_id, question_id=question.id
        ).only("id").afirst()
        if not choice:
            raise HTTPException(400, "Variant topilmadi")

    await CourseUserResponse.objects.aupdate_or_create(
        session=session, question=question,
        defaults={"user": request_user, "choice": choice},
    )

    return {
        "saved": True,
        "question_id": question.id,
        "choice_id": choice.id if choice else None,
    }


# ==========================================================
# 12. TEST SEANSINI YAKUNLASH VA NATIJANI HISOBLASH
# ==========================================================

@api.post("/test-session/{session_id}/finish/")
@rate_limit(rps=5, burst=10)
async def finish_test_session(
    request: Request,
    session_id: str,
    request_user: BaseUser = Depends(get_current_user),
):
    """
    Testni yakunlaydi.

    Muhim:
    - calculate_mathematical_score() natijani hisoblaydi
    - calculate_mathematical_score() completed_at ni o'zi yozadi
    - testdan o'tish foizini hisoblaymiz
    - FAQAT o'tgan bo'lsa ModuleStatus/CourseStatus yangilanadi
    """

    # ------------------------------------------------------
    # 1. SESSION
    # ------------------------------------------------------
    session = await (
        CourseTestSession.objects
        .filter(
            id=session_id,
            user=request_user,
        )
        .select_related("test__modul")
        .afirst()
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Seans topilmadi",
        )

    # ------------------------------------------------------
    # 2. TEST ALLAQACHON YAKUNLANGAN BO'LSA
    # ------------------------------------------------------
    if session.completed_at is not None:

        question_count = await CourseQuestion.objects.filter(
            test_id=session.test_id
        ).acount()

        pass_percentage = (
            (session.correct_count / question_count) * 100
            if question_count > 0
            else 0
        )

        passed = pass_percentage >= session.test.min_pass_percentage

        # Agar oldin tugagan test o'tgan bo'lsa,
        # statusni qayta sync qilish xavfsiz.
        if passed:
            await sync_to_async(
                recalculate_module_status,
                thread_sensitive=True,
            )(
                user_id=request_user.id,
                modul_id=session.test.modul_id,
            )

        return {
            "correct": session.correct_count,
            "wrong": session.wrong_count,
            "unanswered": session.unanswered_count,
            "xp": session.total_xp_earned,

            "question_count": question_count,
            "percentage": round(pass_percentage, 2),
            "min_pass_percentage": session.test.min_pass_percentage,

            "passed": passed,
            "completed": True,
            "already_completed": True,

            "completed_at": session.completed_at.isoformat(),
        }

    # ------------------------------------------------------
    # 3. MATEMATIK NATIJANI HISOBLASH
    #
    # Bu metodning o'zi:
    # - correct_count
    # - wrong_count
    # - unanswered_count
    # - total_xp_earned
    # - completed_at
    #
    # ni yozadi.
    # ------------------------------------------------------
    await sync_to_async(
        session.calculate_mathematical_score,
        thread_sensitive=True,
    )()

    await session.arefresh_from_db()

    # ------------------------------------------------------
    # 4. TESTDAGI SAVOLLAR SONI
    # ------------------------------------------------------
    question_count = await CourseQuestion.objects.filter(
        test_id=session.test_id
    ).acount()

    # ------------------------------------------------------
    # 5. FOIZNI HISOBLASH
    #
    # Masalan:
    # 20 ta savol
    # 15 ta to'g'ri
    #
    # 15 / 20 * 100 = 75%
    # ------------------------------------------------------
    pass_percentage = (
        (session.correct_count / question_count) * 100
        if question_count > 0
        else 0
    )

    pass_percentage = round(pass_percentage, 2)

    # ------------------------------------------------------
    # 6. O'TDI / O'TMADI
    # ------------------------------------------------------
    min_pass_percentage = session.test.min_pass_percentage

    passed = pass_percentage >= min_pass_percentage

    # ------------------------------------------------------
    # 7. FAQAT O'TGAN BO'LSA STATUSNI YANGILAYMIZ
    # ------------------------------------------------------
    if passed:
        await sync_to_async(
            recalculate_module_status,
            thread_sensitive=True,
        )(
            user_id=request_user.id,
            modul_id=session.test.modul_id,
        )

    # ------------------------------------------------------
    # 8. RESPONSE
    # ------------------------------------------------------
    return {
        "correct": session.correct_count,
        "wrong": session.wrong_count,
        "unanswered": session.unanswered_count,
        "xp": session.total_xp_earned,

        "question_count": question_count,
        "percentage": pass_percentage,
        "min_pass_percentage": min_pass_percentage,

        "passed": passed,
        "completed": True,
        "already_completed": False,

        "completed_at": (
            session.completed_at.isoformat()
            if session.completed_at
            else None
        ),
    }
# ==========================================================
# 13. TEST SEANSI NATIJASI (batafsil)
# ==========================================================

@api.get("/test-session/{session_id}/result/")
@rate_limit(rps=10, burst=20)
async def get_test_session_result(
    request: Request,
    session_id: str,
    request_user: BaseUser = Depends(get_current_user),
):
    session = await (
        CourseTestSession.objects
        .filter(id=session_id, user=request_user)
        .select_related("test")
        .afirst()
    )
    if not session:
        raise HTTPException(404, "Seans topilmadi")

    responses = []
    async for r in (
        CourseUserResponse.objects
        .filter(session=session)
        .select_related("question", "choice")
        .only(
            "id", "question_id", "question__text", "question__xp",
            "choice_id", "choice__text", "choice__is_correct",
        )
    ):
        responses.append({
            "question_id": r.question_id,
            "question_text": r.question.text,
            "choice_id": r.choice_id,
            "choice_text": r.choice.text if r.choice else None,
            "is_correct": r.choice.is_correct if r.choice else False,
        })

    return {
        "session_id": str(session.id),
        "test_title": session.test.title,
        "is_completed": session.completed_at is not None,
        "correct": session.correct_count,
        "wrong": session.wrong_count,
        "unanswered": session.unanswered_count,
        "xp": session.total_xp_earned,
        "min_pass_percentage": session.test.min_pass_percentage,
        "responses": responses,
    }


# ==========================================================
# 14. MENING KURSLARIM
# ==========================================================

@api.get("/users/me/courses/")
@rate_limit(rps=10, burst=20)
async def my_courses(
    request: Request,
    request_user: BaseUser = Depends(get_current_user),
):
    """Foydalanuvchining barcha kurslari + progress."""
    result = []
    async for e in (
        Enrollment.objects.filter(user=request_user)
        .select_related("course")
        .order_by("-created_at")
    ):
        status = await CourseStatus.objects.filter(
            user=request_user, course=e.course
        ).only(
            "completed_lessons", "completed_tests", "is_completed"
        ).afirst()

        result.append({
            "id": e.course.id,
            "t": e.course.title,
            "s": e.course.slug,
            "img": (
                e.course.intro_video.thumbnail.url
                if e.course.intro_video and e.course.intro_video.thumbnail else None
            ),
            "paid": e.is_paid,
            "ea": e.created_at.isoformat() if e.created_at else None,
            "cl": status.completed_lessons if status else 0,
            "ct": status.completed_tests if status else 0,
            "done": status.is_completed if status else False,
            "tl": e.course.total_lessons_count,
            "tt": e.course.total_test_count,
        })

    return result


# ==========================================================
# 15. MASALA (PROBLEM) DETALI
# ==========================================================

@api.get("/lesson/{lesson_slug}/problem/{slug}/")
@rate_limit(rps=10, burst=20)
async def get_problem(
    request: Request,
    lesson_slug: str,
    slug: str,
    request_user: BaseUser | None = Depends(get_current_user_option),
):
    # =================================================================
    # 1. STATIK KESH (BASE DATA) - 10 MINUT (600s)
    # =================================================================
    static_cache_key = f"problem_detail_static_{lesson_slug}_{slug}"
    base_data = cache.get(static_cache_key)

    if not base_data:
        problem = await (
            Problem.objects
            .filter(slug=slug, lesson__slug=lesson_slug, is_active=True)
            .select_related('category', 'lesson__modul__course')
            .prefetch_related(
                Prefetch('tags',        queryset=Tags.objects.only('id', 'name')),
                Prefetch('hints',       queryset=Hint.objects.only('id', 'text')),
                Prefetch('challenges',  queryset=Challenge.objects.only('id', 'text')),
                Prefetch('language',    queryset=Language.objects.only('id', 'name', 'version')),
                Prefetch('functions',   queryset=Function.objects.only('id', 'function', 'language_id')),
                Prefetch('test_cases',  queryset=TestCase.objects.filter(is_sample=True).only(
                    'id', 'problem_id', 'input_txt', 'output_txt', 'explanation'
                )),
            )
            .only(
                'id', 'title', 'slug', 'description', 'difficulty', 'xp',
                'time_limit', 'memory_limit', 'category__name',
                'lesson_id', 'lesson__modul_id',
                'lesson__modul__course_id',
            )
            .afirst()
        )

        if not problem:
            raise HTTPException(status_code=404, detail="Masala topilmadi!")

        base_data = {
            "id":       problem.id,
            "title":    problem.title,
            "slug":     problem.slug,
            "desc":     problem.description,
            "dif":      problem.difficulty,
            "xp":       problem.xp,
            "time_l":   problem.time_limit,
            "memory_l": problem.memory_limit,
            "cate_name": problem.category.name if problem.category else None,

            "tags":  [{"id": t.id, "name": t.name} for t in problem.tags.all()],
            "langs": [{"id": l.id, "name": l.name, "version": l.version} for l in problem.language.all()],
            "hints": [{"id": h.id, "text": h.text} for h in problem.hints.all()],
            "chall": [{"id": c.id, "text": c.text} for c in problem.challenges.all()],
            "exam": [
                {
                    "id":          case.id,
                    "input":       case.input_txt,
                    "output":      case.output_txt,
                    "explanation": case.explanation,
                }
                for case in problem.test_cases.all()
            ],
            "func": {
                fn.language_id: {"id": fn.id, "code": fn.function}
                for fn in problem.functions.all()
            },

            "lesson_id": problem.lesson_id,
            "course_id": problem.lesson.modul.course_id,
        }
        cache.set(static_cache_key, base_data, timeout=600)

    # =================================================================
    # 2. KIRISH HUQUQI
    # =================================================================
    if not request_user:
        raise HTTPException(401, "Tizimga kirish talab qilinadi")

    course = await Course.objects.only("id").aget(id=base_data["course_id"])
    await ensure_course_access(request_user.id, course)

    # =================================================================
    # 3. DINAMIK KESH (METRICS DATA) - 15 SEKUND
    # =================================================================
    dynamic_cache_key = f"problem_detail_dynamic_metrics_{base_data['id']}"
    acceptance_rate = cache.get(dynamic_cache_key)

    if acceptance_rate is None:
        metrics = await Problem.objects.filter(id=base_data["id"]).annotate(
            total_subs=Count("submissions"),
            correct_subs=Count("submissions", filter=Q(submissions__status=True)),
        ).annotate(
            calculated_acceptance=Case(
                When(total_subs=0, then=Value(0.0)),
                default=ExpressionWrapper(
                    Cast("correct_subs", FloatField()) / Cast("total_subs", FloatField()) * 100,
                    output_field=FloatField(),
                ),
                output_field=FloatField(),
            )
        ).values("calculated_acceptance").afirst()

        acceptance_rate = round(metrics["calculated_acceptance"]) if metrics else 0
        cache.set(dynamic_cache_key, acceptance_rate, timeout=15)

    # =================================================================
    # 4. JORIY FOYDALANUVCHI STATUSI (KESHGA SOLINMAYDI)
    # =================================================================
    is_solved = await Submission.objects.filter(
        user_id=request_user.id,
        problem_id=base_data["id"],
        status=True,
    ).aexists()

    # =================================================================
    # 5. YAKUNIY JAVOB
    # =================================================================
    return {
        **base_data,
        "acceptance": acceptance_rate,
        "solved":     is_solved,
    }