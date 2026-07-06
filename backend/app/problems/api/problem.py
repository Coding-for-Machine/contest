import msgspec
from typing import Annotated
from django_bolt import Router, Request, Depends,  LimitOffsetPagination, paginate
from django_bolt.params import Query
from django_bolt.exceptions import HTTPException
from django.core.cache import cache

from django.db.models import Prefetch, Count, Q, ExpressionWrapper, FloatField, Case, When, Value
from django.db.models.functions import Cast


from problems.models import Problem, Category, Tags, Hint, Challenge, Function, Language, TestCase
from submissions.models import Submission
from baseuser.authenticate import get_current_user_option
from baseuser.models import BaseUser

api = Router(tags=["admin problem api"])


# http://localhost:8000/api/v1/problems/categories/
@api.get("/categories/")
async def list_categories(request: Request, request_user: BaseUser | None = Depends(get_current_user_option)):
    return [
        {"id": c.id, "name": c.name, "slug": c.slug}
        async for c in Category.objects.only('id', 'name', 'slug').order_by('name')
    ]

# http://localhost:8000/api/v1/problems/tags/
@api.get("/tags/")
async def list_tags(request: Request, request_user: BaseUser | None = Depends(get_current_user_option)):
    return [
        {"id": t.id, "name": t.name}
        async for t in Tags.objects.only('id', 'name').order_by('name')
    ]

class FilterParams(msgspec.Struct):
    limit: int = 10
    offset: int = 0
    search: str | None = None
    category_id: int | None = None  # Kategoriya bo'yicha filter
    tag_id: int | None = None       # Tag bo'yicha filter


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
                "bookmarked": False 
            } for p in problems_list
        ]
    else:
        results = [
            {
                **p, 
                "solved": False,
                "bookmarked": False
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


class PaginationParams(msgspec.Struct):
    limit: int = 10
    offset: int = 0
    
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