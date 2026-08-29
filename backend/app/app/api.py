from django_bolt import BoltAPI, Depends, Request
from django_bolt.openapi import OpenAPIConfig
from django.core.cache import cache
from django.db.models import Count, Q, Avg, F, Window
from django.db.models.functions import RowNumber, Coalesce
from decouple import config
from asgiref.sync import sync_to_async

from baseuser.models import BaseUser
from baseuser.authenticate import get_current_user, get_current_user_option
from problems.models import Problem
from contests.models import Contest
from quizs.models import Test, TestSession
from courses.models import Course

SECRET_KEY = config('AUTH_SECRET_KEY')

api = BoltAPI(
    openapi_config=OpenAPIConfig(
        title="CfM Contest API",
        version="1.0.0",
    )
)

# ============================================================
# ASYNC CACHE WRAPPERS
# ============================================================
get_cached_data = sync_to_async(cache.get, thread_sensitive=True)
set_cached_data = sync_to_async(cache.set, thread_sensitive=True)
delete_cached_data = sync_to_async(cache.delete, thread_sensitive=True)


@api.get("/me")
async def get_my_account_info(
    request: Request,
    current_user: BaseUser = Depends(get_current_user)
):
    return {
        "id": int(current_user.id),
        "telegram_id": int(current_user.telegram_id),
        "username": current_user.username or "",
        "phone": current_user.phone or "",
        "full_name": current_user.full_name or "",
        "is_active": bool(current_user.is_active)
    }


# ============================================================
# HOME PAGE (INDEX) API — index.html'ga aynan mos, minimal
# ------------------------------------------------------------
# Frontend (index.html + main.js) shu javobni kutadi, ortiqcha
# hech narsa yo'q — leaderboard va courses UI'da ishlatilmagani
# uchun bu yerda ham yo'q:
#   data.stats.{users, problems, tests, contests}
#   data.tests[]     -> renderTests()
#   data.problems[]  -> renderProblems()
#   data.contests[]  -> renderContests()
# ============================================================
@api.get("/api/v1/index")
async def get_index_data(request: Request):
    cache_key = "index_page_data"

    cached_data = await get_cached_data(cache_key)
    if cached_data is not None:
        return cached_data

    # ------------------------------------------------------------
    # 1. STATISTIKA — UI'dagi hero-stat va feature-card sonlari
    #    "lessons" faqat feature-card'dagi "N+ dars" uchun kerak —
    #    kurslar ro'yxati o'zi olinmaydi, faqat yagona agregat son.
    # ------------------------------------------------------------
    get_lessons_count = sync_to_async(
        lambda: Course.objects.filter(is_active=True).aggregate(
            total=Count('modullar__lessons', distinct=True)
        )['total'] or 0,
        thread_sensitive=True
    )

    stats = {
        "users": await BaseUser.objects.filter(is_active=True).acount(),
        "problems": await Problem.objects.filter(is_active=True).acount(),
        "tests": await Test.objects.filter(is_active=True).acount(),
        "contests": await Contest.objects.filter(is_active=True).acount(),
        "lessons": await get_lessons_count(),
    }

    # ------------------------------------------------------------
    # 2. SO'NGGI 3 TA TEST
    # ------------------------------------------------------------
    recent_tests_qs = Test.objects.filter(is_active=True).annotate(
        total_sessions=Count('sessions'),
        completed_sessions=Count('sessions', filter=Q(sessions__status=TestSession.Status.COMPLETED)),
        avg_score=Coalesce(Avg('sessions__score', filter=Q(sessions__status=TestSession.Status.COMPLETED)), 0.0)
    ).order_by('-created_at')[:3]

    tests_data = []
    async for test in recent_tests_qs:
        tests_data.append({
            "slug": test.slug,
            "title": test.title,
            "question_count": test.question_count or 0,
            "duration_minutes": test.duration_minutes or 0,
            "min_pass_percentage": test.min_pass_percentage or 60,
            "sessions_count": test.total_sessions,
            "completed_count": test.completed_sessions,
            "avg_score": round(test.avg_score, 1),
            "is_available": test.is_available,
        })

    # ------------------------------------------------------------
    # 3. SO'NGGI MASALALAR — EASY/MEDIUM/HARD'dan bittadan (SQL darajasida)
    # ------------------------------------------------------------
    problems_window_qs = Problem.objects.filter(is_active=True).annotate(
        row_num=Window(
            expression=RowNumber(),
            partition_by=[F('difficulty')],
            order_by=F('id').desc()
        )
    )

    recent_problems_qs = Problem.objects.filter(
        id__in=problems_window_qs.filter(row_num=1).values('id')
    ).select_related('category').annotate(
        total_subs=Count('submissions'),
        accepted_subs=Count('submissions', filter=Q(submissions__status=True))
    ).order_by('difficulty', '-id')

    problems_data = []
    async for problem in recent_problems_qs:
        acceptance = round((problem.accepted_subs / problem.total_subs) * 100, 1) if problem.total_subs else 0
        problems_data.append({
            "slug": problem.slug,
            "title": problem.title,
            "difficulty": problem.difficulty.upper(),
            "category": problem.category.name if problem.category else "Umumiy",
            "xp": problem.xp or 10,
            "acceptance": acceptance,
            "solutions": problem.total_subs,
        })

    # ------------------------------------------------------------
    # 4. YAQINLASHAYOTGAN 2 TA MUSOBAQA
    # ------------------------------------------------------------
    upcoming_contests_qs = Contest.objects.filter(is_active=True, status='upcoming').prefetch_related(
        'prizes'
    ).annotate(
        part_count=Count('registrations', distinct=True)
    ).order_by('start_time')[:2]

    contests_data = []
    async for contest in upcoming_contests_qs:
        all_prizes = list(contest.prizes.all())
        prize_name = all_prizes[0].title if all_prizes else ""

        duration_hours = 0
        if contest.start_time and contest.end_time:
            duration_hours = round((contest.end_time - contest.start_time).total_seconds() / 3600)

        contests_data.append({
            "slug": contest.slug,
            "title": contest.title,
            "is_open": contest.type == 'open',
            "problems_count": contest.questions_count or 0,
            "duration": duration_hours,
            "participants": contest.part_count,
            "prize": prize_name,
            "start_date": contest.start_time.strftime("%d-%b, %Y") if contest.start_time else "",
        })

    # ------------------------------------------------------------
    # 5. JAMLANISH VA KESHGA YOZISH
    # ------------------------------------------------------------
    response_data = {
        "stats": stats,
        "tests": tests_data,
        "problems": problems_data,
        "contests": contests_data,
    }

    await set_cached_data(cache_key, response_data, timeout=3600 * 5)
    return response_data


@api.post("/api/v1/index/invalidate-cache")
async def invalidate_index_cache(request: Request):
    await delete_cached_data("index_page_data")
    return {"message": "Cache tozalandi"}


# ============================================================
# ROUTERLARNI ULASH
# ============================================================
from courses.api.course import api as course_api
from problems.api.problem import api as problem_api
from app.sse.api import sse_api
from submissions.api import api as submit_api
# from quizs.api.tests import api as tests_api
from quizs.api.session import session_api
from baseuser.api import api as user_api
from status.api import api_status
from notifications.api import api_notification
from payment.api import api as payment_api
# from contests.api.contests import api as contest_api

api.include_router(sse_api, prefix="/api/v1/sse")
api.include_router(course_api, prefix="/api/v1/courses")

api.include_router(problem_api, prefix="/api/v1/problems")
api.include_router(submit_api, prefix="/api/v1/code")
# test
# api.include_router(tests_api, prefix="/api/v1/tests")
# api.include_router(session_api, prefix="/api/v1/test-session")
# user
api.include_router(user_api, prefix="/api/v1/user")
# status
api.include_router(api_status, prefix="/api/v1/status")
# api_notifications
api.include_router(api_notification, prefix="/api/v1/notifications")
# payment
api.include_router(payment_api, prefix="/api/v1/payment")
# contests
# api.include_router(contest_api, prefix="/api/v1/contests")
