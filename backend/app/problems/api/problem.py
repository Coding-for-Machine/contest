import random

import msgspec
from typing import Annotated, Literal
from django_bolt import Router, Request, Depends,  LimitOffsetPagination, paginate
from django_bolt.params import Query
from django_bolt.exceptions import HTTPException
from django.core.cache import cache

from django.db.models import Prefetch, Count, Q, ExpressionWrapper, FloatField, Case, When, Value
from django.db.models.functions import Cast


from problems.models import Like, Problem, Category, Tags, Hint, Challenge, Function, Language, TestCase
from submissions.models import Submission
from baseuser.authenticate import get_current_user_option
from baseuser.models import BaseUser

api = Router(tags=["Problem api"])


# =================================================================
# 1. RANDOM — /{slug}/ dan OLDIN yozilishi SHART!
# =================================================================

class RandomParams(msgspec.Struct):
    exclude_slug: str | None = None


@api.get("/random/")
async def get_random_problem(
    request: Request,
    params: Annotated[RandomParams, Query()],
):
    queryset = Problem.objects.filter(is_active=True, lesson_id__isnull=True)

    if params.exclude_slug:
        queryset = queryset.exclude(slug=params.exclude_slug)

    count = await queryset.acount()
    if count == 0:
        raise HTTPException(status_code=404, detail="Mavjud masala topilmadi")

    random_offset = random.randint(0, count - 1)
    problem = await queryset[random_offset : random_offset + 1].only(
        "slug", "title"
    ).afirst()

    if not problem:
        raise HTTPException(status_code=404, detail="Masala topilmadi")

    return {"slug": problem.slug, "title": problem.title}


# =================================================================
# 2. NAVIGATION — Prev / Next
# =================================================================

class NavigationParams(msgspec.Struct):
    direction: Literal["prev", "next"]


@api.get("/{slug}/navigation/")
async def get_problem_navigation(
    request: Request,
    slug: str,
    params: Annotated[NavigationParams, Query()],
):
    current_id = await (
        Problem.objects
        .filter(slug=slug, is_active=True, lesson_id__isnull=True)
        .values_list("id", flat=True)
        .afirst()
    )

    if not current_id:
        raise HTTPException(status_code=404, detail="Masala topilmadi")

    if params.direction == "prev":
        neighbor = await (
            Problem.objects
            .filter(is_active=True, lesson_id__isnull=True, id__lt=current_id)
            .order_by("-id")
            .only("slug", "title")
            .afirst()
        )
    else:
        neighbor = await (
            Problem.objects
            .filter(is_active=True, lesson_id__isnull=True, id__gt=current_id)
            .order_by("id")
            .only("slug", "title")
            .afirst()
        )

    if not neighbor:
        raise HTTPException(status_code=404, detail="Qo'shni masala topilmadi")

    return {"slug": neighbor.slug, "title": neighbor.title}


# =================================================================
# 3. QOLGAN ENDPOINTLAR (avvalgidek)
# =================================================================
# @api.get("/")
# @api.get("/{slug}/")
# ...

# =================================================================
# 3. AVVALGI ENDPOINTLAR (o'zgarmaydi, faqat tartib muhim)
# =================================================================

# Eslatma: /random/ va /{slug}/navigation/  >>>  /{slug}/  dan OLDIN
# turishi kerak, aks holda "random" slug sifatida tutib qolinadi.

# @api.get("/")
# async def list_problems(...): ...

# @api.get("/{slug}/")
# async def get_problem(...): ...

# http://localhost:8000/api/v1/problems/categories/
@api.get("/categories/")
async def list_categories(request: Request):
    return [
        {"id": c.id, "name": c.name, "slug": c.slug}
        async for c in Category.objects.only('id', 'name', 'slug').order_by('name')
    ]

# http://localhost:8000/api/v1/problems/tags/
@api.get("/tags/")
async def list_tags(request: Request):
    return [
        {"id": t.id, "name": t.name}
        async for t in Tags.objects.only('id', 'name').order_by('name')
    ]


MAX_LIMIT = 50  # bir so'rovda maksimal necha ta element (DoS'dan himoya)

class FilterParams(msgspec.Struct):
    limit: Annotated[int, msgspec.Meta(ge=1, le=MAX_LIMIT)] = 20
    offset: Annotated[int, msgspec.Meta(ge=0)] = 0
    search: str | None = None
    category_id: int | None = None
    tag_id: int | None = None
    difficulty: Literal["easy", "medium", "hard"] | None = None


class PaginationParams(msgspec.Struct):
    limit: Annotated[int, msgspec.Meta(ge=1, le=MAX_LIMIT)] = 10
    offset: Annotated[int, msgspec.Meta(ge=0)] = 0

# http://localhost:8000/api/v1/problems/
# problems list page uchin
@api.get("/")
async def list_problems(
    request: Request,
    params: Annotated[FilterParams, Query()],
    request_user: BaseUser | None = Depends(get_current_user_option),
):
    # 1. OPTIMAL KESH: Agar birorta filter ishlatilsa, kesh ishlamaydi (dinamik ma'lumot uchun)
    use_cache = (
        params.search is None
        and params.category_id is None
        and params.tag_id is None
        and params.difficulty is None
    )
    cache_key = f"problems_list_{params.limit}_off_{params.offset}"

    problems_list = cache.get(cache_key) if use_cache else None

    if not problems_list:
        # 2. BAZADAN MA'LUMOTLARNI YUKLASH (ZeroDivisionError va DivisionByZero xatolari tuzatildi)
        queryset = Problem.objects.filter(is_active=True, lesson_id__isnull=True).annotate(
            total_subs=Count("submissions"),
            correct_subs=Count("submissions", filter=Q(submissions__status=True))
        ).annotate(
            # Case va When orqali 0 ga bo'linish xavfsizligi ta'minlandi
            calculated_acceptance=Case(
                When(total_subs=0, then=Value(0.0)),  # Agar urinishlar 0 bo'lsa, foiz ham 0.0 bo'ladi
                default=ExpressionWrapper(
                    Cast("correct_subs", FloatField()) / Cast("total_subs", FloatField()) * 100,
                    output_field=FloatField()
                ),
                output_field=FloatField()
            )
        ).select_related(
            "category"
        ).prefetch_related(
            "tags"
        ).only(
            "id", "title", "slug", "difficulty", "xp", "category_id", "category__name"
        )

        # 3. FILTERS: Qidiruv va munosabatlar bo'yicha filtrlash
        if params.search:
            queryset = queryset.filter(title__icontains=params.search)
            
        if params.category_id:
            queryset = queryset.filter(category_id=params.category_id)
            
        if params.tag_id:
            queryset = queryset.filter(tags__id=params.tag_id)
        # list_problems'da:
        if params.difficulty:
            queryset = queryset.filter(difficulty=params.difficulty)
        # 4. ORDER_BY va PAGINATSIYA
        queryset = queryset.order_by("-id")[params.offset : params.offset + params.limit]
        
        # Olingan ma'lumotlarni ro'yxatga joylash
        problems_list = []
        async for p in queryset:
            tags_list = [f"#{t.name.lower()}" if not t.name.startswith('#') else t.name async for t in p.tags.all()]
            
            problems_list.append({
                "id": p.id,
                "slug": p.slug,
                "title": p.title,
                "difficulty": p.difficulty,
                "xp": p.xp,
                "acceptance": round(p.calculated_acceptance), 
                "category": p.category.name if p.category else None,
                "tags": tags_list,
            })

        if use_cache:
            cache.set(cache_key, problems_list, timeout=300)

    # 5. FOYDALANUVCHI STATUSI (Masala yechilganligini aniqlash)
    if request_user and problems_list:
        current_page_ids = [p["id"] for p in problems_list]
        solved_ids = {
            pid
            async for pid in Submission.objects.filter(
                user_id=request_user.id,
                problem_id__in=current_page_ids,
                status=True,
            ).values_list("problem_id", flat=True)
        }
        results = [
            {
                **p, 
                "solved": p["id"] in solved_ids,
            } for p in problems_list
        ]
    else:
        results = [
            {
                **p, 
                "solved": False,
            } for p in problems_list
        ]

    # 6. UMUMIY SANOQ
    if use_cache:
        total_count = cache.get("problems_total_count")
        if total_count is None:
            total_count = await Problem.objects.filter(is_active=True, lesson_id__isnull=True).acount()
            cache.set("problems_total_count", total_count, timeout=300)
    else:
        count_queryset = Problem.objects.filter(is_active=True, lesson_id__isnull=True)
        if params.search:
            count_queryset = count_queryset.filter(title__icontains=params.search)
        if params.category_id:
            count_queryset = count_queryset.filter(category_id=params.category_id)
        if params.tag_id:
            count_queryset = count_queryset.filter(tags__id=params.tag_id)
        total_count = await count_queryset.acount()

    return {
        "count": total_count,
        "limit": params.limit,
        "offset": params.offset,
        "data": results,
    }


# http://localhost:8000/api/v1/problems/{slug}/
# problems detail page uchin
@api.get("/{slug}/")
async def get_problem(
    request: Request, 
    slug: str, 
    request_user: BaseUser | None = Depends(get_current_user_option)
):
    # =================================================================
    # 1. STATIK KESH (BASE DATA) - 10 MINUT (600s)
    # =================================================================
    static_cache_key = f"problem_detail_static_{slug}"
    base_data = cache.get(static_cache_key)

    if not base_data:
        # Masalaning o'zgarmas og'ir qismlarini bazadan bir marta yuklaymiz
        problem = await (
            Problem.objects
            .filter(slug=slug, is_active=True)
            .select_related('category')
            .prefetch_related(
                Prefetch('tags',        queryset=Tags.objects.only('id', 'name')),
                Prefetch('hints',       queryset=Hint.objects.only('id', 'text')),
                Prefetch('challenges',  queryset=Challenge.objects.only('id', 'text')),
                Prefetch('language',    queryset=Language.objects.only('id', 'name', 'version')),
                Prefetch('functions',   queryset=Function.objects.only('id', 'function', 'language_id')),
                Prefetch('test_cases',  queryset=TestCase.objects.filter(is_sample=True).only('id', 'problem_id', 'input_txt', 'output_txt', 'explanation'))
            )
            .only(
                'id', 'title', 'slug', 'description', 'difficulty', 'xp', 
                'time_limit', 'memory_limit', 'category__name'
            )
            .afirst()
        )

        if not problem:
            raise HTTPException(status_code=404, detail="Masala topilmadi!")

        base_data = {
            "id":           problem.id,
            "title":        problem.title,
            "slug":         problem.slug,
            "desc":         problem.description,
            "dif":          problem.difficulty,
            "xp":           problem.xp,
            "time_l":       problem.time_limit,
            "memory_l":     problem.memory_limit,
            "cate_name":    problem.category.name if problem.category else None,

            "tags":       [{"id": t.id, "name": t.name} for t in problem.tags.all()],
            "langs":      [{"id": l.id, "name": l.name, "version": l.version} for l in problem.language.all()],
            "hints":      [{"id": h.id, "text": h.text} for h in problem.hints.all()],
            "chall":      [{"id": c.id, "text": c.text} for c in problem.challenges.all()],
            "exam": [
                {
                    "id":          case.id,
                    "input":       case.input_txt,
                    "output":      case.output_txt,
                    "explanation": case.explanation
                }
                for case in problem.test_cases.all()
            ],
            "func": {
                fn.language_id: {"id": fn.id, "code": fn.function}
                for fn in problem.functions.all()
            },
        }
        # Uzoq muddatli keshga yozamiz
        cache.set(static_cache_key, base_data, timeout=600)

    # =================================================================
    # 2. DINAMIK KESH (METRICS DATA) - ATIGI 15 SEKUND (15s)
    # =================================================================
    dynamic_cache_key = f"problem_detail_dynamic_metrics_{base_data['id']}"
    acceptance_rate = cache.get(dynamic_cache_key)

    if acceptance_rate is None:
        # Jami va to'g'ri urinishlarni bazada hisoblaymiz
        metrics = await Problem.objects.filter(id=base_data["id"]).annotate(
            total_subs=Count("submissions"),
            correct_subs=Count("submissions", filter=Q(submissions__status=True))
        ).annotate(
            # 0 ga bo'linish xavfsizligi
            calculated_acceptance=Case(
                When(total_subs=0, then=Value(0.0)),
                default=ExpressionWrapper(
                    Cast("correct_subs", FloatField()) / Cast("total_subs", FloatField()) * 100,
                    output_field=FloatField()
                ),
                output_field=FloatField()
            )
        ).values("calculated_acceptance").afirst()

        acceptance_rate = round(metrics["calculated_acceptance"]) if metrics else 0
        
        # Qisqa muddatli keshga yozamiz
        cache.set(dynamic_cache_key, acceptance_rate, timeout=15)

    # =================================================================
    # 3. JORIY FOYDALANUVCHI STATUSI (KESHGA SOLINMAYDI ❌)
    # =================================================================
    is_solved = False

    if request_user:
        # Foydalanuvchi yechgan lahzada srazu ko'rinishi uchun DB-dan to'g'ridan-to'g'ri tekshiradi
        is_solved = await Submission.objects.filter(
            user_id=request_user.id,
            problem_id=base_data["id"],
            status=True
        ).aexists()

    # =================================================================
    # 4. YAKUNIY JAVOBNI BIRLASHTIRIB QAYTARAMIZ
    # =================================================================
    return {
        **base_data,
        "acceptance": acceptance_rate,
        "solved":     is_solved,
    }

    
# http://localhost:8000/api/v1/problems/{slug}/submission?limit=10&offset=0
@api.get("/{slug}/submission")
async def get_submission_list_for_user(
    request: Request, 
    slug: str,
    params: Annotated[PaginationParams, Query()], 
    request_user: BaseUser | None = Depends(get_current_user_option)
):
    # 1. Tizimga kirmagan bo'lsa, srazu bo'sh format (0 SQL Queries)
    if not request_user:
        return {"count": 0, "limit": params.limit, "offset": params.offset, "data": []}

    # 2. Masala ID sini aniqlash
    problem_id = await Problem.objects.filter(slug=slug, is_active=True).values_list('id', flat=True).afirst()
    if not problem_id:
        raise HTTPException(status_code=404, detail="Masala topilmadi!")

    # 3. N+1 MUAMMOSINI 100% YO'Q QILUVCHI QUERYSET
    queryset = Submission.objects.filter(
        user_id=request_user.id,
        problem_id=problem_id
    ).select_related(
        'language'
    ).only(
        'id', 'status', 'verdict', 'passed_test_count', 'total_test_count', 
        'execution_time', 'execution_memory', 'language__name', 'submitted_at'
    ).order_by('-submitted_at')[params.offset : params.offset + params.limit]

    # 4. Ma'lumotlarni asinxron tozalash
    submissions_list = []
    async for sub in queryset:
        """
        {
            "id": 139,
            "status": false,
            "verdict": "WA",
            "passed_count": 0,
            "total_count": 2,
            "time": 135,
            "memory": 19168000,
            "lang": "python",
            "created_at": "2026-07-24 12:49"
        }
        """
        submissions_list.append({
            "id": sub.id,
            "status": sub.status,
            "verdict": sub.verdict,
            "passed_count": sub.passed_test_count,
            "total_count": sub.total_test_count,
            "time": sub.execution_time if sub.execution_time else "-",
            "memory": sub.execution_memory if sub.execution_memory else "-",
            "lang": sub.language.name,
            "created_at": sub.submitted_at.strftime("%Y-%m-%d %H:%M") # Chiroyli vaqt formati
        })

    # Paginatsiya uchun umumiy sanoq
    total_count = await Submission.objects.filter(user_id=request_user.id, problem_id=problem_id).acount()

    return {
        "count": total_count,
        "limit": params.limit,
        "offset": params.offset,
        "data": submissions_list,
    }


# http://localhost:8000/api/v1/problems/stats/
# "Mening holatim" widjeti uchun — ro'yxat filter/pagination holatidan mustaqil
@api.get("/stats/")
async def problems_stats(request: Request, request_user: BaseUser | None = Depends(get_current_user_option)):
    # 1. Daraja bo'yicha JAMI son — kam o'zgaradi, keshlanadi
    cache_key = "problems_stats_totals_by_difficulty"
    totals_by_diff = cache.get(cache_key)
    if totals_by_diff is None:
        totals_by_diff = {"easy": 0, "medium": 0, "hard": 0}
        async for row in (
            Problem.objects
            .filter(is_active=True, lesson_id__isnull=True)
            .values("difficulty")
            .annotate(total=Count("id"))
        ):
            totals_by_diff[row["difficulty"]] = row["total"]
        cache.set(cache_key, totals_by_diff, timeout=300)

    total = sum(totals_by_diff.values())

    # 2. Foydalanuvchi necha ta NOYOB masala yechgani — daraja bo'yicha
    solved_by_diff = {"easy": 0, "medium": 0, "hard": 0}
    solved_total = 0

    if request_user:
        solved_problem_ids = [
            pid
            async for pid in (
                Submission.objects
                .filter(user_id=request_user.id, status=True)
                .values_list("problem_id", flat=True)
                .distinct()
            )
        ]
        if solved_problem_ids:
            async for row in (
                Problem.objects
                .filter(id__in=solved_problem_ids, is_active=True, lesson_id__isnull=True)
                .values("difficulty")
                .annotate(total=Count("id"))
            ):
                solved_by_diff[row["difficulty"]] = row["total"]
            solved_total = sum(solved_by_diff.values())

    return {
        "total": total,
        "solved": solved_total,
        "by_difficulty": {
            d: {"total": totals_by_diff.get(d, 0), "solved": solved_by_diff.get(d, 0)}
            for d in ("easy", "medium", "hard")
        },
    }


# http://localhost:8000/api/v1/problems/{slug}/likes/
@api.get("/{slug}/likes/")
async def get_like_count(
    request: Request,
    slug: str,
    request_user: BaseUser | None = Depends(get_current_user_option)
):
    try:
        # 1. Masalaning jami reaksiyalarini bitta SQL so'rovda hisoblaymiz (Annotate yordamida)
        problem = await (
            Problem.objects
            .filter(slug=slug, is_active=True)
            .annotate(
                likes_count=Count("problem_likes", filter=Q(problem_likes__like_or_dislike=True)),
                dislikes_count=Count("problem_likes", filter=Q(problem_likes__like_or_dislike=False))
            )
            .only("id")  # Faqat ID yetarli, ortiqcha ustunlarni yuklamaymiz (Tezkorlik uchun)
            .aget()
        )
    except Problem.DoesNotExist:
        raise HTTPException(status_code=404, detail="Masala topilmadi")

    # 2. Foydalanuvchi tizimga kirgan bo'lsa, uning joriy reaksiyasini tekshiramiz
    user_reaction = None
    if request_user:
        try:
            like_obj = await Like.objects.only("like_or_dislike").aget(
                problem_id=problem.id, 
                user_id=request_user.id
            )
            user_reaction = "like" if like_obj.like_or_dislike else "dislike"
        except Like.DoesNotExist:
            user_reaction = None

    # 3. Natijani qaytaramiz
    return {
        "likes": problem.likes_count,
        "dislikes": problem.dislikes_count,
        "user_reaction": user_reaction  # "like", "dislike" yoki null
    }




class LikeToggleIn(msgspec.Struct):
    # True = Like, False = Dislike
    like_or_dislike: bool = True


# http://localhost:8000/api/v1/problems/{slug}/likes/
@api.post("/{slug}/likes/")
async def toggle_problem_like(
    request: Request,
    slug: str,
    payload: LikeToggleIn,
    request_user: BaseUser | None = Depends(get_current_user_option)
):
    # 1. Foydalanuvchi tizimga kirganligini tekshirish (Anonim foydalanuvchilar reaksiya qoldirolmaydi)
    if not request_user:
        raise HTTPException(status_code=401, detail="Ushbu amalni bajarish uchun tizimga kiring")

    # 2. Masala mavjudligini tekshirish (Faqat id yuklanadi, tezkorlik uchun)
    try:
        problem = await Problem.objects.filter(slug=slug, is_active=True).only("id").aget()
    except Problem.DoesNotExist:
        raise HTTPException(status_code=404, detail="Masala topilmadi")

    # 3. 'unique_together' cheklovini hisobga olib, aget_or_create'dan foydalanamiz
    like_obj, created = await Like.objects.aget_or_create(
        problem_id=problem.id,
        user_id=request_user.id,
        defaults={"like_or_dislike": payload.like_or_dislike}
    )

    action_status = "created"
    
    if not created:
        # Agar foydalanuvchi avval bosgan reaksiyasini yana qayta bossa -> Reaksiyani o'chiramiz (Toggle)
        if like_obj.like_or_dislike == payload.like_or_dislike:
            await like_obj.adelete()
            action_status = "deleted"
        # Agar reaksiyani o'zgartirsa (masalan Like -> Dislike) -> Yangilaymiz
        else:
            like_obj.like_or_dislike = payload.like_or_dislike
            await like_obj.asave()
            action_status = "updated"

    # 4. Foydalanuvchiga real-vaqtdagi yangi jami hisob-kitobni bitta so'rovda qaytaramiz
    updated_stats = await (
        Problem.objects
        .filter(id=problem.id)
        .annotate(
            likes_count=Count("problem_likes", filter=Q(problem_likes__like_or_dislike=True)),
            dislikes_count=Count("problem_likes", filter=Q(problem_likes__like_or_dislike=False))
        )
        .only("id")
        .aget()
    )

    # Joriy foydalanuvchining yangi reaksiya holati
    current_reaction = None
    if action_status != "deleted":
        current_reaction = "like" if payload.like_or_dislike else "dislike"

    return {
        "status": action_status,
        "likes": updated_stats.likes_count,
        "dislikes": updated_stats.dislikes_count,
        "user_reaction": current_reaction
    }


@api.get("/submission/{id}")
async def get_submission_detail(
    request: Request,
    id: int,
    request_user: BaseUser | None = Depends(get_current_user_option)
):
    """
    Bitta taqdimotning batafsil ma'lumotlari.
    Faqat o'zining yoki admin foydalanuvchining submission'ini ko'rish mumkin.
    """
    try:
        submission = await (
            Submission.objects
            .select_related("user", "problem", "language")
            .aget(id=id)
        )
    except Submission.DoesNotExist:
        raise HTTPException(status_code=404, detail="Taqdimot topilmadi")

    # XAVFSIZLIK: Faqat o'zining submission'ini ko'rish (admin bo'lmasa)
    if request_user is None:
        raise HTTPException(status_code=401, detail="Tizimga kiring")
    
    if submission.user_id != request_user.id and not request_user.is_staff:
        raise HTTPException(status_code=403, detail="Bu ma'lumotni ko'rish huquqingiz yo'q")

    # NULL safety bilan ma'lumotlarni tayyorlash
    user_display = "Noma'lum"
    if submission.user:
        user_display = submission.user.username or str(submission.user.telegram_id or "Noma'lum")

    problem_data = {"id": None, "title": "Noma'lum"}
    if submission.problem:
        problem_data = {
            "id": submission.problem.id,
            "title": submission.problem.title,
        }

    language_data = {"id": None, "name": "Noma'lum"}
    if submission.language:
        language_data = {
            "id": submission.language.id,
            "name": submission.language.name,
        }

    return {
        "id": submission.id,
        "user": user_display,
        "xp": submission.problem.xp if submission.problem else 0,
        "problem": problem_data,
        "language": language_data,
        "status": submission.status,
        "verdict": submission.verdict or "WA",
        "passed": submission.passed_test_count,
        "total": submission.total_test_count,
        "time": submission.execution_time if submission.execution_time is not None else "-",
        "memory": submission.execution_memory if submission.execution_memory is not None else "-",
        "code": submission.code or "",
        "test_results": submission.test_results or [],
        "submitted_at": submission.submitted_at.strftime("%Y-%m-%d %H:%M") if submission.submitted_at else None,
    }


@api.get("/{slug}/hls/video/")
async def get_solution_video(
    request: Request,
    slug: str,
    request_user: BaseUser | None = Depends(get_current_user_option),
):
    if not request_user:
        raise HTTPException(
            status_code=401,
            detail="Tizimga kiring"
        )

    problem = await (
        Problem.objects
        .select_related("solution_video")
        .filter(
            slug=slug,
            is_active=True,
        )
        .only(
            "id",
            "solution_video_id",
            "solution_video__id",
            "solution_video__hls_url",
            "solution_video__thumbnail",
            "solution_video__duration",
        )
        .afirst()
    )

    if not problem:
        raise HTTPException(
            status_code=404,
            detail="Masala topilmadi"
        )

    solved = await Submission.objects.filter(
        user_id=request_user.id,
        problem_id=problem.id,
        status=True,
    ).aexists()

    if not solved:
        raise HTTPException(
            status_code=403,
            detail="Videoni ko'rish uchun avval masalani yeching"
        )

    if not problem.solution_video:
        raise HTTPException(
            status_code=404,
            detail="Ushbu masala uchun yechim videosi mavjud emas"
        )

    video = problem.solution_video

    return {
        "id": str(video.id),
        "hls_url": video.hls_url,
        "thumbnail": (
            video.thumbnail.url
            if video.thumbnail
            else None
        ),
        "duration": video.duration,
    }