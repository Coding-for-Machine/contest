from typing import List, Optional, Annotated

import msgspec
from django_bolt import Router, Request, Depends
from django_bolt.params import Query
from django_bolt.exceptions import NotFound
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from baseuser.models import BaseUser
from baseuser.authenticate import get_current_user_option
from quizs.models import Test, TestSession, TestEnrollment
from django_bolt.serializers import Serializer

api = Router(tags=["Test API v1"])


# =========================================================
#                     SERIALIZERLAR
# =========================================================

class UserListStats(Serializer):
    """Test ro'yxatida ko'rinadigan foydalanuvchi statistikasi."""
    att: int                          # Urinishlar soni
    status: str                       # Oxirgi status
    theta: float                      # Rasch θ (logit)
    se: float                         # Standard Error
    raw_pct: float                    # Oddiy foiz (to'g'ri/berilgan × 100)
    progress: float                   # θ ning 0-100 vizual mapping'i
    xp: int
    passed: bool                      # O'tish chegarasidan oshganmi?


class TestsListSerializer(Serializer):
    """Testlar ro'yxati uchun serializer."""
    id: int
    title: str
    slug: str
    time: int                         # Davomiylik (daqiqa)
    qty: int                          # Savollar soni
    start: Optional[str] = None
    end: Optional[str] = None
    img: Optional[str] = None
    price: float = 0.0
    user: Optional[UserListStats] = None
    buy: Optional[bool] = None        # True = sotib olingan, False = sotib olinmagan, None = bepul


class UserDetailStats(Serializer):
    """Test batafsil sahifasida ko'rinadigan statistika."""
    count: int                        # Urinishlar soni
    status: str                       # Oxirgi status
    theta: float                      # Eng yaxshi θ
    se: float                         # Eng yaxshi SE
    raw_pct: float                    # Oxirgi oddiy foiz
    progress: float                   # Eng yaxshi progress (0-100)
    xp: int                           # Jami XP
    passed: bool                      # Hech bo'lmaganda bir marta o'tganmi?


class VideoSerializer(Serializer):
    id: str
    img: Optional[str] = None
    len: Optional[str] = None
    hls: Optional[str] = None


class TestsDetailSerializer(Serializer):
    """Test batafsil ma'lumotlari."""
    id: int
    title: str
    slug: str
    des: Optional[str] = None
    time: int
    qty: int
    rand: bool                        # Tasodifiy savollar bormi?
    pass_threshold: float             # Rasch θ o'tish chegarasi (logit)
    max_att: int                      # Maksimal urinishlar
    lifelines: int
    start: Optional[str] = None
    end: Optional[str] = None
    video: Optional[VideoSerializer] = None
    user: Optional[UserDetailStats] = None
    buy: Optional[bool] = None
    price: Optional[float] = None


# =========================================================
#                  YORDAMCHI FUNKSIYALAR
# =========================================================

def _build_video_data(test: Test, is_paid: bool, is_purchased: bool) -> Optional[dict]:
    if not test.intro_video:
        return None

    video_data = {
        "id": str(test.intro_video.id),
        "img": test.intro_video.thumbnail.url if test.intro_video.thumbnail else None,
        "len": test.intro_video.duration,
        "hls": None,
    }

    if not is_paid or is_purchased:
        video_data["hls"] = test.intro_video.hls_url

    return video_data


def _compute_display_qty(test: Test) -> int:
    """Foydalanuvchiga ko'rsatiladigan savollar soni."""
    is_rand = test.random_questions_count > 0 and test.question_count > test.random_questions_count
    return test.random_questions_count if is_rand else test.question_count


def _build_user_list_stats(sessions: list) -> Optional[UserListStats]:
    if not sessions:
        return None

    latest = sessions[-1]

    theta_sessions = [
        s for s in sessions
        if s.get("rasch_theta") is not None
    ]

    best_session = max(
        theta_sessions,
        key=lambda s: s["rasch_theta"],
        default=latest,
    )

    pass_threshold = latest.get(
        "test__rasch_theta_pass_threshold", 0.0
    )

    passed = any(
        s.get("rasch_theta") is not None
        and s["rasch_theta"] >= pass_threshold
        for s in sessions
    )

    latest_theta = latest.get("rasch_theta")
    latest_se = latest.get("rasch_se")

    progress = 0.0
    if latest_theta is not None:
        progress = max(
            0.0,
            min(
                100.0,
                (latest_theta + 4.0) / 8.0 * 100.0,
            ),
        )

    return UserListStats(
        att=len(sessions),
        status=latest["status"],
        theta=round(float(latest_theta or 0.0), 2),
        se=round(float(latest_se or 999.0), 2),
        raw_pct=round(float(latest.get("raw_percentage") or 0.0), 1),
        progress=round(progress, 1),
        xp=sum(s.get("total_xp_earned") or 0 for s in sessions),
        passed=passed,
    )

def _build_user_detail_stats(
    sessions: list,
    pass_threshold: float,
) -> Optional[UserDetailStats]:
    """Sessionlar ro'yxatidan UserDetailStats yaratadi."""

    if not sessions:
        return None

    latest = sessions[-1]

    # Rasch theta hisoblangan sessionlar
    theta_sessions = [
        s for s in sessions
        if s.get("rasch_theta") is not None
    ]

    # Eng yaxshi Rasch natija
    if theta_sessions:
        best_session = max(
            theta_sessions,
            key=lambda s: float(s["rasch_theta"]),
        )

        best_theta = float(best_session["rasch_theta"])
        best_se = best_session.get("rasch_se")

        progress = max(
            0.0,
            min(
                100.0,
                (best_theta + 4.0) / 8.0 * 100.0,
            ),
        )
    else:
        # Session mavjud, lekin Rasch hali hisoblanmagan
        best_theta = 0.0
        best_se = 999.0
        progress = 0.0

    # Hech bo'lmaganda bir marta o'tganmi?
    passed = any(
        s.get("rasch_theta") is not None
        and float(s["rasch_theta"]) >= float(pass_threshold)
        for s in sessions
    )

    return UserDetailStats(
        count=len(sessions),
        status=latest.get("status", ""),
        theta=round(best_theta, 2),
        se=round(float(best_se or 999.0), 2),
        raw_pct=round(
            float(latest.get("raw_percentage") or 0.0),
            1,
        ),
        progress=round(progress, 1),
        xp=sum(
            int(s.get("total_xp_earned") or 0)
            for s in sessions
        ),
        passed=passed,
    )

# =========================================================
#     0. FILTRLASH UCHUN YORDAMCHI RO'YXAT (GET /modules/)
# =========================================================
@api.get("/modules/")
async def list_modules_with_tests(request: Request):
    cache_key = "tests_available_modules_v1"
    modules = await cache.aget(cache_key)

    if modules is None:
        modules = []
        seen = {}
        qs = (
            Test.objects.filter(modul__isnull=False, is_active=True)
            .select_related("modul")
            .only("modul_id", "modul__title")
        )
        async for t in qs:
            if t.modul_id not in seen:
                seen[t.modul_id] = str(t.modul)
        
        modules = [{"id": mid, "name": name} for mid, name in seen.items()]
        await cache.aset(cache_key, modules, timeout=300)

    return modules


# =========================================================
#           1. TESTLAR RO'YXATI (SCROLL PAGINATSIYA)
# =========================================================
class FilterParams(msgspec.Struct):
    limit: int = 10
    offset: int = 0
    search: Optional[str] = None
    is_free: Optional[bool] = None
    only_available: Optional[bool] = None


class PaginatedResponse(msgspec.Struct):
    total: int
    limit: int
    offset: int
    items: List[TestsListSerializer]


def _apply_common_filters(queryset, params: FilterParams):
    if params.search:
        queryset = queryset.filter(
            Q(title__icontains=params.search) | Q(slug__icontains=params.search)
        )
    if params.is_free is True:
        queryset = queryset.filter(price=0)
    elif params.is_free is False:
        queryset = queryset.filter(price__gt=0)
    if params.only_available:
        now = timezone.now()
        queryset = queryset.filter(start_time__lte=now, end_time__gte=now)
    return queryset


@api.get("/", response_model=PaginatedResponse)
async def get_test_list_api(
    request: Request,
    params: Annotated[FilterParams, Query()],
    request_user: Optional[BaseUser] = Depends(get_current_user_option),
):
    use_cache = (
        params.search is None
        and params.is_free is None
        and params.only_available is None
    )
    cache_key = f"tests_list_{params.limit}_off_{params.offset}"

    tests_list = await cache.aget(cache_key) if use_cache else None

    if not tests_list:
        queryset = (
            Test.objects.filter(modul__isnull=True, is_active=True)
            .select_related("intro_video")
            .only(
                "id", "title", "slug", "duration_minutes", "question_count",
                "random_questions_count", "start_time", "end_time", "price",
                "intro_video_id", "intro_video__thumbnail",
            )
        )

        queryset = _apply_common_filters(queryset, params)
        queryset = queryset.order_by("-id")[params.offset : params.offset + params.limit]

        tests_list = []
        async for t in queryset:
            img_url = (
                t.intro_video.thumbnail.url
                if (t.intro_video and t.intro_video.thumbnail)
                else None
            )

            tests_list.append({
                "id": t.id,
                "title": t.title,
                "slug": t.slug,
                "time": t.duration_minutes,
                "qty": _compute_display_qty(t),
                "start": t.start_time.isoformat() if t.start_time else None,
                "end": t.end_time.isoformat() if t.end_time else None,
                "img": img_url,
                "price": float(t.price),
            })

        if use_cache:
            await cache.aset(cache_key, tests_list, timeout=300)

    results = []

    if request_user and tests_list:
        current_page_ids = [t["id"] for t in tests_list]

        # Foydalanuvchi sessionlari (Rasch maydonlari bilan)
        user_sessions_dict = {}
        async for sess in TestSession.objects.filter(
            user=request_user, test_id__in=current_page_ids
        ).values(
            "test_id", "status", "rasch_theta", "rasch_se",
            "raw_percentage", "total_xp_earned",
            "test__rasch_theta_pass_threshold",
        ):
            user_sessions_dict.setdefault(sess["test_id"], []).append(sess)

        purchased_ids = {
            pid
            async for pid in TestEnrollment.objects.filter(
                user=request_user, test_id__in=current_page_ids
            ).values_list("test_id", flat=True)
        }

        for t in tests_list:
            sessions = user_sessions_dict.get(t["id"])
            user_stats = _build_user_list_stats(sessions) if sessions else None

            buy_status = None
            if t["price"] > 0:
                buy_status = t["id"] in purchased_ids

            results.append(TestsListSerializer(
                id=t["id"],
                title=t["title"],
                slug=t["slug"],
                time=t["time"],
                qty=t["qty"],
                start=t["start"],
                end=t["end"],
                img=t["img"],
                price=t["price"],
                user=user_stats,
                buy=buy_status,
            ))
    else:
        for t in tests_list:
            buy_status = False if t["price"] > 0 else None
            results.append(TestsListSerializer(
                id=t["id"],
                title=t["title"],
                slug=t["slug"],
                time=t["time"],
                qty=t["qty"],
                start=t["start"],
                end=t["end"],
                img=t["img"],
                price=t["price"],
                user=None,
                buy=buy_status,
            ))

    if use_cache:
        total_count = await cache.aget("tests_total_count")
        if total_count is None:
            total_count = await Test.objects.filter(modul__isnull=True, is_active=True).acount()
            await cache.aset("tests_total_count", total_count, timeout=300)
    else:
        count_queryset = Test.objects.filter(modul__isnull=True, is_active=True)
        count_queryset = _apply_common_filters(count_queryset, params)
        total_count = await count_queryset.acount()

    return PaginatedResponse(
        total=total_count,
        limit=params.limit,
        offset=params.offset,
        items=results,
    )


# =========================================================
#                2. TEST DETAIL API (BATAFSIL)
# =========================================================
@api.get("/{slug}", response_model=TestsDetailSerializer)
async def get_test_detail_api(
    request: Request,
    slug: str,
    request_user: Optional[BaseUser] = Depends(get_current_user_option),
):
    try:
        test = await (
            Test.objects
            .select_related("intro_video")
            .only(
                "id", "title", "description", "slug", "duration_minutes",
                "question_count", "random_questions_count",
                "rasch_theta_pass_threshold", "max_attempts",
                "max_lifelines", "start_time", "end_time",
                "price", "is_active",
                "intro_video__id", "intro_video__thumbnail",
                "intro_video__hls_url", "intro_video__duration",
            )
            .aget(slug=slug, modul__isnull=True, is_active=True)
        )
    except Test.DoesNotExist:
        raise NotFound(detail="Test topilmadi")

    is_paid = float(test.price) > 0
    is_purchased = False
    user_stats = None

    if request_user:
        sessions = []
        async for sess in TestSession.objects.filter(
            user=request_user, test=test
        ).values(
            "status", "rasch_theta", "rasch_se",
            "raw_percentage", "total_xp_earned",
        ):
            sessions.append(sess)

        is_purchased = await TestEnrollment.objects.filter(
            user=request_user, test=test
        ).aexists()

        if sessions:
            user_stats = _build_user_detail_stats(
                sessions, test.rasch_theta_pass_threshold
            )

    video_data = _build_video_data(test, is_paid, is_purchased)

    res = {
        "id": test.id,
        "title": test.title,
        "slug": test.slug,
        "des": test.description,
        "time": test.duration_minutes,
        "qty": _compute_display_qty(test),
        "rand": (
            test.random_questions_count > 0
            and test.question_count > test.random_questions_count
        ),
        "pass_threshold": test.rasch_theta_pass_threshold,
        "max_att": test.max_attempts,
        "lifelines": test.max_lifelines,
        "start": test.start_time.isoformat() if test.start_time else None,
        "end": test.end_time.isoformat() if test.end_time else None,
        "video": video_data,
        "user": user_stats,
    }

    if is_paid:
        res["buy"] = is_purchased
        if not is_purchased:
            res["price"] = float(test.price)

    return res


# =========================================================
#                3. HERO API
# =========================================================
KEY = "hero:test"
TTL = 3600


@api.get("/hero/")
async def hero():
    cached = await cache.aget(KEY)
    if cached is not None:
        return cached
    
    now = timezone.now()
    test = await (
        Test.objects
        .filter(is_active=True)
        .filter(
            Q(start_time__lte=now, end_time__gte=now)
            | Q(start_time__gt=now)
        )
        .select_related("intro_video")
        .order_by("start_time", "id")
        .afirst()
    )

    if not test:
        data = None
    else:
        video = test.intro_video

        data = {
            "id": str(test.id),
            "title": test.title,
            "slug": test.slug,
            "desc": test.description,
            "duration": test.duration_minutes,
            "questions": test.question_count,
            "random": test.random_questions_count,
            "pass_threshold": test.rasch_theta_pass_threshold,
            "attempts": test.max_attempts,
            "code": bool(test.access_code),
            "start": test.start_time.isoformat(),
            "end": test.end_time.isoformat(),
            "price": str(test.price),
            "sale": (
                str(test.discount_price)
                if test.discount_price is not None
                else None
            ),
            "lifelines": test.max_lifelines,
            "video": (
                {
                    "url": (
                        video.hls_url
                        or (video.video.url if video.video else None)
                    ),
                    "thumb": (
                        video.thumbnail.url
                        if video.thumbnail
                        else None
                    ),
                    "duration": video.duration,
                }
                if video
                else None
            ),
        }
    
    await cache.aset(KEY, data, TTL)
    return data