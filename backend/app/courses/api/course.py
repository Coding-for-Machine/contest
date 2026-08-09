# courses/api.py
import copy
import logging
from datetime import date
from typing import Annotated

from django.db.models.functions import Cast
import msgspec
from asgiref.sync import sync_to_async
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q, Case, Count, ExpressionWrapper, FloatField, Prefetch, Value, When
from django.utils import timezone

from django_bolt import Router, Depends, Request
from django_bolt.exceptions import HTTPException
from django_bolt.middleware import rate_limit
from django_bolt.params import Query

from courses.access import ensure_course_access
from problems.models import Challenge, Function, Hint, Language, Problem, Tags, TestCase
from quizs.models import Choice, Question, UserResponse
from submissions.models import Submission
from baseuser.models import BaseUser
from baseuser.authenticate import get_current_user_option, get_current_user

from courses.models import Course, Lecture, Modul, Lesson, Enrollment
from .cache import (
    get_course_list_static,
    set_course_list_static,
    get_course_detail_static,
    set_course_detail_static,
    get_course_user_cache,
    set_course_user_cache,
)
from status.models import (
    CourseStatus,
    LectureStatus,
    LessonStatus,
    ModuleStatus,
    ProblemStatus,
    UserStats,
)
from status.services import award_xp

logger = logging.getLogger(__name__)
api = Router(tags=["Courses"])


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
            "total_lessons_count", "total_test_count",
            "intro_video__hls_url", "intro_video__thumbnail", "intro_video__duration",
        )
    )


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
                "title": c.title,
                "slug": c.slug,
                "price": float(c.price),
                "discount_price": float(c.discount_price) if c.discount_price else None,
                "thumbnail": (
                    c.intro_video.thumbnail.url
                    if c.intro_video and c.intro_video.thumbnail else None
                ),
                "total_lessons": c.total_lessons_count,
                "total_tests": c.total_test_count,
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
        c["is_paid"] = enrollments.get(cid, False)
        st = statuses.get(cid)
        c["completed_lessons"] = st.completed_lessons if st else 0
        c["completed_tests"] = st.completed_tests if st else 0
        c["is_completed"] = st.is_completed if st else False

    return result


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
    """Kurs detali: modullar, darslar, video, user status."""
    data = get_course_detail_static(slug)

    if data is None:
        course = await _course_detail_qs(slug).afirst()
        if not course:
            raise HTTPException(404, "Kurs topilmadi")

        modules = []
        for module in course.modullar.all():
            lessons = []
            for lesson in module.lessons.all():
                lessons.append({
                    "id": lesson.id,
                    "title": lesson.title,
                    "slug": lesson.slug,
                    "order": lesson.order,
                    "total_tasks": lesson.total_tasks_count,
                })
            modules.append({
                "id": module.id,
                "title": module.title,
                "slug": module.slug,
                "order": module.order,
                "lessons": lessons,
            })

        data = {
            "id": course.id,
            "title": course.title,
            "slug": course.slug,
            "description": course.description,
            "price": float(course.price),
            "discount_price": float(course.discount_price) if course.discount_price else None,
            "video": {
                "hls_url": course.intro_video.hls_url if course.intro_video else None,
                "thumbnail": (
                    course.intro_video.thumbnail.url
                    if course.intro_video and course.intro_video.thumbnail else None
                ),
                "duration": course.intro_video.duration if course.intro_video else None,
            },
            "total_lessons": course.total_lessons_count,
            "total_tests": course.total_test_count,
            "modules": modules,
        }
        set_course_detail_static(slug, data)

    result = copy.deepcopy(data)

    if not user:
        return result

    course_id = result["id"]
    user_data = get_course_user_cache(slug, user.id)

    if user_data is None:
        lesson_ids = [l["id"] for m in result["modules"] for l in m["lessons"]]

        lesson_statuses = {}
        async for ls in LessonStatus.objects.filter(user=user, lesson_id__in=lesson_ids).only(
            "lesson_id", "is_completed", "finished_tasks_count"
        ):
            lesson_statuses[ls.lesson_id] = {
                "is_completed": ls.is_completed,
                "finished_tasks": ls.finished_tasks_count,
            }

        status = await CourseStatus.objects.filter(user=user, course_id=course_id).afirst()

        user_data = {
            "lesson_statuses": lesson_statuses,
            "completed_lessons": status.completed_lessons if status else 0,
            "completed_tests": status.completed_tests if status else 0,
            "is_completed": status.is_completed if status else False,
        }
        set_course_user_cache(slug, user.id, user_data)

    for m in result["modules"]:
        for l in m["lessons"]:
            st = user_data["lesson_statuses"].get(l["id"])
            l["user_status"] = st if st else {"is_completed": False, "finished_tasks": 0}

    result["user_progress"] = {
        "is_paid": await Enrollment.objects.filter(
            user=user, course_id=course_id, is_paid=True
        ).aexists(),
        "completed_lessons": user_data["completed_lessons"],
        "completed_tests": user_data["completed_tests"],
        "is_completed": user_data["is_completed"],
    }

    return result


# ==========================================================
# 3. KURSGA YOZILISH (BEPUL)
# ==========================================================
from django_bolt import JSON

@api.post("/{slug}/enroll")
@rate_limit(rps=5, burst=10)
async def enroll_course(
    request: Request,
    slug: str,
    request_user: BaseUser = Depends(get_current_user),
):
    """
    Bepul kurs uchun — to'g'ridan-to'g'ri kursga yozadi.
    Pullik kurs uchun — Enrollment yaratmaydi, to'lovga yo'naltirish uchun ma'lumot qaytaradi.
    Haqiqiy pullik yozilish faqat payment webhook orqali (mark_transaction_paid) amalga oshadi.
    """
    course = await Course.objects.filter(
        slug=slug, is_active=True
    ).only("id", "price", "discount_price").afirst()

    if not course:
        raise HTTPException(404, "Kurs topilmadi")

    enrollment = await Enrollment.objects.filter(
        user_id=request_user.id, course_id=course.id
    ).afirst()

    if enrollment:
        return {
            "enrolled": True,
            "is_paid": enrollment.is_paid,
        }

    if course.current_price > 0:
        return JSON(
            {
                "payment_req": True,
                "amount": str(course.current_price),
            },
            status_code=402,
        )

    enrollment = await Enrollment.objects.acreate(
        user_id=request_user.id,
        course_id=course.id,
        is_paid=True,
    )

    return {
        "enrolled": True,
        "is_paid": enrollment.is_paid,
    }

# ==========================================================
# 4. DARS DETALI
# ==========================================================

@api.get("/lesson/{slug}/")
@rate_limit(rps=10, burst=20)
async def get_lesson(
    request: Request,
    slug: str,
    request_user: BaseUser | None = Depends(get_current_user_option),
):
    """Dars detali: lectures, problems, quizzes + user status."""
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
                    "id", "lesson_id", "title", "slug", "order"
                ).order_by("order"),
            ),
            Prefetch(
                "problems",
                queryset=Problem.objects.only(
                    "id", "lesson_id", "title", "slug", "is_active", "xp"
                ).order_by("id"),
            ),
            Prefetch(
                "quiz_questions",
                queryset=Question.objects.only(
                    "id", "lesson_id", "order", "difficulty", "xp"
                ).order_by("order"),
            ),
        )
        .afirst()
    )

    if not lesson:
        raise HTTPException(404, "Dars topilmadi")
    await ensure_course_access(request_user.id, lesson.modul.course)
    
    # OLDINGI DARS TEKSHIRUVI
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

    if prev_lesson:
        prev_done = await LessonStatus.objects.filter(
            user=request_user, lesson=prev_lesson, is_completed=True
        ).aexists()
        if not prev_done:
            raise HTTPException(403, "Avval oldingi darsni to'liq tugating")

    # STATUS
    lesson_status = await LessonStatus.objects.filter(
        user=request_user, lesson=lesson
    ).only("finished_tasks_count", "is_completed").afirst()

    completed_lectures = {
        pk async for pk in LectureStatus.objects.filter(
            user=request_user, lecture__lesson=lesson, is_completed=True
        ).values_list("lecture_id", flat=True)
    }

    completed_questions = {
        pk async for pk in UserResponse.objects.filter(
            user=request_user, question__lesson=lesson, session__isnull=True
        ).values_list("question_id", flat=True).distinct()
    }

    completed_problems = {
        pk async for pk in ProblemStatus.objects.filter(
            user=request_user, problem__lesson=lesson, solved=True
        ).values_list("problem_id", flat=True)
    }

    return {
        "id": lesson.id,
        "title": lesson.title,
        "slug": lesson.slug,
        "course_id": lesson.modul.course_id,
        "modul_id": lesson.modul_id,
        "total_tasks": lesson.total_tasks_count,
        "user_status": {
            "finished_tasks": lesson_status.finished_tasks_count if lesson_status else 0,
            "is_completed": lesson_status.is_completed if lesson_status else False,
        },
        "lectures": [
            {
                "id": lec.id,
                "title": lec.title,
                "slug": lec.slug,
                "order": lec.order,
                "is_completed": lec.id in completed_lectures,
            }
            for lec in lesson.lectures.all()
        ],
        "problems": [
            {
                "id": p.id,
                "title": p.title,
                "slug": p.slug,
                "xp": p.xp,
                "is_completed": p.id in completed_problems,
            }
            for p in lesson.problems.all() if p.is_active
        ],
        "questions": [
            {
                "id": q.id,
                "order": q.order,
                "difficulty": q.difficulty,
                "xp": q.xp,
                "is_completed": q.id in completed_questions,
            }
            for q in lesson.quiz_questions.all()
        ],
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
    .filter(
        lesson__slug=slug,
        slug=lecture_slug
    )
    .select_related(
        "video",
        "lesson__modul__course",
    )
    .only(
        "id",
        "title",
        "body",
        "xp",
        "reading_time",

        "lesson__id",
        "lesson__modul__id",
        "lesson__modul__course__id",

        "video__hls_url",
        "video__video",
        "video__thumbnail",
        "video__duration",
    )
    .afirst()
)
    if not lecture:
        raise HTTPException(404, "Ma'ruza topilmadi")
    
    await ensure_course_access(request_user.id, lecture.lesson.modul.course)

    lecture_status = await LectureStatus.objects.filter(
        user=request_user,
        lecture=lecture
    ).afirst()

    if not lecture_status:
        lecture_status = await LectureStatus.objects.acreate(
            user=request_user,
            lecture=lecture,
            started_at=timezone.now()
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
from datetime import timedelta

from status.services import (
    mark_lesson_task_completed,
    award_xp,
)


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
    .filter(
        lesson__slug=slug,
        slug=lecture_slug
    )
    .select_related(
        "lesson__modul__course"
    )
    .only(
        "id",
        "xp",
        "reading_time",
        "lesson__id",
        "lesson__modul__id",
        "lesson__modul__course__id",
    )
    .afirst()
)

    if not lecture:
        raise HTTPException(404, "Ma'ruza topilmadi")


    await ensure_course_access(
    request_user.id,
    lecture.lesson.modul.course
)

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
            raise HTTPException(
                403,
                "Ma'ruzani tugatish uchun vaqt yetarli emas"
            )

    status.is_completed = True
    status.completed_at = now

    await status.asave(
        update_fields=["is_completed", "completed_at"]
    )

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
# 7. QUIZ SAVOL
# ==========================================================
# ==========================================================
# 7. QUIZ SAVOL
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
        raise HTTPException(
            401,
            "Tizimga kirish talab qilinadi"
        )


    question = await (
        Question.objects
        .filter(
            id=question_id,
            lesson__slug=slug,
        )
        .select_related(
            "lesson__modul__course",
        )
        .prefetch_related(
            Prefetch(
                "choices",
                queryset=Choice.objects.only(
                    "id",
                    "text",
                )
            )
        )
        .only(
            "id",
            "text",
            "difficulty",
            "xp",

            # Course relation uchun kerak
            "lesson__modul__course__id",
            "lesson__modul__course__price",
            "lesson__modul__course__discount_price",
        )
        .afirst()
    )


    if not question:
        raise HTTPException(
            404,
            "Savol topilmadi"
        )


    # Kurs access tekshiruvi
    await ensure_course_access(
        request_user.id,
        question.lesson.modul.course,
    )


    done = await (
        UserResponse.objects
        .filter(
            user=request_user,
            question_id=question.id,
            session__isnull=True,
            choice__is_correct=True,
        )
        .aexists()
    )


    choices = (
        question
        ._prefetched_objects_cache
        .get("choices", [])
    )


    return {
        "id": question.id,
        "text": question.text,
        "dif": question.difficulty,
        "xp": question.xp,
        "done": done,

        "choices": [
            {
                "id": choice.id,
                "text": choice.text,
            }
            for choice in choices
        ],
    }



# ==========================================================
# 8. QUIZ JAVOB
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
        raise HTTPException(
            401,
            "Tizimga kirish talab qilinadi"
        )


    question = await (
        Question.objects
        .filter(
            id=question_id,
            lesson__slug=slug,
        )
        .select_related(
            "lesson__modul__course",
            "explanation_video",
        )
        .only(
            "id",
            "lesson_id",
            "xp",

            # Course access uchun
            "lesson__modul__course__id",
            "lesson__modul__course__price",
            "lesson__modul__course__discount_price",

            # Video
            "explanation_video__hls_url",
            "explanation_video__thumbnail",
            "explanation_video__duration",
        )
        .afirst()
    )


    if not question:
        raise HTTPException(
            404,
            "Savol topilmadi"
        )


    await ensure_course_access(
        request_user.id,
        question.lesson.modul.course,
    )


    choice = await (
        Choice.objects
        .filter(
            id=payload.choice_id,
            question_id=question.id,
        )
        .only(
            "id",
            "is_correct",
            "explanation",
        )
        .afirst()
    )


    if not choice:
        raise HTTPException(
            400,
            "Variant topilmadi"
        )


    old = await (
        UserResponse.objects
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

        await UserResponse.objects.acreate(
            user=request_user,
            question=question,
            choice=choice,
        )


        if choice.is_correct:

            xp = question.xp

            try:

                await sync_to_async(
                    mark_lesson_task_completed,
                    thread_sensitive=True,
                )(
                    user_id=request_user.id,
                    lesson_id=question.lesson_id,
                )


                await sync_to_async(
                    award_xp,
                    thread_sensitive=True,
                )(
                    user=request_user,
                    xp_amount=xp,
                    source="quiz",
                )


            except Exception:

                logger.exception(
                    "quiz reward error"
                )


    video = None


    if question.explanation_video:

        video = {
            "url": question.explanation_video.hls_url,

            "img": (
                question.explanation_video.thumbnail.url
                if question.explanation_video.thumbnail
                else None
            ),

            "time": question.explanation_video.duration,
        }


    return {
        "ans": {
            "id": choice.id,
            "correct": choice.is_correct,
        },

        "xp": xp,

        "exp": choice.explanation,

        "video": video,
    }

    
# ==========================================================
# 9. MENING KURSLARIM
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
            "title": e.course.title,
            "slug": e.course.slug,
            "thumbnail": (
                e.course.intro_video.thumbnail.url
                if e.course.intro_video and e.course.intro_video.thumbnail else None
            ),
            "is_paid": e.is_paid,
            "enrolled_at": e.created_at.isoformat() if e.created_at else None,
            "completed_lessons": status.completed_lessons if status else 0,
            "completed_tests": status.completed_tests if status else 0,
            "is_completed": status.is_completed if status else False,
            "total_lessons": e.course.total_lessons_count,
            "total_tests": e.course.total_test_count,
        })

    return result


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
        # Faqat shu lessonga bog'langan, aktiv masala olinadi
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

            # Kirish huquqini tekshirish uchun kerakli minimal ma'lumot
            "lesson_id": problem.lesson_id,
            "course_id": problem.lesson.modul.course_id,
        }
        cache.set(static_cache_key, base_data, timeout=600)

    # =================================================================
    # 2. KIRISH HUQUQI — masala lessonga bog'langani uchun har doim tekshiriladi
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