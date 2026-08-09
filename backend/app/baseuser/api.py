# apps/baseuser/api.py
"""
Foydalanuvchi profili, statistikasi, heatmap va faoliyat tarixi uchun API.

Endpointlar:
    GET /{tg_id_or_username}              -> Profil (public + owner-only maydonlar)
    GET /heatmap/{telegram_id}             -> GitHub-uslubidagi faollik xaritasi (cached)
    GET /history/{telegram_id}             -> Submission tarixi (cursor pagination, code YO'Q)
    GET /submissions/{submission_id}       -> Bitta submission to'liq tafsiloti (faqat egasiga code)
    GET /{tg_id_or_username}/activity      -> Submission + Test + Contest birlashgan lenta (cached)
    GET /{tg_id_or_username}/certificates  -> Foydalanuvchining barcha sertifikatlari
    GET /{tg_id_or_username}/courses       -> Foydalanuvchi a'zo bo'lgan kurslar + progress
"""

from datetime import datetime, timedelta

from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from django_bolt import JSON, Depends, Request, Router, status

from certificate.models import Certificate
from contests.models import ContestRegistration
from courses.models import Enrollment
from quizs.models import TestSession
from status.models import UserActivityDaily
from submissions.models import Submission

from .authenticate import get_current_user, get_current_user_option
from .models import BaseUser

api = Router(tags=["User api"])


# ============================================================
# CONSTANTS
# ============================================================

MAX_HEATMAP_DAYS = 730          # 2 yil — abuse'dan himoya
HEATMAP_CACHE_SECONDS = 60 * 30  # 30 daqiqa

MAX_HISTORY_PAGE_SIZE = 50
DEFAULT_HISTORY_PAGE_SIZE = 20

MAX_ACTIVITY_ITEMS = 30
DEFAULT_ACTIVITY_ITEMS = 15
ACTIVITY_CACHE_SECONDS = 60 * 2  # 2 daqiqa — profilga tez-tez kirishadi

CERTIFICATES_CACHE_SECONDS = 60 * 10   # 10 daqiqa — kam-kam o'zgaradi
COURSES_CACHE_SECONDS = 60 * 3         # 3 daqiqa — progress tez-tez o'zgaradi


# ============================================================
# HELPERS
# ============================================================

async def _resolve_user(tg_id_or_username: str, *, active_only: bool = True):
    """telegram_id yoki username bo'yicha BaseUser'ni topadi (yoki None qaytaradi)."""
    query = BaseUser.objects.all()
    if active_only:
        query = query.filter(is_active=True)

    if tg_id_or_username.isdigit():
        return await query.filter(
            Q(telegram_id=int(tg_id_or_username)) | Q(username__iexact=tg_id_or_username)
        ).order_by().afirst()

    return await query.filter(username__iexact=tg_id_or_username).order_by().afirst()


def _not_found(message: str = "Foydalanuvchi topilmadi"):
    return JSON({"detail": message}, status_code=status.HTTP_404_NOT_FOUND)


async def _aget_or_404(queryset, **kwargs):
    """
    Django'ning aget_object_or_404() o'rniga: obyekt topilmasa Django'ning
    HTML Http404'ini ko'tarmaydi (bu Django default error page chiqarib
    yuboradi), balki (None, JSON 404 javobi) qaytaradi — chaqiruvchi joyda
    ikkalasini ham tekshirish kifoya.

    Foydalanish:
        obj, err = await _aget_or_404(Submission.objects.select_related(...), id=submission_id)
        if err:
            return err
    """
    try:
        obj = await queryset.aget(**kwargs)
        return obj, None
    except queryset.model.DoesNotExist:
        return None, _not_found(f"{queryset.model._meta.verbose_name} topilmadi")
    except (ValueError, TypeError):
        # Masalan: telegram_id sifatida "abc" kabi noto'g'ri tur yuborilsa
        return None, JSON(
            {"detail": "Noto'g'ri so'rov parametri"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )


# ============================================================
# 1. PROFIL
# ============================================================

@api.get("/{tg_id_or_username}")
async def get_user_profile(
    request: Request,
    tg_id_or_username: str,
    request_user: BaseUser | None = Depends(get_current_user_option),
):
    """Foydalanuvchi profili. Shaxsiy maydonlar (phone) faqat egasiga ko'rinadi."""

    query = BaseUser.objects.filter(is_active=True).select_related("profile", "stats").order_by()

    if tg_id_or_username.isdigit():
        user = await query.filter(
            Q(telegram_id=int(tg_id_or_username)) | Q(username__iexact=tg_id_or_username)
        ).afirst()
    else:
        user = await query.filter(username__iexact=tg_id_or_username).afirst()

    if not user:
        return _not_found()

    is_owner = request_user is not None and request_user.id == user.id

    profile_data = None
    if hasattr(user, "profile") and user.profile:
        profile_data = {
            "avatar": user.profile.avatar.url if user.profile.avatar else None,
            "bio": user.profile.bio,
            "website": user.profile.website,
        }

    stats_data = None
    if hasattr(user, "stats") and user.stats:
        stats_data = {
            "xp": user.stats.xp,
            "level": user.stats.level,
        }

    return {
        "telegram_id": user.telegram_id,
        "username": user.username,
        "phone": user.phone if is_owner else None,  # Shaxsiy ma'lumot faqat egasiga ko'rinadi
        "full_name": user.full_name,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "is_owner": is_owner,
        "profile": profile_data,
        "stats": stats_data,
    }


# ============================================================
# 2. HEATMAP
# ============================================================

@api.get("/heatmap/{telegram_id}")
async def get_user_heatmap(request: Request, telegram_id: int, days: int = 365):
    """GitHub-uslubidagi kunlik faollik xaritasi + streak hisob-kitobi."""

    days = min(max(days, 1), MAX_HEATMAP_DAYS)

    cache_key = f"heatmap:{telegram_id}:{days}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    user_data = await BaseUser.objects.filter(
        telegram_id=telegram_id, is_active=True
    ).values("id").afirst()

    if not user_data:
        return _not_found()

    internal_user_id = user_data["id"]
    today = timezone.now().date()
    start_date = today - timedelta(days=days)

    rows = UserActivityDaily.objects.filter(
        user_id=internal_user_id,
        date__gte=start_date,
        date__lte=today,
    ).order_by("date").values_list("date", "tasks_count")

    heatmap_sparse = {}
    current_streak = 0
    max_streak = 0
    total_active_days = 0
    prev_date = None

    async for d, tasks in rows:
        if tasks > 0:
            heatmap_sparse[d.isoformat()] = tasks
            total_active_days += 1

            if prev_date is not None and (d - prev_date).days == 1:
                current_streak += 1
            else:
                current_streak = 1
            max_streak = max(max_streak, current_streak)
            prev_date = d
        else:
            current_streak = 0
            prev_date = d

    if prev_date is None or (today - prev_date).days > 1:
        current_streak = 0

    result = {
        "telegram_id": telegram_id,
        "start_date": start_date.isoformat(),
        "end_date": today.isoformat(),
        "total_active_days": total_active_days,
        "current_streak": current_streak,
        "max_streak": max_streak,
        "heatmap": heatmap_sparse,
    }

    cache.set(cache_key, result, timeout=HEATMAP_CACHE_SECONDS)
    return result


# ============================================================
# 3. SUBMISSION TARIXI (xavfsiz, paginatsiyalangan)
# ============================================================

@api.get("/history/{telegram_id}")
async def get_history(
    request: Request,
    telegram_id: str,
    cursor: str | None = None,
    limit: int = DEFAULT_HISTORY_PAGE_SIZE,
    verdict: str | None = None,
):
    """
    Submission tarixi ro'yxati.

    - `code` maydoni BU YERDA umuman qaytarilmaydi (xavfsizlik uchun).
      To'liq kodni ko'rish uchun /submissions/{submission_id} chaqiring.
    - cursor-based pagination: navbatdagi sahifa uchun `next_cursor`ni
      keyingi so'rovda `cursor` sifatida yuboring.
    - `verdict` bo'yicha ixtiyoriy filter: AC, WA, RE, TLE, MLE, CE.
    """

    limit = min(max(limit, 1), MAX_HISTORY_PAGE_SIZE)

    user, err = await _aget_or_404(BaseUser.objects.filter(is_active=True), telegram_id=telegram_id)
    if err:
        return err

    qs = (
        Submission.objects.filter(user=user)
        .select_related("problem", "language")
        .order_by("-submitted_at")
    )

    valid_verdicts = {"AC", "WA", "RE", "TLE", "MLE", "CE"}
    if verdict and verdict in valid_verdicts:
        qs = qs.filter(verdict=verdict)

    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
            qs = qs.filter(submitted_at__lt=cursor_dt)
        except ValueError:
            return JSON(
                {"detail": "Noto'g'ri cursor formati. ISO-8601 formatida bo'lishi kerak."},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    # limit+1 olib, keyingi sahifa bor-yo'qligini bilamiz — qo'shimcha count() so'ramasdan
    rows = [sub async for sub in qs[: limit + 1]]
    has_more = len(rows) > limit
    rows = rows[:limit]

    history_data = [
        {
            "id": sub.id,
            "problem": {
                "id": sub.problem_id,
                "title": sub.problem.title if sub.problem else "Noma'lum masala",
            },
            "language": sub.language.name if sub.language_id else None,
            "status": sub.status,
            "verdict": sub.verdict,
            "verdict_display": sub.get_verdict_display(),
            "progress": f"{sub.passed_test_count}/{sub.total_test_count}",
            "execution_time": sub.execution_time,
            "execution_memory": sub.execution_memory,
            "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
        }
        for sub in rows
    ]

    return {
        "results": history_data,
        "count": len(history_data),
        "has_more": has_more,
        "next_cursor": rows[-1].submitted_at.isoformat() if has_more and rows else None,
    }


# ============================================================
# 4. BITTA SUBMISSION TAFSILOTI (kod faqat egasiga)
# ============================================================

@api.get("/submissions/{submission_id}")
async def get_submission_detail(
    request: Request,
    submission_id: int,
    request_user: BaseUser | None = Depends(get_current_user_option),
):
    """
    Bitta submissionning to'liq tafsiloti.

    `code` va `test_results` faqat submission egasiga qaytariladi —
    boshqa foydalanuvchilar faqat umumiy metrikalarni ko'radi.
    """

    sub, err = await _aget_or_404(
        Submission.objects.select_related("problem", "language", "user"),
        id=submission_id,
    )
    if err:
        return err

    is_owner = request_user is not None and request_user.id == sub.user_id

    return {
        "id": sub.id,
        "problem": {
            "id": sub.problem_id,
            "title": sub.problem.title if sub.problem else "Noma'lum masala",
        },
        "language": sub.language.name if sub.language_id else None,
        "code": sub.code if is_owner else None,
        "test_results": sub.test_results if is_owner else None,
        "is_owner": is_owner,
        "status": sub.status,
        "verdict": sub.verdict,
        "verdict_display": sub.get_verdict_display(),
        "progress": f"{sub.passed_test_count}/{sub.total_test_count}",
        "execution_time": sub.execution_time,
        "execution_memory": sub.execution_memory,
        "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
    }


# ============================================================
# 5. PROFIL UCHUN BIRLASHGAN ACTIVITY FEED
# ============================================================

@api.get("/{tg_id_or_username}/activity")
async def get_profile_activity(
    request: Request,
    tg_id_or_username: str,
    limit: int = DEFAULT_ACTIVITY_ITEMS,
):
    """
    Submission + TestSession + ContestRegistration'ni bitta xronologik
    lentaga birlashtiradi (LeetCode/Codeforces profilidagi "recent
    activity" kabi). Profil sahifasida ko'rsatish uchun mo'ljallangan.
    """

    limit = min(max(limit, 1), MAX_ACTIVITY_ITEMS)

    user = await _resolve_user(tg_id_or_username)
    if not user:
        return _not_found()

    cache_key = f"activity:{user.id}:{limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    submissions = [
        {
            "type": "submission",
            "id": s.id,
            "title": s.problem.title if s.problem else "Noma'lum masala",
            "verdict": s.verdict,
            "verdict_display": s.get_verdict_display(),
            "timestamp": s.submitted_at,
        }
        async for s in Submission.objects.filter(user=user, status=True)
        .select_related("problem")
        .order_by("-submitted_at")[:limit]
    ]

    tests = [
        {
            "type": "test",
            "id": str(t.id),
            "title": t.test.title if t.test else "Noma'lum test",
            "xp": t.total_xp_earned,
            "score": t.score,
            "timestamp": t.completed_at,
        }
        async for t in TestSession.objects.filter(user=user, status=TestSession.Status.COMPLETED)
        .select_related("test")
        .order_by("-completed_at")[:limit]
    ]

    contests = [
        {
            "type": "contest",
            "id": str(c.id),
            "title": c.contest.title if c.contest else "Noma'lum musobaqa",
            "rank": c.rank,
            "xp": c.total_xp_earned,
            "timestamp": c.completed_at,
        }
        async for c in ContestRegistration.objects.filter(
            user=user, status=ContestRegistration.Status.COMPLETED
        )
        .select_related("contest")
        .order_by("-completed_at")[:limit]
    ]

    feed = sorted(
        (item for item in submissions + tests + contests if item["timestamp"]),
        key=lambda item: item["timestamp"],
        reverse=True,
    )[:limit]

    for item in feed:
        item["timestamp"] = item["timestamp"].isoformat()

    result = {
        "telegram_id": user.telegram_id,
        "username": user.username,
        "activity": feed,
        "count": len(feed),
    }

    cache.set(cache_key, result, timeout=ACTIVITY_CACHE_SECONDS)
    return result


# ============================================================
# 6. SERTIFIKATLAR
# ============================================================

@api.get("/{tg_id_or_username}/certificates")
async def get_user_certificates(request: Request, tg_id_or_username: str):
    """
    Foydalanuvchining barcha berilgan sertifikatlari (kurs / test / musobaqa).

    Faqat `status="completed"` bo'lgan (PDF muvaffaqiyatli tayyorlangan)
    sertifikatlar qaytariladi — hali jarayonda yoki xato bo'lganlari
    profilga chiqarilmaydi.
    """

    user = await _resolve_user(tg_id_or_username)
    if not user:
        return _not_found()

    cache_key = f"certificates:{user.id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    certs_qs = (
        Certificate.objects.filter(user=user, status="completed")
        .select_related("course", "test", "contest", "test_session", "contest_registration")
        .order_by("-issued_at")
    )

    certificates = []
    async for cert in certs_qs:
        certificates.append({
            "id": str(cert.id),
            "certificate_code": cert.certificate_code,
            "source_type": cert.source_type,           # course | test | contest | default
            "source_title": cert.source_title,
            "verify_url": cert.verify_url,
            "pdf_url": cert.pdf_file.url if cert.pdf_file else None,
            "issued_at": cert.issued_at.isoformat() if cert.issued_at else None,
        })

    result = {
        "telegram_id": user.telegram_id,
        "username": user.username,
        "certificates": certificates,
        "count": len(certificates),
    }

    cache.set(cache_key, result, timeout=CERTIFICATES_CACHE_SECONDS)
    return result


# ============================================================
# 7. A'ZO BO'LGAN KURSLAR (Enrollments)
# ============================================================

@api.get("/{tg_id_or_username}/courses")
async def get_user_courses(
    request: Request,
    tg_id_or_username: str,
    request_user: BaseUser | None = Depends(get_current_user_option),
    only_active: bool = False,
):
    """
    Foydalanuvchi a'zo (enroll) bo'lgan barcha kurslar, progress bilan.

    `is_paid` maydoni faqat profil egasiga ko'rsatiladi (to'lov holati
    shaxsiy ma'lumot hisoblanadi). `only_active=true` bo'lsa, faqat
    hali yakunlanmagan kurslar qaytariladi.
    """

    user = await _resolve_user(tg_id_or_username)
    if not user:
        return _not_found()

    is_owner = request_user is not None and request_user.id == user.id

    qs = (
        Enrollment.objects.filter(user=user)
        .select_related("course")
        .order_by("-created_at")
    )
    if only_active:
        qs = qs.filter(is_completed=False)

    courses = []
    async for enr in qs:
        if not enr.course:
            continue

        total_lessons = enr.course.total_lessons_count or 0
        total_tests = enr.course.total_test_count or 0
        total_units = total_lessons + total_tests
        finished_units = enr.finished_darslar_soni + enr.finished_test_soni
        progress_percent = (
            round((finished_units / total_units) * 100, 1) if total_units else 0
        )

        courses.append({
            "course": {
                "id": enr.course.id,
                "slug": enr.course.slug,
                "title": enr.course.title,
                "is_active": enr.course.is_active,
            },
            "is_paid": enr.is_paid if is_owner else None,
            "is_completed": enr.is_completed,
            "finished_lessons": enr.finished_darslar_soni,
            "total_lessons": total_lessons,
            "finished_tests": enr.finished_test_soni,
            "total_tests": total_tests,
            "progress_percent": progress_percent,
            "completed_at": enr.completed_at.isoformat() if enr.completed_at else None,
            "enrolled_at": enr.created_at.isoformat() if enr.created_at else None,
        })

    return {
        "telegram_id": user.telegram_id,
        "username": user.username,
        "courses": courses,
        "count": len(courses),
    }