from typing import List, Optional, Annotated

import msgspec
from django_bolt import Router, Request, Depends
from django_bolt.params import Query
from asgiref.sync import sync_to_async
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone
from django.http import Http404

from baseuser.models import BaseUser
from baseuser.authenticate import get_current_user_option
from quizs.models import Test, TestSession, TestEnrollment
from django_bolt.serializers import Serializer

api = Router(tags=["Test API v3"])


# =========================================================
#                     SERIALIZERLAR
# =========================================================
class UserListStats(Serializer):
    """Ro'yxat sahifasida foydalanuvchining ushbu testdagi qisqa statistikasi."""
    att: int            # nechta urinish qilgan
    status: str          # oxirgi seans holati
    score: float          # eng yaxshi ball
    xp: int             # jami yig'ilgan XP


class TestsListSerializer(Serializer):
    """`GET /` — testlar ro'yxati uchun javob shakli."""
    id: int
    title: str
    slug: str
    time: int
    qty: int
    start: Optional[str] = None
    end: Optional[str] = None
    img: Optional[str] = None
    user: Optional[UserListStats] = None
    buy: Optional[bool] = None


class UserDetailStats(Serializer):
    """Batafsil sahifada foydalanuvchi statistikasi."""
    count: int
    status: str
    score: float
    xp: int


class VideoSerializer(Serializer):
    """Testning kirish/qoidalar videosi haqida ma'lumot."""
    id: str
    img: Optional[str] = None
    len: Optional[str] = None  # duration CharField ekanligi uchun str
    hls: Optional[str] = None


class TestsDetailSerializer(Serializer):
    """`GET /{slug}` — bitta test haqida to'liq ma'lumot."""
    id: int
    title: str
    slug: str
    des: str | None
    time: int
    qty: int
    rand: bool
    min_pass_percentage: int
    max_att: int
    penalty: float
    lifelines: int
    start: Optional[str] = None
    end: Optional[str] = None
    video: Optional[VideoSerializer] = None
    user: Optional[UserDetailStats] = None
    buy: Optional[bool] = None
    price: Optional[float] = None


class ModuleOptionSerializer(Serializer):
    """Filtr uchun: yakuniy testi bor bo'lim (modul)."""
    id: int
    name: str


# =========================================================
#                  YORDAMCHI FUNKSIYALAR
# =========================================================

def _build_video_data(test: Test, is_paid: bool, is_purchased: bool) -> Optional[dict]:
    """Test bilan bog'liq video ma'lumotini shakllantiradi (HLS faqat sotib olinganlarga ko'rinadi)."""
    if not test.intro_video:
        return None

    video_data = {
        "id": str(test.intro_video.id),
        "img": test.intro_video.thumbnail.url if test.intro_video.thumbnail else None,
        "len": test.intro_video.duration,  # CharField -> string holatida
        "hls": None,
    }

    # HLS faqat sotib olingan yoki bepul testlar uchun
    if not is_paid or is_purchased:
        video_data["hls"] = test.intro_video.hls_url

    return video_data


def _compute_display_qty(test: Test) -> int:
    """Foydalanuvchiga ko'rsatiladigan savollar sonini hisoblaydi (random yoki to'liq)."""
    is_rand = test.random_questions_count > 0 and test.question_count > test.random_questions_count
    return test.random_questions_count if is_rand else test.question_count


# =========================================================
#     0. FILTRLASH UCHUN YORDAMCHI RO'YXAT (GET /modules/)
#        — problems ilovasidagi categories/tags ekvivalenti
# =========================================================
@api.get("/modules/")
async def list_modules_with_tests(request: Request):
    """
    Yakuniy (bob/modul) testi mavjud bo'lgan modullar ro'yxati — frontendda
    filtr sifatida ishlatish uchun. Natija qisqa muddat keshlanadi.

    Eslatma: ``courses.Modul`` modelining aniq maydon nomi noma'lum bo'lgani
    uchun ``str(modul)`` (ya'ni modelning ``__str__``i) nom sifatida
    ishlatiladi. Agar Modul'da ``title``/``name`` maydoni bo'lsa va aynan
    o'shani chiqarish kerak bo'lsa, ``str(m.modul)`` o'rniga ``m.modul.title``
    (yoki mos maydon) ga almashtiring.
    """
    cache_key = "tests_available_modules_v1"
    modules = await cache.aget(cache_key)

    if modules is None:
        def _fetch():
            seen = {}
            qs = (
                Test.objects.filter(modul__isnull=False, is_active=True)
                .select_related("modul")
                .only("modul_id", "modul")
            )
            for t in qs:
                if t.modul_id not in seen:
                    seen[t.modul_id] = str(t.modul)
            return [{"id": mid, "name": name} for mid, name in seen.items()]

        modules = await sync_to_async(_fetch, thread_sensitive=True)()
        await cache.aset(cache_key, modules, timeout=300)

    return modules


# =========================================================
#           1. TESTLAR RO'YXATI (SCROLL PAGINATSIYA)
# =========================================================
class FilterParams(msgspec.Struct):
    limit: int = 10
    offset: int = 0
    search: str | None = None
    is_free: bool | None = None       # True = faqat bepul, False = faqat pullik
    only_available: bool | None = None  # True = hozir ochiq (vaqt oynasi ichida) testlar


class PaginatedResponse(msgspec.Struct):
    total: int
    limit: int
    offset: int
    items: List[TestsListSerializer]
    # Eslatma: keyingi offset yoki "oxirimi" degan maydonlar ATAYLAB yo'q —
    # frontend buni o'zi hisoblaydi: keyingi so'rov uchun offset + limit,
    # "boshqa sahifa yo'q" belgisi esa len(items) < limit.


def _apply_common_filters(queryset, params: "FilterParams"):
    """Ro'yxat va sanoq (count) so'rovlarida bir xil filtrlar qo'llanishi uchun umumiy funksiya."""
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
    request_user: BaseUser | None = Depends(get_current_user_option),
):
    # 1. OPTIMAL KESH: har qanday filtr (search, is_free, only_available) bo'lsa
    #    kesh butunlay aylanib o'tiladi — filtrlangan natija boshqa foydalanuvchiga
    #    yoki boshqa so'rovga noto'g'ri qaytmasligi uchun.
    use_cache = (
        params.search is None
        and params.is_free is None
        and params.only_available is None
    )
    cache_key = f"tests_list_{params.limit}_off_{params.offset}"

    tests_list = await cache.aget(cache_key) if use_cache else None

    if not tests_list:
        queryset = Test.objects.filter(modul__isnull=True, is_active=True).select_related(
            "intro_video"
        ).only(
            "id", "title", "slug", "duration_minutes", "question_count",
            "random_questions_count", "start_time", "end_time", "price",
            "intro_video_id",
            "intro_video__thumbnail",
        )

        queryset = _apply_common_filters(queryset, params)
        queryset = queryset.order_by("-id")[params.offset : params.offset + params.limit]

        tests_list = []
        async for t in queryset:
            img_url = t.intro_video.thumbnail.url if (t.intro_video and t.intro_video.thumbnail) else None

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

    # 2. FOYDALANUVCHI STATUSI (Dinamik qism — hech qachon keshlanmaydi)
    results = []

    if request_user and tests_list:
        current_page_ids = [t["id"] for t in tests_list]

        user_sessions_dict = {}
        async for sess in TestSession.objects.filter(
            user=request_user, test_id__in=current_page_ids
        ).values("test_id", "status", "score", "total_xp_earned"):
            user_sessions_dict.setdefault(sess["test_id"], []).append(sess)

        purchased_ids = {
            pid
            async for pid in TestEnrollment.objects.filter(
                user=request_user, test_id__in=current_page_ids
            ).values_list("test_id", flat=True)
        }

        for t in tests_list:
            user_stats = None
            sessions = user_sessions_dict.get(t["id"])
            if sessions:
                user_stats = UserListStats(
                    att=len(sessions),
                    status=sessions[-1]["status"],
                    score=max(s["score"] for s in sessions),
                    xp=sum(s["total_xp_earned"] for s in sessions),
                )

            buy_status = None
            if t["price"] > 0:
                buy_status = t["id"] in purchased_ids

            results.append(TestsListSerializer(
                id=t["id"], title=t["title"], slug=t["slug"], time=t["time"], qty=t["qty"],
                start=t["start"], end=t["end"], img=t["img"], user=user_stats, buy=buy_status,
            ))
    else:
        for t in tests_list:
            buy_status = False if t["price"] > 0 else None
            results.append(TestsListSerializer(
                id=t["id"], title=t["title"], slug=t["slug"], time=t["time"], qty=t["qty"],
                start=t["start"], end=t["end"], img=t["img"], user=None, buy=buy_status,
            ))

    # 3. UMUMIY SANOQ
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
    request_user: BaseUser | None = Depends(get_current_user_option),
):
    def fetch_test_detail():
        try:
            return (
                Test.objects.select_related("intro_video")
                .only(
                    "id", "title", "description", "slug", "duration_minutes", "question_count",
                    "random_questions_count", "min_pass_percentage", "max_attempts",
                    "penalty_coefficient", "max_lifelines", "start_time", "end_time",
                    "price", "is_active",
                    "intro_video__id", "intro_video__thumbnail",
                    "intro_video__hls_url", "intro_video__duration",
                )
                .get(slug=slug, modul__isnull=True, is_active=True)
            )
        except Test.DoesNotExist:
            return None

    test = await sync_to_async(fetch_test_detail, thread_sensitive=True)()
    if not test:
        raise Http404()

    is_paid = float(test.price) > 0
    is_purchased = False
    user_stats = None

    if request_user:
        def fetch_user_detail_data():
            sessions = list(
                TestSession.objects.filter(user=request_user, test=test).values(
                    "status", "score", "total_xp_earned"
                )
            )
            purchased = TestEnrollment.objects.filter(
                user=request_user, test=test
            ).exists()
            return sessions, purchased

        sessions, is_purchased = await sync_to_async(
            fetch_user_detail_data, thread_sensitive=True
        )()

        if sessions:
            user_stats = {
                "count": len(sessions),
                "status": sessions[-1]["status"],
                "score": max(s["score"] for s in sessions),
                "xp": sum(s["total_xp_earned"] for s in sessions),
            }

    video_data = _build_video_data(test, is_paid, is_purchased)

    res = {
        "id": test.id,
        "title": test.title,
        "slug": test.slug,
        "des": test.description,
        "time": test.duration_minutes,
        "qty": _compute_display_qty(test),
        "rand": test.random_questions_count > 0
        and test.question_count > test.random_questions_count,
        "min_pass_percentage": test.min_pass_percentage,
        "max_att": test.max_attempts,
        "penalty": test.penalty_coefficient,
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