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
from django_bolt.exceptions import HTTPException, NotFound

from django_bolt.middleware import rate_limit
from courses.access import ensure_course_access
from problems.models import Challenge, Function, Hint, Language, Problem, Tags, TestCase
from submissions.models import Submission
from baseuser.models import BaseUser
from baseuser.authenticate import get_current_user_option, get_current_user

from courses.models import (
    ArrangeItem, Blank, BlankAnswer, Course, Lecture, MatchingPair, Modul, Lesson, Enrollment,
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
    return (
        Course.objects
        .filter(
            slug=slug,
            is_active=True,
        )
        .select_related(
            "intro_video",
        )
        .prefetch_related(
            Prefetch(
                "modullar",
                queryset=(
                    Modul.objects
                    .filter(is_active=True)
                    .select_related("test")
                    .prefetch_related(
                        Prefetch(
                            "lessons",
                            queryset=(
                                Lesson.objects
                                .filter(is_active=True)
                                .only(
                                    "id",
                                    "modul_id",
                                    "title",
                                    "slug",
                                    "order",
                                    "total_tasks_count",
                                )
                                .order_by("order")
                            ),
                        ),
                    )
                    .only(
                        # Modul
                        "id",
                        "course_id",
                        "title",
                        "slug",
                        "order",

                        # CourseTest
                        "test__id",
                        "test__modul_id",
                        "test__title",
                        "test__slug",
                        "test__duration",
                        "test__min_pass_percentage",
                        "test__is_active",
                    )
                    .order_by("order")
                ),
            ),
        )
        .only(
            # Course
            "id",
            "title",
            "slug",
            "description",
            "level",
            "price",
            "discount_price",
            "total_lessons_count",
            "total_test_count",
            "total_modules_count",

            # Intro video
            "intro_video__id",
            "intro_video__hls_url",
            "intro_video__thumbnail",
            "intro_video__duration",
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



@api.get("/{slug}")
@rate_limit(rps=10, burst=20)
async def course_detail(
    request: Request,
    slug: str,
    user: BaseUser | None = Depends(get_current_user_option),
):
    # ==========================================================
    # 1. STATIC COURSE
    # ==========================================================

    data = get_course_detail_static(slug)

    if data is None:
        course = await _course_detail_qs(slug).afirst()

        if course is None:
            raise HTTPException(404, "Kurs topilmadi")

        modules = []

        async for module in course.modullar.all():

            lessons = [
                {
                    "id": lesson.id,
                    "t": lesson.title,
                    "s": lesson.slug,
                    "o": lesson.order,
                    "tk": lesson.total_tasks_count,
                }
                async for lesson in module.lessons.all()
            ]

            # Prefetch qilingan reverse OneToOne
            # mavjud bo'lmasa DoesNotExist.
            try:
                test = module.test
            except CourseTest.DoesNotExist:
                test = None

            test_data = None

            if test is not None and test.is_active:
                test_data = {
                    "id": test.id,
                    "t": test.title,
                    "s": test.slug,
                    "dur": test.duration,
                    "min_pct": test.min_pass_percentage,
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

        intro_video = course.intro_video

        data = {
            "id": course.id,
            "t": course.title,
            "s": course.slug,
            "desc": course.description,
            "level": course.level,

            "p": float(course.price),
            "dp": (
                float(course.discount_price)
                if course.discount_price is not None
                else None
            ),

            "vid": {
                "hls": intro_video.hls_url if intro_video else None,
                "img": (
                    intro_video.thumbnail.url
                    if intro_video and intro_video.thumbnail
                    else None
                ),
                "dur": intro_video.duration if intro_video else None,
            },

            "tl": course.total_lessons_count,
            "tt": course.total_test_count,
            "tm": course.total_modules_count,
            "mods": modules,
        }

        set_course_detail_static(slug, data)

    # Cache objectni user uchun mutate qilib yubormaslik
    result = copy.deepcopy(data)

    # ==========================================================
    # 2. STUDENTS COUNT
    # ==========================================================

    result["students"] = await _get_students_count(result["id"])

    # ==========================================================
    # 3. ANONYMOUS
    # ==========================================================

    if user is None:
        previous_lesson_exists = False

        for module_index, module in enumerate(result["mods"]):

            module["locked"] = module_index > 0

            for lesson_index, lesson in enumerate(module["ls"]):

                lesson["locked"] = (
                    previous_lesson_exists
                )

                previous_lesson_exists = True

        return result

    # ==========================================================
    # 4. USER PROGRESS
    # ==========================================================

    course_id = result["id"]

    lesson_ids = [
        lesson["id"]
        for module in result["mods"]
        for lesson in module["ls"]
    ]

    module_ids = [
        module["id"]
        for module in result["mods"]
    ]

    test_ids = [
        module["test"]["id"]
        for module in result["mods"]
        if module["test"] is not None
    ]

    # ----------------------------------------------------------
    # LessonStatus
    # ----------------------------------------------------------

    lesson_statuses = {}

    if lesson_ids:
        async for status in (
            LessonStatus.objects
            .filter(
                user_id=user.id,
                lesson_id__in=lesson_ids,
            )
            .values(
                "lesson_id",
                "is_completed",
                "finished_tasks_count",
            )
        ):
            lesson_statuses[status["lesson_id"]] = {
                "done": status["is_completed"],
                "ft": status["finished_tasks_count"],
            }

    # ----------------------------------------------------------
    # ModuleStatus
    # ----------------------------------------------------------

    module_statuses = {}

    if module_ids:
        async for status in (
            ModuleStatus.objects
            .filter(
                user_id=user.id,
                modul_id__in=module_ids,
            )
            .values(
                "modul_id",
                "is_completed",
                "completed_lessons",
                "completed_tests",
            )
        ):
            module_statuses[status["modul_id"]] = {
                "done": status["is_completed"],
                "cl": status["completed_lessons"],
                "ct": status["completed_tests"],
            }

    # ----------------------------------------------------------
    # Test sessions
    # ----------------------------------------------------------

    test_results = {}
    attempted_test_ids = set()

    if test_ids:

        # Eng yaxshi yakunlangan attempt
        async for session in (
            CourseTestSession.objects
            .filter(
                user_id=user.id,
                test_id__in=test_ids,
                completed_at__isnull=False,
            )
            .order_by(
                "test_id",
                "-total_xp_earned",
            )
            .values(
                "test_id",
                "correct_count",
                "wrong_count",
                "unanswered_count",
            )
        ):
            test_id = session["test_id"]

            if test_id in test_results:
                continue

            total = (
                session["correct_count"]
                + session["wrong_count"]
                + session["unanswered_count"]
            )

            score_pct = (
                round(
                    session["correct_count"] / total * 100
                )
                if total
                else 0
            )

            test_results[test_id] = {
                "score_pct": score_pct,
            }

        # Attempt qilingan testlar
        async for test_id in (
            CourseTestSession.objects
            .filter(
                user_id=user.id,
                test_id__in=test_ids,
            )
            .values_list(
                "test_id",
                flat=True,
            )
            .distinct()
        ):
            attempted_test_ids.add(test_id)

    # ----------------------------------------------------------
    # CourseStatus
    # ----------------------------------------------------------

    course_status = await (
        CourseStatus.objects
        .filter(
            user_id=user.id,
            course_id=course_id,
        )
        .values(
            "completed_lessons",
            "completed_tests",
            "is_completed",
            "started_at",
        )
        .afirst()
    )

    # ----------------------------------------------------------
    # Enrollment
    # ----------------------------------------------------------

    enrollment = await (
        Enrollment.objects
        .filter(
            user_id=user.id,
            course_id=course_id,
        )
        .values(
            "is_paid",
        )
        .afirst()
    )

    # ==========================================================
    # 5. APPLY PROGRESS + LOCK
    # ==========================================================

    previous_module_done = True
    previous_lesson_done = True

    for module in result["mods"]:

        module_status = module_statuses.get(
            module["id"],
            {
                "done": False,
                "cl": 0,
                "ct": 0,
            },
        )

        module["ms"] = module_status

        module["locked"] = not previous_module_done

        previous_module_done = module_status["done"]

        # ------------------------------------------------------
        # Lessons
        # ------------------------------------------------------

        for lesson in module["ls"]:

            lesson_status = lesson_statuses.get(
                lesson["id"]
            )

            if lesson_status is None:
                lesson_status = {
                    "done": False,
                    "ft": 0,
                }

            lesson["us"] = lesson_status
            lesson["locked"] = not previous_lesson_done

            previous_lesson_done = lesson_status["done"]

        # ------------------------------------------------------
        # Test
        # ------------------------------------------------------

        test = module["test"]

        if test is not None:

            test_id = test["id"]

            best = test_results.get(test_id)

            test["result"] = {
                "attempted": test_id in attempted_test_ids,
                "score_pct": (
                    best["score_pct"]
                    if best
                    else None
                ),
                "passed": (
                    best["score_pct"] >= test["min_pct"]
                    if best
                    else None
                ),
            }

    # ==========================================================
    # 6. COURSE PROGRESS
    # ==========================================================

    result["progress"] = {
        "paid": (
            enrollment["is_paid"]
            if enrollment
            else False
        ),
        "started_at": (
            course_status["started_at"].isoformat()
            if course_status and course_status["started_at"]
            else None
        ),
        "cl": (
            course_status["completed_lessons"]
            if course_status
            else 0
        ),
        "ct": (
            course_status["completed_tests"]
            if course_status
            else 0
        ),
        "done": (
            course_status["is_completed"]
            if course_status
            else False
        ),
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
    if not request_user:
        raise HTTPException(401, "Tizimga kirish talab qilinadi")

    # ==========================================================
    # 1. LESSON
    # ==========================================================

    lesson = await (
        Lesson.objects
        .filter(
            slug=slug,
            is_active=True,
        )
        .select_related(
            "modul",
            "modul__course",
        )
        .prefetch_related(
            Prefetch(
                "lectures",
                queryset=Lecture.objects
                .filter(is_active=True)
                .order_by("order", "id"),
            ),
            Prefetch(
                "problems",
                queryset=Problem.objects
                .filter(is_active=True)
                .order_by("id"),
            ),
            Prefetch(
                "questions",
                queryset=CourseQuestion.objects
                .filter(test__isnull=True, is_embeddable=False)
                .order_by("id"),
            ),
        )
        .afirst()
    )

    if lesson is None:
        raise HTTPException(404, "Dars topilmadi")

    course = lesson.modul.course

    # ==========================================================
    # 2. COURSE ACCESS
    # ==========================================================

    await ensure_course_access(
        request_user.id,
        course,
    )

    # ==========================================================
    # 3. PREVIOUS LESSON
    # ==========================================================

    previous_lesson = await (
        Lesson.objects
        .filter(
            modul__course_id=course.id,
            is_active=True,
        )
        .filter(
            Q(modul__order__lt=lesson.modul.order)
            |
            Q(
                modul__order=lesson.modul.order,
                order__lt=lesson.order,
            )
        )
        .order_by(
            "-modul__order",
            "-order",
            "-id",
        )
        .values(
            "id",
            "slug",
            "title",
        )
        .afirst()
    )

    # ==========================================================
    # 4. ACCESS
    # ==========================================================

    access = {
        "locked": False,
        "previous_lesson_id": None,
        "previous_lesson_slug": None,
        "previous_lesson_completed": True,
    }

    if previous_lesson:

        previous_done = await LessonStatus.objects.filter(
            user_id=request_user.id,
            lesson_id=previous_lesson["id"],
            is_completed=True,
        ).aexists()

        access.update(
            {
                "previous_lesson_id": previous_lesson["id"],
                "previous_lesson_slug": previous_lesson["slug"],
                "previous_lesson_completed": previous_done,
                "locked": not previous_done,
            }
        )

    # ==========================================================
    # 5. LOCKED
    # ==========================================================

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

    # ==========================================================
    # 6. USER LESSON STATUS
    # ==========================================================

    lesson_status = await (
        LessonStatus.objects
        .filter(
            user_id=request_user.id,
            lesson_id=lesson.id,
        )
        .values(
            "finished_tasks_count",
            "is_completed",
        )
        .afirst()
    )

    # ==========================================================
    # 7. COMPLETED LECTURES
    # ==========================================================

    completed_lectures = {
        lecture_id
        async for lecture_id in (
            LectureStatus.objects
            .filter(
                user_id=request_user.id,
                lecture__lesson_id=lesson.id,
                is_completed=True,
            )
            .values_list(
                "lecture_id",
                flat=True,
            )
        )
    }

    # ==========================================================
    # 8. COMPLETED QUESTIONS
    # ==========================================================

    completed_questions = {
            question_id
            async for question_id in (
                CourseUserResponse.objects
                .filter(
                    user_id=request_user.id,
                    question__lesson_id=lesson.id,
                    session__isnull=True,
                    is_correct=True,
                )
                .values_list("question_id", flat=True)
                .distinct()
            )
        }

    # ==========================================================
    # 9. COMPLETED PROBLEMS
    # ==========================================================

    completed_problems = {
        problem_id
        async for problem_id in (
            ProblemStatus.objects
            .filter(
                user_id=request_user.id,
                problem__lesson_id=lesson.id,
                solved=True,
            )
            .values_list(
                "problem_id",
                flat=True,
            )
        )
    }

    # ==========================================================
    # 10. RESPONSE
    # ==========================================================

    return {
        "id": lesson.id,
        "t": lesson.title,
        "s": lesson.slug,
        "tk": lesson.total_tasks_count,

        "us": {
            "ft": (
                lesson_status["finished_tasks_count"]
                if lesson_status
                else 0
            ),
            "done": (
                lesson_status["is_completed"]
                if lesson_status
                else False
            ),
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
                "id": problem.id,
                "t": problem.title,
                "s": problem.slug,
                "xp": problem.xp,
                "done": problem.id in completed_problems,
            }
            for problem in lesson.problems.all()
        ],

        "qs": [
            {
                "id": question.id,
                "txt": question.text,
                "dif": question.difficulty,
                "xp": question.xp,
                "done": question.id in completed_questions,
            }
            for question in lesson.questions.all()
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

# GET descraption va hk. orqali savolarni olish yo'li questions/{question_id}/
# ==========================================================
# 16. YAKKA SAVOLNI ID ORQALI OLISH
#
# Maqsad:
#   - Istalgan joydan savolni ID orqali olish
#   - Lesson yoki Testga bog'langan bo'lishidan qat'i nazar ishlashi
#   - N+1 query bo'lmasligi
#   - Faqat frontendga kerakli fieldlarni yuborish
#   - Question type bo'yicha kerakli relationlargina qaytarilishi
#
# Frontend:
#
#   GET /questions/{question_id}/
#
# Masalan description ichida:
#
#   {{savol:123:get}}
#
# backend shu 123 ID orqali ushbu endpointni chaqirishi mumkin.
# ==========================================================
# UNIVERSAL QUESTION SERIALIZER
# ==========================================================

def _serialize_question(question):
    question_type = question.question_type

    result = {
        "id": question.id,
        "txt": question.text,
        "instruction": question.instruction,
        "type": question_type,
        "dif": question.difficulty,
        "xp": question.xp,
        "exp": question.explanation,
        "vid": (
            {
                "hls": question.explanation_video.hls_url,
                "img": (
                    question.explanation_video.thumbnail.url
                    if question.explanation_video.thumbnail
                    else None
                ),
                "dur": question.explanation_video.duration,
            }
            if question.explanation_video
            else None
        ),
    }

    # ------------------------------------------------------
    # SINGLE / MULTIPLE CHOICE
    # ------------------------------------------------------

    if question_type in (
        CourseQuestion.QuestionType.SINGLE_CHOICE,
        CourseQuestion.QuestionType.MULTIPLE_CHOICE,
    ):
        result["choices"] = [
            {
                "id": choice.id,
                "txt": choice.text,
            }
            for choice in question.choices.all()
        ]

    # ------------------------------------------------------
    # MATCHING
    # ------------------------------------------------------

    elif question_type == CourseQuestion.QuestionType.MATCHING:
        import random

        pairs = list(question.matching_pairs.all())

        # Chap tomon — original tartib
        result["pairs_left"] = [
            {
                "id": pair.id,
                "txt": pair.left,
                "o": pair.order,
            }
            for pair in pairs
        ]

        # O'ng tomon — random tartib
        pairs_right = [
            {
                "id": pair.id,
                "txt": pair.right,
            }
            for pair in pairs
        ]

        random.shuffle(pairs_right)

        result["pairs_right"] = pairs_right

    # ------------------------------------------------------
    # ARRANGE WORDS
    # ------------------------------------------------------

    elif question_type == CourseQuestion.QuestionType.ARRANGE_WORDS:
        result["items"] = [
            {
                "id": item.id,
                "txt": item.text,
            }
            for item in question.arrange_items.all()
        ]

    # ------------------------------------------------------
    # FILL BLANKS
    # ------------------------------------------------------

    elif question_type == CourseQuestion.QuestionType.FILL_BLANKS:
        result["blanks"] = [
            {
                "id": blank.id,
                "pos": blank.position,
                "case": blank.case_sensitive,
            }
            for blank in question.blanks.all()
        ]

    return result


# ==========================================================
# GET /questions/{question_id}/
# ==========================================================

@api.get("/questions/{question_id}/")
@rate_limit(rps=30, burst=60)
async def get_question_by_id(
    request: Request,
    question_id: int,
    request_user: BaseUser = Depends(get_current_user),
):
    """
    Universal embeddable question endpoint.

    Faqat is_embeddable=True bo'lgan savollar olinadi.

    Auth majburiy.

    Question:
        - Lesson'ga tegishli bo'lishi mumkin
        - Test'ga tegishli bo'lishi mumkin

    Agar question kursga tegishli bo'lsa,
    foydalanuvchining kursga access'i tekshiriladi.
    """

    question = await (
        CourseQuestion.objects
        .filter(
            id=question_id,
            is_embeddable=True,
        )
        .select_related(
            "explanation_video",
            "lesson__modul__course",
            "test__modul__course",
        )
        .only(
            # --------------------------------------------------
            # Question
            # --------------------------------------------------

            "id",
            "lesson_id",
            "test_id",
            "text",
            "instruction",
            "question_type",
            "difficulty",
            "xp",
            "explanation",

            # --------------------------------------------------
            # Lesson -> Modul -> Course
            # --------------------------------------------------

            "lesson__id",
            "lesson__modul__id",
            "lesson__modul__course__id",

            # --------------------------------------------------
            # Test -> Modul -> Course
            # --------------------------------------------------

            "test__id",
            "test__modul__id",
            "test__modul__course__id",

            # --------------------------------------------------
            # Explanation video
            # --------------------------------------------------

            "explanation_video__id",
            "explanation_video__hls_url",
            "explanation_video__thumbnail",
            "explanation_video__duration",
        )
        .prefetch_related(

            # --------------------------------------------------
            # SINGLE / MULTIPLE CHOICE
            # --------------------------------------------------

            Prefetch(
                "choices",
                queryset=(
                    CourseChoice.objects
                    .only(
                        "id",
                        "question_id",
                        "text",
                    )
                    .order_by("id")
                ),
            ),

            # --------------------------------------------------
            # MATCHING
            # --------------------------------------------------

            Prefetch(
                "matching_pairs",
                queryset=(
                    MatchingPair.objects
                    .only(
                        "id",
                        "question_id",
                        "left",
                        "right",
                        "order",
                    )
                    .order_by("order", "id")
                ),
            ),

            # --------------------------------------------------
            # ARRANGE WORDS
            # --------------------------------------------------

            Prefetch(
                "arrange_items",
                queryset=(
                    ArrangeItem.objects
                    .only(
                        "id",
                        "question_id",
                        "text",
                    )
                    .order_by("id")
                ),
            ),

            # --------------------------------------------------
            # FILL BLANKS
            # --------------------------------------------------

            Prefetch(
                "blanks",
                queryset=(
                    Blank.objects
                    .only(
                        "id",
                        "question_id",
                        "position",
                        "case_sensitive",
                    )
                    .order_by("position", "id")
                ),
            ),
        )
        .afirst()
    )

    if question is None:
        raise NotFound(
            404,
            detail="Savol topilmadi!",
        )

    # ======================================================
    # COURSE ACCESS
    # ======================================================

    course = None

    if question.lesson_id:
        course = question.lesson.modul.course

    elif question.test_id:
        course = question.test.modul.course

    if course is not None:
        await ensure_course_access(
            request_user.id,
            course,
        )

    # ======================================================
    # SERIALIZE
    # ======================================================

    return _serialize_question(question)

# ==========================================================
# 17. UNIVERSAL QUESTION ANSWER
#
# Barcha joydagi CourseQuestion uchun ishlaydi:
#
#   - Lesson quiz
#   - Test question
#   - Description ichidagi question
#
# Endpoint:
#
#   POST /questions/{question_id}/answer/
#
# Frontend faqat USER JAVOBINI yuboradi.
#
# To'g'ri javob backenddan hech qachon yuborilmaydi.
# ==========================================================


class QuestionAnswerIn(msgspec.Struct):
    # SINGLE_CHOICE
    choice_id: int | None = None
    # MULTIPLE_CHOICE
    selected_choice_ids: list[int] | None = None
    # MATCHING / ARRANGE / FILL_BLANKS
    answer_data: dict | None = None


def _question_video_data(question):
    """
    Explanation video ma'lumotlarini frontend formatida qaytaradi.

    DB query bu yerda ochilmaydi.
    explanation_video oldindan select_related qilinadi.
    """

    video = question.explanation_video

    if not video:
        return None

    return {
        "hls": video.hls_url,
        "img": (
            video.thumbnail.url
            if video.thumbnail
            else None
        ),
        "dur": video.duration,
    }


@api.post("/questions/{question_id}/answer/")
@rate_limit(rps=10, burst=20)
async def answer_question(
    request: Request,
    question_id: int,
    payload: QuestionAnswerIn,
    request_user: BaseUser = Depends(get_current_user),
):
    """
    Universal savol javob endpointi.

    Bu endpoint savolning qayerda ishlatilishidan qat'i nazar
    javobni tekshiradi.

    Question:
        - lessonga tegishli bo'lishi mumkin
        - testga tegishli bo'lishi mumkin

    Agar savol lesson ichida bo'lsa:
        session = None

    Agar savol test ichida bo'lsa:
        test session kerak bo'ladi.

    Muhim:
        Correct answer frontendga yuborilmaydi.
    """

    # ======================================================
    # 1. SAVOLNI OLAMIZ
    #
    # select_related:
    #   explanation_video
    #   lesson -> modul -> course
    #   test -> modul -> course
    #
    # bilan oldindan olinadi.
    # ======================================================

    question = await (
        CourseQuestion.objects
        .filter(id=question_id)
        .select_related(
            "explanation_video",
            "lesson__modul__course",
            "test__modul__course",
        )
        .only(
            # --------------------------------------------------
            # Question
            # --------------------------------------------------

            "id",
            "lesson_id",
            "test_id",
            "question_type",
            "xp",
            "explanation",

            # --------------------------------------------------
            # Lesson -> Modul -> Course
            # --------------------------------------------------

            "lesson__id",
            "lesson__modul__id",
            "lesson__modul__course__id",

            # --------------------------------------------------
            # Test -> Modul -> Course
            # --------------------------------------------------

            "test__id",
            "test__modul__id",
            "test__modul__course__id",

            # --------------------------------------------------
            # Explanation video
            # --------------------------------------------------

            "explanation_video__id",
            "explanation_video__hls_url",
            "explanation_video__thumbnail",
            "explanation_video__duration",
        )
        .prefetch_related(

            # --------------------------------------------------
            # SINGLE / MULTIPLE CHOICE
            # --------------------------------------------------

            Prefetch(
                "choices",
                queryset=CourseChoice.objects.only(
                    "id",
                    "question_id",
                    "is_correct",
                ),
            ),

            # --------------------------------------------------
            # MATCHING
            # --------------------------------------------------

            Prefetch(
                "matching_pairs",
                queryset=MatchingPair.objects.only(
                    "id",
                    "question_id",
                    "left",
                    "right",
                    "order",
                ),
            ),

            # --------------------------------------------------
            # ARRANGE
            # --------------------------------------------------

            Prefetch(
                "arrange_items",
                queryset=ArrangeItem.objects.only(
                    "id",
                    "question_id",
                    "text",
                    "correct_position",
                ),
            ),

            # --------------------------------------------------
            # FILL BLANK
            # --------------------------------------------------

            Prefetch(
                "blanks",
                queryset=(
                    Blank.objects
                    .only(
                        "id",
                        "question_id",
                        "position",
                        "case_sensitive",
                    )
                    .prefetch_related(
                        Prefetch(
                            "answers",
                            queryset=BlankAnswer.objects.only(
                                "id",
                                "blank_id",
                                "answer",
                            ),
                        )
                    )
                ),
            ),
        )
        .afirst()
    )

    # ======================================================
    # 2. QUESTION TOPILMADIK
    # ======================================================

    if question is None:
        raise HTTPException(
            404,
            "Savol topilmadi",
        )

    # ======================================================
    # 3. COURSE ACCESS
    #
    # Question lessonda yoki testda bo'lishi mumkin.
    # ======================================================

    course = None

    if question.lesson_id:
        course = question.lesson.modul.course

    elif question.test_id:
        course = question.test.modul.course

    if course is None:
        raise HTTPException(
            400,
            "Savol hech qanday kursga tegishli emas",
        )

    await ensure_course_access(
        request_user.id,
        course,
    )

    # ======================================================
    # 4. TEST QUESTIONMI YOKI LESSON QUESTIONMI?
    # ======================================================

    session = None

    if question.test_id:

        # --------------------------------------------------
        # Test savoliga javob berayotgan bo'lsa,
        # aktiv sessionni aniqlaymiz.
        #
        # User session_id yubormaydi.
        # Backend question -> test -> active session orqali
        # topadi.
        # --------------------------------------------------

        session = await (
            CourseTestSession.objects
            .filter(
                user_id=request_user.id,
                test_id=question.test_id,
                completed_at__isnull=True,
            )
            .order_by("-started_at")
            .afirst()
        )

        if session is None:
            raise HTTPException(
                400,
                "Test seansi boshlanmagan",
            )

    # ======================================================
    # 5. OLDIN TO'G'RI YECHILGANMI?
    #
    # Lesson question:
    #     session IS NULL
    #
    # Test question:
    #     session = current test session
    #
    # Test savolida global "already done" tekshirmaymiz.
    # Chunki user keyingi test attemptida yana javob berishi
    # mumkin.
    # ======================================================

    existing_correct = await (
        CourseUserResponse.objects
        .filter(
            user_id=request_user.id,
            question_id=question.id,
            session=session,
            is_correct=True,
        )
        .aexists()
    )

    if existing_correct:

        return {
            "question_id": question.id,
            "correct": True,
            "xp": 0,
            "already_done": True,
            "explanation": question.explanation,
            "video": _question_video_data(question),
        }

    # ======================================================
    # 6. JAVOBNI VALIDATSIYA QILAMIZ
    # ======================================================

    q_type = question.question_type

    response = None

    # ======================================================
    # SINGLE CHOICE
    # ======================================================

    if q_type == CourseQuestion.QuestionType.SINGLE_CHOICE:

        if payload.choice_id is None:
            raise HTTPException(
                400,
                "choice_id talab qilinadi",
            )

        choice = await (
            CourseChoice.objects
            .filter(
                id=payload.choice_id,
                question_id=question.id,
            )
            .only(
                "id",
                "is_correct",
            )
            .afirst()
        )

        if choice is None:
            raise HTTPException(
                400,
                "Variant topilmadi",
            )

        response = CourseUserResponse(
            user=request_user,
            question=question,
            session=session,
            choice=choice,
        )

    # ======================================================
    # MULTIPLE CHOICE
    # ======================================================

    elif q_type == CourseQuestion.QuestionType.MULTIPLE_CHOICE:

        selected_ids = list(
            set(
                payload.selected_choice_ids or []
            )
        )

        if not selected_ids:
            raise HTTPException(
                400,
                "Kamida bitta variant tanlang",
            )

        choices = [
            choice
            async for choice in (
                CourseChoice.objects
                .filter(
                    question_id=question.id,
                    id__in=selected_ids,
                )
                .only(
                    "id",
                )
            )
        ]

        if len(choices) != len(selected_ids):
            raise HTTPException(
                400,
                "Noto'g'ri variant mavjud",
            )

        response = CourseUserResponse(
            user=request_user,
            question=question,
            session=session,
        )

        await sync_to_async(
            response.save,
            thread_sensitive=True,
        )()

        await sync_to_async(
            response.selected_choices.set,
            thread_sensitive=True,
        )(selected_ids)

    # ======================================================
    # MATCHING / ARRANGE / FILL
    # ======================================================

    elif q_type in (
        CourseQuestion.QuestionType.MATCHING,
        CourseQuestion.QuestionType.ARRANGE_WORDS,
        CourseQuestion.QuestionType.FILL_BLANKS,
    ):

        if not payload.answer_data:
            raise HTTPException(
                400,
                "answer_data talab qilinadi",
            )

        response = CourseUserResponse(
            user=request_user,
            question=question,
            session=session,
            answer_data=payload.answer_data,
        )

    # ======================================================
    # UNKNOWN TYPE
    # ======================================================

    else:

        raise HTTPException(
            400,
            "Noma'lum savol turi",
        )

    # ======================================================
    # 7. RESPONSE SAQLASH
    # ======================================================

    if response.pk is None:
        await sync_to_async(
            response.save,
            thread_sensitive=True,
        )()

    # ======================================================
    # 8. JAVOBNI TEKSHIRISH
    #
    # Sizdagi mavjud:
    #
    #     response.check_and_score()
    #
    # ishlatiladi.
    #
    # U:
    #     - is_answered
    #     - is_correct
    #
    # qaytaradi.
    # ======================================================

    is_answered, is_correct = await sync_to_async(
        response.check_and_score,
        thread_sensitive=True,
    )()

    # ======================================================
    # 9. XP
    # ======================================================

    xp = 0

    if is_correct:

        xp = question.xp

        # --------------------------------------------------
        # LESSON QUESTION
        #
        # Faqat lesson question bo'lsa lesson task
        # completion qilamiz.
        # --------------------------------------------------

        if question.lesson_id:

            try:

                await sync_to_async(
                    mark_lesson_task_completed,
                    thread_sensitive=True,
                )(
                    user_id=request_user.id,
                    lesson_id=question.lesson_id,
                )

            except Exception:

                logger.exception(
                    "lesson quiz completion error",
                    extra={
                        "user_id": request_user.id,
                        "question_id": question.id,
                    },
                )

        # --------------------------------------------------
        # XP
        # --------------------------------------------------

        try:
            if CourseUserResponse:
                with transaction.atomic():
                    response = (
                        CourseUserResponse.objects
                        .select_for_update()
                        .filter(
                            user_id=request_user.id,
                            question_id=question.id,
                        )
                        .first()
                    )

                    if response and not response.xp_awarded:
                        response.xp_awarded = True
                        response.save(update_fields=["xp_awarded"])

                        award_xp(
                            user=request_user,
                            xp_amount=xp,
                            source="quiz",
                        )

        except Exception:
            logger.exception(
                "quiz XP reward error",
                extra={
                    "user_id": request_user.id,
                    "question_id": question.id,
                },
            )
    # ======================================================
    # 10. RESPONSE
    # ======================================================

    return {
        "question_id": question.id,

        "correct": is_correct,

        "xp": xp,

        "already_done": False,

        "explanation": question.explanation,

        "video": _question_video_data(question),
    }