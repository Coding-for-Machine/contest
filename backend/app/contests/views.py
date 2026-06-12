from ninja import Router, Schema
from ninja.pagination import paginate, PageNumberPagination
from typing import Optional, List
from django.db.models import Q, Count, Exists, OuterRef
from django.utils import timezone
from datetime import datetime
from contests.models import Contest, ContestRegistration
from baseuser.authenticate import JWTAuth


# ==================== SCHEMAS (Models ga mos) ====================

class ContestOut(Schema):
    """Tanlov chiqish formati"""
    # Asosiy maydonlar
    id: int
    title: str
    description: str
    type: str  # open, private
    status: str  # upcoming, ongoing, ended
    
    # Vaqt maydonlari
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration: str
    
    # Ishtirokchilar
    participants: int  # participants_count
    max_participants: int
    registered: bool = False  # user ro'yxatdan o'tganmi?
    
    # Qiyinlik va mukofotlar
    difficulty: str  # easy, medium, hard
    prizes: List[str] = []
    
    # Yopiq tanlov uchun
    requires_access_key: bool = False  # access_key bormi?
    
    # Statistika
    featured: bool = False
    category: Optional[str] = None
    
    # Qo'shimcha ma'lumotlar
    user_is_registered: bool = False
    reg_count: int = 0  # Jami ro'yxatdan o'tganlar
    time_remaining: Optional[str] = None  # Qolgan vaqt
    progress_percentage: Optional[int] = None  # Davom etayotgan bo'lsa, foiz

class ContestListOut(Schema):
    """Tanlovlar ro'yxati uchun qisqartirilgan format"""
    id: int
    title: str
    type: str
    status: str
    start_time: Optional[str] = None
    duration: str
    difficulty: str
    participants: int
    max_participants: int
    featured: bool
    registered: bool = False
    time_remaining: Optional[str] = None

class ContestDetailOut(Schema):
    """Bitta tanlov to'liq ma'lumot"""
    id: int
    title: str
    description: str
    type: str
    status: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration: str
    difficulty: str
    max_participants: int
    prizes: List[str] = []
    category: Optional[str] = None
    featured: bool
    registered: bool = False
    is_registration_open: bool = False  # property
    can_join: bool = False  # property
    participants_count: int = 0
    registrations_count: int = 0
    time_remaining: Optional[str] = None
    progress_percentage: Optional[int] = None
    
    # Foydalanuvchi statistikasi (agar registered bo'lsa)
    user_rank: Optional[int] = None
    user_score: Optional[int] = None
    registered_at: Optional[str] = None

class RegisterIn(Schema):
    """Ro'yxatdan o'tish uchun schema"""
    access_key: Optional[str] = None

class RegisterOut(Schema):
    """Ro'yxatdan o'tish javobi"""
    success: bool
    message: str
    contest_id: Optional[int] = None
    contest_title: Optional[str] = None

class MyContestOut(Schema):
    """Mening tanlovlarim uchun"""
    id: int
    title: str
    status: str
    registered_at: str
    total_score: int = 0
    rank: Optional[int] = None
    start_time: str
    end_time: str
    time_remaining: Optional[str] = None

# ==================== YORDAMCHI FUNKSIYALAR ====================

def get_time_remaining(target_time: datetime) -> Optional[str]:
    """Qolgan vaqtni formatlash"""
    now = timezone.now()
    diff = target_time - now
    
    if diff.total_seconds() <= 0:
        return None
    
    days = diff.days
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60
    
    if days > 0:
        return f"{days} kun {hours} soat"
    elif hours > 0:
        return f"{hours} soat {minutes} daqiqa"
    else:
        return f"{minutes} daqiqa"

def get_progress_percentage(start_time: datetime, end_time: datetime) -> Optional[int]:
    """Davom etayotgan tanlov foizini hisoblash"""
    now = timezone.now()
    
    if now < start_time:
        return 0
    if now > end_time:
        return 100
    
    total = (end_time - start_time).total_seconds()
    elapsed = (now - start_time).total_seconds()
    
    return int((elapsed / total) * 100)

# ==================== ROUTER ====================

router = Router(tags=["contests"])

class ContestPagination(PageNumberPagination):
    """Sahifalash"""
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50

# ==================== PUBLIC ENDPOINTS (Token kerak emas) ====================

@router.get("/contests", response=List[ContestListOut], auth=None)
@paginate(ContestPagination)
async def list_contests(
    request,
    status: Optional[str] = None,
    difficulty: Optional[str] = None,
    search: Optional[str] = None,
    featured: bool = False,
    contest_type: Optional[str] = None,  # open, private
):
    """
    Tanlovlar ro'yxati - PUBLIC
    
    Filtrlar:
    - status: upcoming, ongoing, ended
    - difficulty: easy, medium, hard
    - search: nom yoki tavsif bo'yicha qidirish
    - featured: true/false
    - contest_type: open, private
    """
    now = timezone.now()
    
    # 1. Base queryset
    queryset = Contest.objects.all()
    
    # 2. Annotate registrations count
    queryset = queryset.annotate(
        registrations_count=Count('registrations', filter=Q(registrations__is_active=True), distinct=True)
    )
    
    # 3. User registration status (agar user bo'lsa)
    user = request.auth if hasattr(request, 'auth') else None
    if user:
        reg_exists = ContestRegistration.objects.filter(
            user=user,
            contest=OuterRef('pk'),
            is_active=True
        )
        queryset = queryset.annotate(
            user_is_registered=Exists(reg_exists)
        )
    
    # 4. Filters
    filters = Q()
    
    if status:
        if status == "upcoming":
            filters &= Q(start_time__gt=now)
        elif status == "ongoing":
            filters &= Q(start_time__lte=now, end_time__gte=now)
        elif status == "ended":
            filters &= Q(end_time__lt=now)
    
    if difficulty:
        filters &= Q(difficulty=difficulty)
    
    if featured:
        filters &= Q(is_featured=True)
    
    if contest_type:
        filters &= Q(type=contest_type)
    
    if search:
        filters &= (Q(title__icontains=search) | Q(description__icontains=search))
    
    queryset = queryset.filter(filters).order_by("-start_time")
    
    # 5. Response
    result = []
    async for contest in queryset:
        # Statusni aniqlash
        if contest.start_time > now:
            contest_status = "upcoming"
            time_remaining = get_time_remaining(contest.start_time)
        elif contest.start_time <= now <= contest.end_time:
            contest_status = "ongoing"
            time_remaining = get_time_remaining(contest.end_time)
        else:
            contest_status = "ended"
            time_remaining = None
        
        result.append(
            ContestListOut(
                id=contest.id,
                title=contest.title,
                type=contest.type,
                status=contest_status,
                start_time=contest.start_time.isoformat() if contest.start_time else None,
                duration=contest.duration,
                difficulty=contest.difficulty,
                participants=getattr(contest, 'registrations_count', 0),
                max_participants=contest.max_participants,
                featured=contest.is_featured,
                registered=getattr(contest, 'user_is_registered', False) if user else False,
                time_remaining=time_remaining
            )
        )
    
    return result

@router.get("/contests/{contest_id}", response=ContestDetailOut, auth=None)
async def get_contest_detail(request, contest_id: int):
    """
    Bitta tanlov to'liq ma'lumotlari - PUBLIC
    """
    now = timezone.now()
    
    # Get contest with annotations
    contest = await Contest.objects.annotate(
        registrations_count=Count('registrations', filter=Q(registrations__is_active=True), distinct=True)
    ).filter(id=contest_id).afirst()
    
    if not contest:
        return 404, {"detail": "Contest not found"}
    
    # User registration status
    user = request.auth if hasattr(request, 'auth') else None
    registered = False
    user_registration = None
    
    if user:
        user_registration = await ContestRegistration.objects.filter(
            user=user,
            contest=contest,
            is_active=True
        ).afirst()
        registered = user_registration is not None
    
    # Status va vaqt
    if contest.start_time > now:
        status = "upcoming"
        time_remaining = get_time_remaining(contest.start_time)
        progress = 0
    elif contest.start_time <= now <= contest.end_time:
        status = "ongoing"
        time_remaining = get_time_remaining(contest.end_time)
        progress = get_progress_percentage(contest.start_time, contest.end_time)
    else:
        status = "ended"
        time_remaining = None
        progress = 100
    
    return ContestDetailOut(
        id=contest.id,
        title=contest.title,
        description=contest.description,
        type=contest.type,
        status=status,
        start_time=contest.start_time.isoformat() if contest.start_time else None,
        end_time=contest.end_time.isoformat() if contest.end_time else None,
        duration=contest.duration,
        difficulty=contest.difficulty,
        max_participants=contest.max_participants,
        prizes=contest.prizes or [],
        category=contest.category,
        featured=contest.is_featured,
        registered=registered,
        is_registration_open=status == "upcoming",
        can_join=status == "ongoing",
        participants_count=getattr(contest, 'registrations_count', 0),
        registrations_count=getattr(contest, 'registrations_count', 0),
        time_remaining=time_remaining,
        progress_percentage=progress,
        user_rank=user_registration.rank if user_registration else None,
        user_score=user_registration.total_score if user_registration else None,
        registered_at=user_registration.registered_at.isoformat() if user_registration and user_registration.registered_at else None
    )

@router.get("/contests/featured", response=List[ContestListOut], auth=None)
async def get_featured_contests(request):
    """
    Tanlangan (featured) tanlovlar - PUBLIC
    """
    now = timezone.now()
    
    queryset = Contest.objects.filter(
        is_featured=True,
        end_time__gt=now  # Faqat tugamaganlar
    ).annotate(
        registrations_count=Count('registrations', filter=Q(registrations__is_active=True), distinct=True)
    ).order_by('start_time')[:5]
    
    result = []
    async for contest in queryset:
        if contest.start_time > now:
            status = "upcoming"
            time_remaining = get_time_remaining(contest.start_time)
        else:
            status = "ongoing"
            time_remaining = get_time_remaining(contest.end_time)
        
        result.append(
            ContestListOut(
                id=contest.id,
                title=contest.title,
                type=contest.type,
                status=status,
                start_time=contest.start_time.isoformat() if contest.start_time else None,
                duration=contest.duration,
                difficulty=contest.difficulty,
                participants=getattr(contest, 'registrations_count', 0),
                max_participants=contest.max_participants,
                featured=True,
                registered=False,
                time_remaining=time_remaining
            )
        )
    
    return result

# ==================== PROTECTED ENDPOINTS (Token kerak) ====================

@router.post("/contests/{contest_id}/register", response=RegisterOut, auth=JWTAuth())
async def register_to_contest(request, contest_id: int, data: RegisterIn = None):
    """
    Tanlovga ro'yxatdan o'tish - TOKEN KERAK!
    """
    user = request.auth
    if not user:
        return 401, {"detail": "Authentication required"}
    
    # Get contest
    contest = await Contest.objects.filter(id=contest_id).afirst()
    if not contest:
        return 404, {"detail": "Contest not found"}
    
    # Check if contest is upcoming
    now = timezone.now()
    if contest.start_time <= now:
        return 400, {"detail": "Registration is closed"}
    
    # Check if already registered
    existing = await ContestRegistration.objects.filter(
        user=user,
        contest=contest,
        is_active=True
    ).aexists()
    
    if existing:
        return RegisterOut(
            success=True,
            message="Siz avval ro'yxatdan o'tgansiz!",
            contest_id=contest.id,
            contest_title=contest.title
        )
    
    # Check max participants
    current_participants = await ContestRegistration.objects.filter(
        contest=contest,
        is_active=True
    ).acount()
    
    if current_participants >= contest.max_participants:
        return 400, {"detail": "Tanlov ishtirokchilari soni to'ldi"}
    
    # Check access key for private contests
    if contest.type == "private":
        access_key = data.access_key if data else None
        if not access_key or access_key != contest.access_key:
            return 401, {"detail": "Noto'g'ri kirish kaliti"}
    
    # Create registration
    registration = await ContestRegistration.objects.acreate(
        user=user,
        contest=contest,
        is_active=True,
        total_score=0
    )
    
    return RegisterOut(
        success=True,
        message="Siz muvaffaqiyatli ro'yxatdan o'tdingiz!",
        contest_id=contest.id,
        contest_title=contest.title
    )

@router.get("/me/contests", response=List[MyContestOut], auth=JWTAuth())
async def my_contests(request):
    """
    Mening tanlovlarim - TOKEN KERAK!
    """
    user = request.auth
    if not user:
        return 401, {"detail": "Authentication required"}
    
    registrations = ContestRegistration.objects.filter(
        user=user,
        is_active=True
    ).select_related('contest').order_by('-registered_at')
    
    result = []
    async for reg in registrations:
        now = timezone.now()
        contest = reg.contest
        
        # Determine status
        if contest.start_time > now:
            status = "upcoming"
            time_remaining = get_time_remaining(contest.start_time)
        elif contest.start_time <= now <= contest.end_time:
            status = "ongoing"
            time_remaining = get_time_remaining(contest.end_time)
        else:
            status = "ended"
            time_remaining = None
        
        result.append(
            MyContestOut(
                id=contest.id,
                title=contest.title,
                status=status,
                registered_at=reg.registered_at.isoformat() if reg.registered_at else None,
                total_score=reg.total_score or 0,
                rank=reg.rank,
                start_time=contest.start_time.isoformat() if contest.start_time else None,
                end_time=contest.end_time.isoformat() if contest.end_time else None,
                time_remaining=time_remaining
            )
        )
    
    return result

@router.post("/contests/{contest_id}/unregister", auth=JWTAuth())
async def unregister_from_contest(request, contest_id: int):
    """
    Tanlovdan ro'yxatdan o'tishni bekor qilish - TOKEN KERAK!
    """
    user = request.auth
    if not user:
        return 401, {"detail": "Authentication required"}
    
    registration = await ContestRegistration.objects.filter(
        user=user,
        contest_id=contest_id,
        is_active=True
    ).afirst()
    
    if not registration:
        return 404, {"detail": "Siz bu tanlovda ro'yxatdan o'tmagansiz"}
    
    # Soft delete
    registration.is_active = False
    await registration.asave(update_fields=['is_active'])
    
    return {"success": True, "message": "Ro'yxatdan o'tish bekor qilindi"}

@router.post("/contests/{contest_id}/join", auth=JWTAuth())
async def join_contest(request, contest_id: int):
    """
    Tanlovga kirish (boshlash) - TOKEN KERAK!
    """
    user = request.auth
    if not user:
        return 401, {"detail": "Authentication required"}
    
    # Check registration
    registration = await ContestRegistration.objects.filter(
        user=user,
        contest_id=contest_id,
        is_active=True
    ).afirst()
    
    if not registration:
        return 403, {"detail": "Avval ro'yxatdan o'tishingiz kerak"}
    
    # Check if contest is ongoing
    contest = await Contest.objects.filter(id=contest_id).afirst()
    now = timezone.now()
    
    if now < contest.start_time:
        return 400, {"detail": f"Tanlov hali boshlanmadi. {get_time_remaining(contest.start_time)} dan keyin"}
    elif now > contest.end_time:
        return 400, {"detail": "Tanlov yakunlangan"}
    
    return {
        "success": True,
        "message": "Tanlovga xush kelibsiz!",
        "contest_id": contest.id,
        "contest_title": contest.title,
        "redirect_url": f"/contests/{contest_id}/problems"
    }

# ==================== ADMIN ENDPOINTS (Staff/Admin uchun) ====================

@router.post("/admin/contests", auth=JWTAuth())
async def create_contest(request, data: dict):
    """
    Yangi tanlov yaratish - ADMIN/STAFF
    """
    user = request.auth
    if not user or not user.is_staff:
        return 403, {"detail": "Admin huquqi talab qilinadi"}
    
    try:
        contest = await Contest.objects.acreate(
            title=data.get('title'),
            description=data.get('description'),
            type=data.get('type', 'open'),
            start_time=datetime.fromisoformat(data.get('start_time')),
            end_time=datetime.fromisoformat(data.get('end_time')),
            duration=data.get('duration'),
            max_participants=data.get('max_participants', 1000),
            difficulty=data.get('difficulty', 'medium'),
            prizes=data.get('prizes', []),
            access_key=data.get('access_key'),
            is_featured=data.get('featured', False),
            category=data.get('category')
        )
        
        return {
            "success": True,
            "id": contest.id,
            "title": contest.title,
            "message": "Tanlov muvaffaqiyatli yaratildi"
        }
    except Exception as e:
        return 400, {"detail": f"Xatolik: {str(e)}"}