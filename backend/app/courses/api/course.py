import copy
import logging
from typing import Annotated

import msgspec
from django.db.models import Prefetch
from django_bolt import Router, Request, Depends
from django_bolt.exceptions import HTTPException

from quizs.models import TestSession
from baseuser.authenticate import get_current_user_option
from baseuser.models import BaseUser
from courses.models import Course, Enrollment
from courses import cache as course_cache
from status.models import LessonStatus

logger = logging.getLogger(__name__)

api = Router(tags=["Course Ultra Optimized API"])

# ── Helpers ───────────────────────────────────────────────────────────────────

def safe_url(field) -> str | None:
    try:
        return field.url if field else None
    except ValueError:
        return None


def safe_float(value) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def progress_str(completed: int, total: int) -> str:
    """'5/20' formatida string — JSON da eng kam joy egallaydi"""
    return f"{completed}/{total}"


def calc_session_percentage(score: float, xp: int) -> float:
    if not xp:
        return 0.0
    return round(max(0.0, score / xp * 100), 1)


# ── Course List API ───────────────────────────────────────────────────────────

@api.get("/")
async def get_course_list_api(
    request: Request,
    request_user: BaseUser | None = Depends(get_current_user_option)
):
    """Kurslar ro'yxatini traffikni tejagan va asinxron holatda qaytaruvchi API"""
    static_list = course_cache.get_course_list_static()

    if not static_list:
        qs = (
            Course.objects
            .filter(is_active=True)
            .select_related('intro_video')
            .only(
                'id', 'title', 'slug', 'price', 'discount_price',
                'total_lessons_count', 'total_test_count',
                'intro_video__thumbnail'
            )
            .order_by('-id')
        )

        db_static_list = []
        async for course in qs:
            course_item = {
                "id": course.id,
                "title": course.title,
                "slug": course.slug,
                "price": safe_float(course.price) or 0,
                "content": {
                    "lessons": course.total_lessons_count or 0,
                    "tests": course.total_test_count or 0
                }
            }
            
            discount_val = safe_float(course.discount_price)
            if discount_val and discount_val < course_item["price"]:
                course_item["discount_price"] = discount_val

            if course.intro_video and course.intro_video.thumbnail:
                try:
                    course_item["thumbnail"] = course.intro_video.thumbnail.url
                except ValueError:
                    pass

            db_static_list.append(course_item)
        
        static_list = db_static_list
        course_cache.set_course_list_static(static_list)

    result_list = copy.deepcopy(static_list)
    course_ids = [c["id"] for c in result_list]

    # FOYDALANUVCHI PROGRESSINI JONLI TEKSHIRISH
    enrollment_map = {}
    if request_user and course_ids:
        # SynchronousOnlyOperation oldini olish uchun select_related('course') qo'shildi
        qs_enr = (
            Enrollment.objects
            .filter(user=request_user, course_id__in=course_ids)
            .select_related('course')
        )
        async for enr in qs_enr:
            total_items = (enr.course.total_lessons_count or 0) + (enr.course.total_test_count or 0)
            completed_items = (enr.finished_darslar_soni or 0) + (enr.finished_test_soni or 0)
            percentage = round((completed_items / total_items * 100), 1) if total_items > 0 else 0.0

            enrollment_map[enr.course_id] = {
                "is_paid": enr.is_paid,
                "lessons": enr.finished_darslar_soni or 0,
                "tests": enr.finished_test_soni or 0,
                "percent": percentage
            }
            if enr.is_completed:
                enrollment_map[enr.course_id]["is_completed"] = True

    # DATA MERGE — Faqat progress mavjud bo'lsagina kalit qo'shiladi
    for c in result_list:
        user_prog = enrollment_map.get(c["id"])
        if user_prog:
            c["progress"] = user_prog

    return result_list


# ── Course Detail Helpers ─────────────────────────────────────────────────────

async def _build_static(slug: str) -> dict | None:
    cached = course_cache.get_course_static(slug)
    if cached is not None:
        return cached

    course = await (
        Course.objects
        .filter(slug=slug, is_active=True)
        .select_related('intro_video')
        .prefetch_related(
            'modullar__lessons',
            'modullar__tests',
        )
        .afirst()
    )

    if not course:
        return None

    video_data = None
    if course.intro_video:
        v = course.intro_video
        video_data = {
            "src":      v.hls_url or safe_url(v.video),
            "thumb":    safe_url(v.thumbnail),
            "duration": v.duration,
        }

    modules = []
    for modul in course.modullar.all():
        lessons = [
            {
                "id":          lesson.id,
                "title":       lesson.title,
                "slug":        lesson.slug,
                "total_tasks": lesson.total_tasks_count,
            }
            for lesson in modul.lessons.all()
        ]
        tests = [
            {
                "id":               test.id,
                "title":            test.title,
                "slug":             test.slug,
                "duration_minutes": test.duration_minutes,
            }
            for test in modul.tests.all()
        ]
        modules.append({
            "id":      modul.id,
            "title":   modul.title,
            "slug":    modul.slug,
            "lessons": lessons,
            "tests":   tests,
        })

    data = {
        "id":             course.id,
        "title":          course.title,
        "description":    course.description,
        "slug":           course.slug,
        "price":          safe_float(course.price),
        "discount_price": safe_float(course.discount_price),
        "video":          video_data,
        "total_lessons":  course.total_lessons_count,
        "total_tests":    course.total_test_count,
        "modules":        modules,
    }

    course_cache.set_course_static(slug, data)
    return data


async def _build_user_data(slug: str, user: BaseUser, static: dict) -> dict:
    """
    User ga bog'liq dynamic ma'lumot.
    Cache TTL: 5 daqiqa + jitter.
    """
    cached = course_cache.get_course_user(slug, user.id)
    if cached is not None:
        return cached

    lesson_ids: list[int] = [
        lesson["id"]
        for modul in static["modules"]
        for lesson in modul["lessons"]
    ]
    test_ids: list[int] = [
        test["id"]
        for modul in static["modules"]
        for test in modul["tests"]
    ]

    # ── LessonStatus — bitta query ────────────────────────────────────
    lesson_status_map: dict[int, dict] = {}
    if lesson_ids:
        async for ls in LessonStatus.objects.filter(
            user=user,
            lesson_id__in=lesson_ids,
        ):
            lesson_status_map[ls.lesson_id] = {
                "finished_tasks": ls.finished_tasks_count,
                "is_completed":   ls.is_completed,
            }

    # ── TestSession — bitta query ─────────────────────────────────────
    test_session_map: dict[int, dict] = {}
    if test_ids:
        seen: set[int] = set()
        async for ts in (
            TestSession.objects
            .filter(
                user=user,
                test_id__in=test_ids,
                status=TestSession.Status.COMPLETED,
            )
            .order_by('test_id', '-started_at')
        ):
            if ts.test_id not in seen:
                seen.add(ts.test_id)
                test_session_map[ts.test_id] = {
                    "status":        ts.status,
                    "score":         ts.score,
                    "correct_count": ts.correct_count,
                    "wrong_count":   ts.wrong_count,
                    "xp_earned":     ts.total_xp_earned,
                    "percentage":    calc_session_percentage(ts.score, ts.total_xp_earned),
                }

    # ── Enrollment — bitta query ──────────────────────────────────────
    enrollment = await Enrollment.objects.filter(
        user=user,
        course__slug=slug,
    ).afirst()

    total_lessons     = static["total_lessons"]
    total_tests       = static["total_tests"]
    completed_lessons = sum(1 for ls in lesson_status_map.values() if ls["is_completed"])
    completed_tests   = len(test_session_map)

    data = {
        "is_paid":         enrollment.is_paid      if enrollment else False,
        "is_completed":    enrollment.is_completed if enrollment else False,
        "lesson_progress": progress_str(completed_lessons, total_lessons),
        "test_progress":   progress_str(completed_tests, total_tests),
        "lesson_statuses": lesson_status_map,
        "test_statuses":   test_session_map,
    }

    course_cache.set_course_user(slug, user.id, data)
    return data


def _merge(static: dict, user_data: dict | None) -> dict:
    """Static (Kesh) + Dynamic (User progress) ma'lumotlarni birlashtiradi"""
    is_paid         = False
    is_completed    = False
    lesson_progress = progress_str(0, static["total_lessons"])
    test_progress   = progress_str(0, static["total_tests"])
    lesson_statuses: dict = {}
    test_statuses:   dict = {}

    if user_data:
        is_paid         = user_data.get("is_paid", False)
        is_completed    = user_data.get("is_completed", False)
        lesson_statuses = user_data.get("lesson_statuses", {})
        test_statuses   = user_data.get("test_statuses", {})
        lesson_progress = user_data.get("lesson_progress", lesson_progress)
        test_progress   = user_data.get("test_progress", test_progress)

    modules = []
    for modul in static["modules"]:
        lessons = [
            {
                **lesson,
                "finished_tasks": lesson_statuses.get(str(lesson["id"]), lesson_statuses.get(lesson["id"], {})).get("finished_tasks", 0),
                "is_completed":   lesson_statuses.get(str(lesson["id"]), lesson_statuses.get(lesson["id"], {})).get("is_completed", False),
            }
            for lesson in modul["lessons"]
        ]
        tests = [
            {
                **test,
                "status":        test_statuses.get(str(test["id"]), test_statuses.get(test["id"], {})).get("status"),
                "score":         test_statuses.get(str(test["id"]), test_statuses.get(test["id"], {})).get("score"),
                "correct_count": test_statuses.get(str(test["id"]), test_statuses.get(test["id"], {})).get("correct_count", 0),
                "wrong_count":   test_statuses.get(str(test["id"]), test_statuses.get(test["id"], {})).get("wrong_count", 0),
                "xp_earned":     test_statuses.get(str(test["id"]), test_statuses.get(test["id"], {})).get("xp_earned", 0),
                "percentage":    test_statuses.get(str(test["id"]), test_statuses.get(test["id"], {})).get("percentage"),
            }
            for test in modul["tests"]
        ]
        modules.append({**modul, "lessons": lessons, "tests": tests})

    return {
        "id":              static["id"],
        "title":           static["title"],
        "description":     static["description"],
        "slug":            static["slug"],
        "price":           static["price"],
        "discount_price":  static["discount_price"],
        "video":           static["video"],
        "is_paid":         is_paid,
        "is_completed":    is_completed,
        "lesson_progress": lesson_progress,
        "test_progress":   test_progress,
        "modules":         modules,
    }


# ── Course Detail API Endpoint ────────────────────────────────────────────────

@api.get("/{slug}")
async def get_course_detail_api(
    slug: str,
    request_user: BaseUser | None = Depends(get_current_user_option)
):
    """
    Slug bo'yicha Kurs tafsilotlarini qaytaruvchi asinxron API.
    Ma'lumotlar o'ta yuqori tezlikda kesh karkasiga joylanadi.
    """
    static_data = await _build_static(slug)
    if not static_data:
        raise HTTPException(status_code=404, detail="Kurs topilmadi.")

    static_skeleton = copy.deepcopy(static_data)

    user_data = None
    if request_user:
        user_data = await _build_user_data(slug, request_user, static_skeleton)

    return _merge(static_skeleton, user_data)
