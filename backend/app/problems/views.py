from ninja import Router, Schema
from django.db.models import (
    Count, Q, Exists, OuterRef,
    F, FloatField, Value, Case, When,
)
from django.db.models.functions import Coalesce, Round
from django.shortcuts import get_object_or_404
from typing import Optional, List
from django.core.cache import cache

from baseuser.authenticate import JWTAuth
from .models import Problem, Category, Tags, Like
from submissions.models import Submission
from video.models import Video


api = Router(tags=["Problems"])

# ─── 1. Trafikni Tejovchi Minimal Chiqish Sxemalari (Schemas) ───
class CompactProblemOut(Schema):
    id: int
    title: str
    slug: str
    diff: str  # easy, medium, hard
    rate: float  # acceptance_rate
    tags: List[str]  # Faqat string massivi: ["math", "dp"]
    status: int  # 1: yechilgan (✓), 0: xato (✗), -1: urinilmagan (—)

class ProblemStats(Schema):
    easy: int
    medium: int
    hard: int

class CompactProblemResponse(Schema):
    total: int
    stats: Optional[ProblemStats] = None  # Faqat offset=0 bo'lganda trafikni tejash uchun uzatiladi
    items: List[CompactProblemOut]
# ─── 1. Yangi Kam Trafikli Chiqish Sxemalari (Schemas) ───

class ChoiceOut(Schema):
    id: int
    text: str

class ProblemQuestionItemOut(Schema):
    id: int
    text: str
    difficulty: str
    xp: int
    image_url: Optional[str] = None
    choices: List[ChoiceOut]  # Javob variantlari (To'g'rimi yoki yo'qligi trafik uchun yashiriladi)

class ProblemQuestionResponse(Schema):
    id: int
    title: str
    slug: str
    description: str
    constraints: str
    questions: List[ProblemQuestionItemOut]  # Masalaga tegishli test savollari

class ProblemVideoOut(Schema):
    id: int
    title: str
    slug: str
    duration: Optional[str] = None
    description: str
    poster_url: Optional[str] = None
    video_url: Optional[str] = None

"""
{
  "total": 512,
  "stats": {
    "easy": 180,
    "medium": 230,
    "hard": 102
  },
  "items": [
    {
      "id": 1001,
      "title": "Two Sum",
      "slug": "two-sum",
      "diff": "easy",
      "rate": 72.0,
      "tags": ["math", "dp"],
      "status": 1
    },
    {
      "id": 1002,
      "title": "Valid Parentheses",
      "slug": "valid-parentheses",
      "diff": "easy",
      "rate": 65.0,
      "tags": ["string"],
      "status": 0
    },
    {
      "id": 1003,
      "title": "Longest Substring",
      "slug": "longest-substring",
      "diff": "medium",
      "rate": 55.0,
      "tags": ["string", "greedy"],
      "status": -1
    }
  ]
}
"""
# ─── 2. Masalalar Ro'yxati Endpointi ───
@api.get("/problems", response=CompactProblemResponse, auth=JWTAuth())
def list_problems(
    request,
    difficulty: Optional[str] = None,
    category_id: Optional[int] = None,
    tag_id: Optional[int] = None,
    search: Optional[str] = None,
    solved: Optional[int] = None,  # 1, 0 yoki -1
    limit: int = 20,
    offset: int = 0
):
    telegram_id = request.auth.telegram_id
    
    # 1. Kesh kalitini yaratamiz
    cache_key = f"probs:{telegram_id}:{difficulty}:{category_id}:{tag_id}:{search}:{solved}:{limit}:{offset}"
    cached_data = cache.get(cache_key)
    
    # 🔥 DIAGNOSTIKA VA XATOLIKNING ASOSIY YECHIMI:
    # Keshdan lug'at (dict) qaytsa, Django Ninja uni tanimaydi. 
    # Shuning uchun uni qaytadan Pydantic modeliga (CompactProblemResponse) o'tkazib return qilamiz.
    if cached_data:
        try:
            return CompactProblemResponse(**cached_data)
        except Exception:
            # Agar keshdagi ma'lumot mos kelmasa, keshni tozalab bazadan o'qiymiz
            cache.delete(cache_key)

    # Baza so'rovini boshlash
    qs = Problem.objects.filter(is_active=True, problem_type="problem").prefetch_related("tags")

    # ── Frontend Filtrlari ──
    if difficulty:
        qs = qs.filter(difficulty=difficulty)
    if category_id:
        qs = qs.filter(category_id=category_id)
    if tag_id:
        qs = qs.filter(tags__id=tag_id).distinct()
    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))

    # ── Annotatsiya va Submissions (Statistika hisoblash) ──
    accepted_sub = Submission.objects.filter(problem=OuterRef("pk"), status=True).values("problem").annotate(c=Count("id")).values("c")[:1]
    total_sub = Submission.objects.filter(problem=OuterRef("pk")).values("problem").annotate(c=Count("id")).values("c")[:1]
    
    solved_sub = Submission.objects.filter(user__telegram_id=telegram_id, problem=OuterRef("pk"), status=True)
    failed_sub = Submission.objects.filter(user__telegram_id=telegram_id, problem=OuterRef("pk"), status=False)

    qs = qs.annotate(
        accepted_count=Coalesce(accepted_sub, Value(0)),
        total_subs=Coalesce(total_sub, Value(0)),
        is_solved=Exists(solved_sub),
        is_failed=Exists(failed_sub),
    ).annotate(
        acceptance_rate=Case(
            When(total_subs=0, then=Value(0.0)),
            default=Round(F("accepted_count") * 100.0 / F("total_subs"), 1),
            output_field=FloatField(),
        )
    )

    # ── Mening Holatim (Solved) Filtri ──
    if solved is not None:
        if solved == 1:
            qs = qs.filter(is_solved=True)
        elif solved == 0:
            qs = qs.filter(is_solved=False, is_failed=True)
        elif solved == -1:
            qs = qs.filter(is_solved=False, is_failed=False)

    # Tartiblash
    qs = qs.order_by("is_solved", "-created_at")

    # Jami mos keluvchi masalalar soni
    total_count = qs.count()

    # Statistika faqat offset=0 bo'lganda yuklanadi
    stats_data = None
    if offset == 0:
        counts = qs.values("difficulty").annotate(total=Count("id"))
        stats_dict = {"easy": 0, "medium": 0, "hard": 0}
        for item in counts:
            diff = item["difficulty"]
            if diff in stats_dict:
                stats_dict[diff] = item["total"]
        stats_data = ProblemStats(**stats_dict)

    # Pagination qismi
    paginated_qs = qs[offset : offset + limit]

    # JSON ga ixcham formatda o'tkazish
    items_list = []
    for p in paginated_qs:
        status_code = -1
        if p.is_solved:
            status_code = 1
        elif p.is_failed:
            status_code = 0

        items_list.append(
            CompactProblemOut(
                id=p.id,
                title=p.title,
                slug=p.slug,
                diff=p.difficulty,
                rate=float(p.acceptance_rate or 0),
                tags=[t.name for t in p.tags.all()],
                status=status_code
            )
        )

    response_payload = CompactProblemResponse(
        total=total_count,
        stats=stats_data,
        items=items_list
    )

    # 🔥 DIQQAT: Pydantic v2 da .dict() eskirgan, .model_dump() ishlatiladi.
    # Keshga yozishdan oldin ma'lumotni toza json-serializable (lug'at) formatga o'tkazamiz
    try:
        if hasattr(response_payload, "model_dump"):
            cache_data_to_save = response_payload.model_dump()
        else:
            cache_data_to_save = response_payload.dict()
            
        cache.set(cache_key, cache_data_to_save, timeout=300)
    except Exception as e:
        print(f"Keshga yozishda xatolik: {e}")

    return response_payload

# ─── 1. Trafik uchun minimal chiqish sxemasi ───
class CompactCategoryOut(Schema):
    id: int
    name: str
    slug: str

# ─── 2. Kategoriyalar Endpointi ───
"""
[
  {
    "id": 1,
    "name": "Matematika",
    "slug": "matematika"
  },
  {
    "id": 2,
    "name": "Algoritmlar",
    "slug": "algoritmlar"
  },
  {
    "id": 3,
    "name": "Ma'lumotlar tuzilmasi",
    "slug": "malumotlar-tuzilmasi"
  }
]
"""
@api.get("/categories", response=List[CompactCategoryOut], auth=JWTAuth())
def list_categories(request):
    """
    Barcha aktiv kategoriyalar ro'yxatini minimal trafik bilan qaytaradi.
    """
    # values() yoki only() orqali faqat kerakli maydonlarni bazadan tezkor tortamiz
    qs = Category.objects.all().only("id", "name", "slug").order_by("name")
    
    return [
        CompactCategoryOut(
            id=c.id,
            name=c.name,
            slug=c.slug
        )
        for c in qs
    ]


# ─── Tags ──────────────────────────────────────────────────────────────────────

class CompactTagOut(Schema):
    id: int
    name: str

# ─── 2. Teglar (Mavzular) Endpointi ───

@api.get("/tags", response=List[CompactTagOut], auth=JWTAuth())
def list_tags(request):
    """
    Kamida bitta faol 'problem' turidagi masalaga ega bo'lgan 
    barcha teglarni (mavzularni) eng tezkor uslubda qaytaradi.
    """
    # SQL JOIN (Count) yuklamasini chetlab o'tish uchun faqat bog'langan m2m mantiqidan foydalanamiz
    qs = (
        Tags.objects
        .filter(
            problems__is_active=True, 
            problems__problem_type="problem"
        )
        .only("id", "name")  # SQL dan faqat kerakli ustunlarni o'qiymiz
        .distinct()          # Takrorlanishlarni (dublikatlarni) o'chiramiz
        .order_by("name")    # Alifbo tartibida sarflaymiz
    )
    
    return [
        CompactTagOut(
            id=t.id,
            name=t.name
        )
        for t in qs
    ]

"""
{
  "id": 1001,
  "title": "Two Sum",
  "slug": "two-sum",
  "diff": "easy",
  "xp": 100,
  "rate": 72.0,
  "is_solved": false,
  "time_limit": 2000,
  "memory_limit": 256,
  "description": "Berilgan butun sonlar massivi `nums` va bitta butun son `target` berilgan. Yig'indisi `target` ga teng bo'lgan ikkita sonning indekslarini qaytaring.",
  "constraints": "2 <= nums.length <= 10^4\n-10^9 <= nums[i] <= 10^9\n-10^9 <= target <= 10^9",
  "tags": ["math", "dp"],
  "examples": [
    {
      "input": "nums = [2,7,11,15], target = 9",
      "output": "[0,1]",
      "explanation": "Chunki nums[0] + nums[1] == 9, shuning uchun [0, 1] qaytaramiz."
    }
  ],
  "allowed_languages": [
    {
      "id": 1,
      "name": "Python",
      "slug": "python",
      "template": "def twoSum(nums: list[int], target: int) -> list[int]:\n    # Kodni shu yerga yozing\n    pass"
    },
    {
      "id": 2,
      "name": "JavaScript",
      "slug": "javascript",
      "template": "var twoSum = function(nums, target) {\n    \n};"
    }
  ]
}
"""
class CompactExampleOut(Schema):
    input: str
    output: str
    explanation: str

class AllowedLanguageOut(Schema):
    id: int
    name: str
    slug: str
    template: str

class CompactProblemDetailOut(Schema):
    id: int
    title: str
    slug: str
    diff: str
    xp: int
    rate: float
    is_solved: bool
    time_limit: int
    memory_limit: int
    description: str
    constraints: str
    tags: List[str]
    examples: List[CompactExampleOut]
    allowed_languages: List[AllowedLanguageOut]


# ─── 2. Problem Detail Endpointi ──────────────────────────────────────────────

@api.get("/problem/{slug}", response=CompactProblemDetailOut, auth=JWTAuth())
def get_problems_by_slug(request, slug: str):
    """
    Bitta masala haqida to'liq ma'lumotlarni minimal trafik formatida qaytaradi.
    Kod muharriri uchun dasturlash tillari andozalari (templates) ham birga keladi.
    """
    telegram_id = request.auth.telegram_id

    # 1. Masala foydalanuvchi tomonidan yechilganmi yoki yo'qmi (Subquery)
    solved_sub = Submission.objects.filter(
        user__telegram_id=telegram_id,
        problem=OuterRef("pk"),
        status=True,
    )

    # 2. Masalaning umumiy qabul foizini hisoblash (Subqueries)
    accepted_sub = Submission.objects.filter(problem=OuterRef("pk"), status=True).values("problem").annotate(c=Count("id")).values("c")[:1]
    total_sub = Submission.objects.filter(problem=OuterRef("pk")).values("problem").annotate(c=Count("id")).values("c")[:1]

    # 3. Asosiy so'rov (Prefetch orqali m2m jadvallar yuklanishini tezlashtiramiz)
    qs = Problem.objects.filter(is_active=True, slug=slug).prefetch_related("tags", "language", "examples", "functions__language")
    
    # Annotatsiya qo'shish
    qs = qs.annotate(
        is_solved=Exists(solved_sub),
        accepted_count=Coalesce(accepted_sub, Value(0)),
        total_subs=Coalesce(total_sub, Value(0)),
    ).annotate(
        acceptance_rate=Case(
            When(total_subs=0, then=Value(0.0)),
            default=Round(F("accepted_count") * 100.0 / F("total_subs"), 1),
            output_field=FloatField(),
        )
    )

    # Masalani bazadan qidirish, topilmasa 404 qaytarish
    p = get_object_or_404(qs)

    # 4. Misollarni ixcham formatga o'tkazish
    examples_list = [
        CompactExampleOut(
            input=ex.input_txt,
            output=ex.output_txt,
            explanation=ex.explanation
        )
        for ex in p.examples.all()
    ]

    # 5. Ruxsat berilgan dasturlash tillari va ularning andozalarini (templates) yig'ish
    # Funksiyalar shablonini oson topish uchun lug'at (dict) yaratib olamiz
    function_templates = {
        f.language_id: f.function for f in p.functions.all()
    }
    
    allowed_languages_list = []
    for lang in p.language.all():
        # Agar masalaga mos til shabloni (Function) yozilmagan bo'lsa, bo'sh joy qaytaradi
        template_code = function_templates.get(lang.id, "")
        
        allowed_languages_list.append(
            AllowedLanguageOut(
                id=lang.id,
                name=lang.name,
                slug=lang.slug or "",
                template=template_code
            )
        )

    # 6. JSON strukturaga moslab natijani qaytarish
    return CompactProblemDetailOut(
        id=p.id,
        title=p.title,
        slug=p.slug,
        diff=p.difficulty,
        xp=p.xp,
        rate=float(p.acceptance_rate or 0),
        is_solved=bool(p.is_solved),
        time_limit=p.time_limit or 2000,
        memory_limit=p.memory_limit or 256,
        description=p.description,
        constraints=getattr(p, 'constraints', '') or "", # Agar modelda constraints maydoni bo'lsa o'qiydi
        tags=[t.name for t in p.tags.all()],
        examples=examples_list,
        allowed_languages=allowed_languages_list
    )

# ─── 1. Yangi Ixcham Chiqish Sxemalari (Schemas) ───

class ChoiceOut(Schema):
    id: int
    text: str

class ProblemQuestionItemOut(Schema):
    id: int
    text: str
    difficulty: str
    xp: int
    image_url: Optional[str] = None
    choices: List[ChoiceOut]


# ─── 2. Faqat Savollar Ro'yxati Endpointi agar bulsa ─────────────────────────────────────

@api.get("/problem/{slug}/question", response=List[ProblemQuestionItemOut], auth=JWTAuth())
def get_problem_question(request, slug: str):
    """
    Masalaga tegishli faqat universal test savollarini va variantlarini
    ortiqcha tavsiflarsiz, to'liq rasm URL manzillari bilan qaytaradi.
    """
    # prefetch_related orqali faqat bog'langan savol va variantlarni RAMga yuklaymiz
    p = get_object_or_404(
        Problem.objects.filter(is_active=True).prefetch_related("questions__choices"), 
        slug=slug
    )

    questions_list = []
    for q in p.questions.all():
        # Savol variantlari shakllantiriladi
        choices_list = [
            ChoiceOut(id=c.id, text=c.text)
            for c in q.choices.all()
        ]
        
        # Rasm URL manzilini mutloq formatga keltirish (http://localhost:9000/...)
        image_full_url = None
        if q.image:
            image_full_url = request.build_absolute_uri(q.image.url)

        questions_list.append(
            ProblemQuestionItemOut(
                id=q.id,
                text=q.text,
                difficulty=q.difficulty,
                xp=q.xp,
                image_url=image_full_url,
                choices=choices_list
            )
        )

    return questions_list




# ─── 3. Masalaga Tegishli Videolar Ro'yxati Endpointi. agar bulsa  ──────────────────────────

@api.get("/problem/{slug}/videos", response=List[ProblemVideoOut], auth=JWTAuth())
def get_problem_videos(request, slug: str):
    """
    Ushbu masalaga biriktirilgan barcha video darslar ro'yxatini qaytaradi.
    Trafikni tejash uchun HLS oqimi yoki MP4 yuklab olish manzillari optimallashgan.
    """
    # related_name="problem_videos" orqali videolarni bitta SQL queryda yuklaymiz (N+1 oldi olinadi)
    p = get_object_or_404(
        Problem.objects.filter(is_active=True).prefetch_related("problem_videos"), 
        slug=slug
    )

    videos_list = []
    for v in p.problem_videos.all():
        # Poster uchun birinchi navbatda tashqi link (thumbnail), bo'lmasa o'zimizning fayl yuklamasi olinadi
        poster = v.thumbnail if v.thumbnail else (v.image.url if v.image else None)
        
        # Pleyer uchun HLS (oqim) yoki MP4 to'g'ridan-to'g'ri manzili tanlanadi
        video_link = v.hls_url if v.hls_url else (v.mp4_url if v.mp4_url else (v.video.url if v.video else None))

        videos_list.append(
            ProblemVideoOut(
                id=v.id,
                title=v.title,
                slug=v.slug,
                duration=v.duration or "--:--",
                description=v.description,
                poster_url=poster,
                video_url=video_link
            )
        )

    return videos_list



class LikeIn(Schema):
    is_like: bool  # True: Like tugmasi bosildi, False: Dislike bosildi

class LikeOut(Schema):
    lk: int
    dl: int
    st: int



@api.post("/problem/{slug}/like", response=LikeOut, auth=JWTAuth())
def toggle_problem_like(request, slug: str, payload: LikeIn):
    """
    Masalaga Like yoki Dislike bosish, o'chirish va o'zgartirish (Toggle) API-si.
    Maksimal darajada siqilgan va eng qisqa trafik formatida javob qaytaradi.
    """
    user = request.auth
    problem = get_object_or_404(Problem, slug=slug, is_active=True)
    
    # 1. Foydalanuvchining eski reaksiyasini qidiramiz
    existing = Like.objects.filter(problem=problem, user=user).first()
    
    if existing and existing.like_or_dislike == payload.is_like:
        # Foydalanuvchi o'zi bosgan tugmani qayta bossa - reaksiyani butunlay o'chiramiz
        existing.delete()
        status_code = 0
    else:
        # Yangi reaksiya qo'shish yoki eskisini o'zgartirish (update_or_create)
        Like.objects.update_or_create(
            problem=problem, 
            user=user, 
            defaults={"like_or_dislike": payload.is_like}
        )
        status_code = 1 if payload.is_like else -1

    # 2. OPTIMAL HISOB-KITOB: Bitta SQL queryda jami likelar va dislikelarni sanaymiz
    stats = Like.objects.filter(problem=problem).aggregate(
        likes=Count("id", filter=Q(like_or_dislike=True)),
        dislikes=Count("id", filter=Q(like_or_dislike=False))
    )

    return LikeOut(
        lk=stats["likes"] or 0,
        dl=stats["dislikes"] or 0,
        st=status_code
    )


# ─── 2. Alohida Masala Reaksiyalari Endpointi (GET) ───────────────────────────

@api.get("/problem/{slug}/likes", response=LikeOut, auth=JWTAuth())
def get_problem_detail_likes(request, slug: str):
    """
    Problem Detail sahifasini tezlashtirish uchun:
    Bitta masalaga tegishli jami likelar, dislikelar va foydalanuvchining 
    shaxsiy reaksiyasini mutloq alohida va yengil formatda qaytaradi.
    """
    user = request.auth
    problem = get_object_or_404(Problem, slug=slug, is_active=True)

    # 1. Bitta tezkor SQL so'rovda jami statistikani sanaymiz
    stats = Like.objects.filter(problem=problem).aggregate(
        likes=Count("id", filter=Q(like_or_dislike=True)),
        dislikes=Count("id", filter=Q(like_or_dislike=False))
    )

    # 2. Foydalanuvchining shaxsiy reaksiyasini aniqlaymiz
    user_reaction = Like.objects.filter(problem=problem, user=user).first()
    
    status_code = 0
    if user_reaction:
        status_code = 1 if user_reaction.like_or_dislike else -1

    return LikeOut(
        lk=stats["likes"] or 0,
        dl=stats["dislikes"] or 0,
        st=status_code
    )

# user submissionlarini olish
from ninja import Schema
from django.shortcuts import get_object_or_404
from django.utils import timezone
from typing import List, Optional
from baseuser.authenticate import JWTAuth
from .models import Problem
from submissions.models import Submission

# Router yuqorida e'lon qilingan deb hisoblaymiz: api = Router(...)

# ─── 1. Judge0 tizimiga moslashtirilgan professional schema ───
class CompactSubmissionHistoryOut(Schema):
    id: int
    st: str          # ac, wa, tle, ce
    lng: str         # Dasturlash tili nomi
    tm: str          # Vaqt ko'rsatkichi (e.g. "124ms" yoki "—")
    mm: str          # Xotira ko'rsatkichi (e.g. "9.2MB" yoki "—")
    ag: str          # Inson tilida qachon yuborilgani (e.g. "2 min oldin")
    dt: Optional[str] = None  # Xatolik tafsiloti (e.g. "Test 3 da xato")


# ─── Yordamchi vaqt funksiyasi (Trafikni tejash uchun matnni serverda yig'amiz) ───
def _get_time_ago(submitted_at):
    diff = timezone.now() - submitted_at
    seconds = diff.total_seconds()
    if seconds < 60:
        return "Hozirgincha"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes} min oldin"
    hours = int(minutes // 60)
    if hours < 24:
        return f"{hours} soat oldin"
    days = int(hours // 24)
    return f"{days} kun oldin"


# ─── 2. Urinishlar Tarixi Endpointi ───────────────────────────────────────────

@api.get("/problem/{slug}/submissions", response=List[CompactSubmissionHistoryOut], auth=JWTAuth())
def get_user_submissions(request, slug: str):
    """
    Foydalanuvchining Judge0 kabi batafsil ko'rsatkichli barcha urinishlar
    tarixini eng siqilgan va minimal trafik formatida qaytaradi.
    """
    user = request.auth
    problem = get_object_or_404(Problem, slug=slug, is_active=True)

    # N+1 muammosidan qutulish uchun select_related("language")
    submissions_qs = (
        Submission.objects
        .filter(problem=problem, user=user)
        .select_related("language")
        .only("id", "language__name", "status", "test_results", "submitted_at")
        .order_by("-submitted_at")
    )

    response_data = []
    for sub in submissions_qs:
        # Standart holatlar (Agar hammasi o'tgan bo'lsa default 'ac')
        final_status = "ac" if sub.status else "wa"
        time_str = "—"
        mem_str = "—"
        detail_str = None

        # RAMda test caselarni tahlil qilish (Judge0 mantiqi)
        if isinstance(sub.test_results, list) and len(sub.test_results) > 0:
            # 1. Agarda xatolik bo'lsa, qaysi testda birinchi bo'lib yuz berganini aniqlaymiz
            failed_case = next((res for res in sub.test_results if res.get("status") != "passed"), None)
            
            if failed_case:
                final_status = failed_case.get("status", "wa") # wa, tle, ce
                
                if final_status == "tle":
                    detail_str = "Vaqt limiti oshdi"
                    time_str = f">{problem.time_limit or 2000}ms"
                elif final_status == "ce":
                    detail_str = "Kompilyatsiya xatoligi"
                else:
                    detail_str = f"Test {failed_case.get('test_case', 1)} da xato"
            else:
                # Agar barcha testlardan o'tgan bo'lsa (Accepted) - vaqt va xotira yig'indisini hisoblaymiz
                # Bizning RAM/WebSocketda yozilgan test_results ko'rsatkichlaridan maksimal yoki yig'indini olamiz
                max_time = max(int(res.get("time", 0)) for res in sub.test_results)
                max_mem = max(float(res.get("memory", 0.0)) for res in sub.test_results)
                
                time_str = f"{max_time}ms"
                mem_str = f"{max_mem:.1f}MB" if max_mem > 0 else "4.2MB"

        response_data.append(
            CompactSubmissionHistoryOut(
                id=sub.id,
                st=final_status,
                lng=sub.language.name if sub.language else "C++ 17",
                tm=time_str,
                mm=mem_str,
                ag=_get_time_ago(sub.submitted_at),
                dt=detail_str
            )
        )

    return response_data



class FailedCaseDetailOut(Schema):
    num: int          # Xato qilgan test raqami
    input: str        # Test kirish matni
    expected: str     # Kutilgan to'g'ri javob (Output)
    output: str       # Talaba kodi qaytargan xato javob

class CompactCaseStatsOut(Schema):
    num: int          # Test case tartib raqami
    st: str           # ac, wa, tle, ce
    tm: int           # ms
    mm: float         # MB

class SubmissionDetailResponse(Schema):
    id: int
    status: str
    lang: str
    code: str
    time: str
    memory: str
    date: str
    error_case: Optional[FailedCaseDetailOut] = None
    cases: List[CompactCaseStatsOut]


# ─── 2. Urinish Tafsiloti API Endpointi ───────────────────────────────────────

@api.get("/submission/{submission_id}/detail", response=SubmissionDetailResponse, auth=JWTAuth())
def get_submission_detail(request, submission_id: int):
    """
    Urinish identifikatori (ID) bo'yicha yuborilgan kod, barcha test caselar
    va yuz bergan xatolik tafsilotlarini alohida siqilgan formatda qaytaradi.
    """
    user = request.auth
    
    # Faqat so'rov yuborgan foydalanuvchining o'ziga tegishli urinishni qidiramiz (Xavfsizlik)
    sub = get_object_or_404(Submission.objects.select_related("language", "problem"), id=submission_id, user=user)

    cases_list = []
    final_status = "ac" if sub.status else "wa"
    failed_case_obj = None
    max_time = 0
    max_mem = 0.0

    if isinstance(sub.test_results, list) and len(sub.test_results) > 0:
        # 1. Umumiy vaqt va xotira ko'rsatkichlarini hisoblash
        max_time = max(int(res.get("time", 0)) for res in sub.test_results)
        max_mem = max(float(res.get("memory", 0.0)) for res in sub.test_results)
        
        # 2. Test caselarni massiv ko'rinishida yig'ish
        for res in sub.test_results:
            c_status = res.get("status", "wa")
            c_num = res.get("test_case", 1)
            
            if c_status != "passed" and final_status == "ac":
                final_status = c_status # Birinchi xato holatini saqlaymiz (wa, tle, ce)

            cases_list.append(
                CompactCaseStatsOut(
                    num=c_num,
                    st="ac" if c_status == "passed" else c_status,
                    tm=int(res.get("time", 0)),
                    mm=float(res.get("memory", 0.0))
                )
            )

        # 3. Agar kod xato bo'lsa, o'sha test casening bazadagi kirish/chiqish matnlarini olamiz
        if not sub.status:
            first_failed = next((res for res in sub.test_results if res.get("status") != "passed"), None)
            if first_failed:
                f_num = first_failed.get("test_case", 1)
                
                # Bazadagi TestCase modelidan tartib raqami bo'yicha qidiramiz
                # [f_num - 1] mantiqi tartib bo'yicha indeksni aniqlaydi
                db_cases = list(TestCase.objects.filter(problem=sub.problem).order_by("id"))
                if len(db_cases) >= f_num:
                    target_test = db_cases[f_num - 1]
                    failed_case_obj = FailedCaseDetailOut(
                        num=f_num,
                        input=target_test.input_txt,
                        expected=target_test.output_txt,
                        output=first_failed.get("user_output", "—") # Talabaning xato javobi
                    )

    return SubmissionDetailResponse(
        id=sub.id,
        status=final_status,
        lang=sub.language.name if sub.language else "C++ 17",
        code=sub.code,
        time=f"{max_time}ms" if max_time > 0 else "—",
        memory=f"{max_mem:.1f}MB" if max_mem > 0 else "—",
        date=sub.submitted_at.strftime("%Y-%m-%d %H:%M"),
        error_case=failed_case_obj,
        cases=cases_list
    )
