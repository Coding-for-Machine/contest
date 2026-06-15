from django.utils import timezone
from django.db.models import OuterRef, Subquery, Max, Count, Q
from ninja import Router, Query, Schema
from ninja.errors import HttpError
from typing import List

from django.db import transaction 
from .models import Certificate, Test, TestSession, UserRank, UserResponse
from .schemas import CertificateOut, HistoryOut, LeaderboardUserOut, TestListOut, TestFilterSchema, TestResultOut, TestStartOut, TestSubmitPayload
from baseuser.authenticate import JWTAuth # Sizning JWTAuth klassingiz

router = Router(tags=["Test va Olimpiadalar"])

@router.get("/tests", response=List[TestListOut], auth=JWTAuth())
def list_available_tests(request, filters: TestFilterSchema = Query(...)):
    user = request.auth
    now = timezone.now()

    queryset = Test.objects.filter(is_active=True)

    # Qidiruv filtri
    if filters.search:
        queryset = queryset.filter(title__icontains=filters.search)

    # Vaqt filtri
    if filters.status == "active":
        queryset = queryset.filter(start_time__lte=now, end_time__gte=now)
    elif filters.status == "upcoming":
        queryset = queryset.filter(start_time__gt=now)
    elif filters.status == "ended":
        queryset = queryset.filter(end_time__lt=now)

    # SQL darajasida eng yuqori ballni hisoblash (N+1 muammosiz)
    best_score_subquery = TestSession.objects.filter(
        user=user, test_id=OuterRef('pk'), status='completed'
    ).values('test_id').annotate(max_score=Max('score')).values('max_score')

    test_sessions = TestSession.objects.filter(user=user, test_id=OuterRef('pk'))
    
    queryset = queryset.annotate(
        user_attempts_count=Count(Subquery(test_sessions.values('id'))),
        has_in_progress=Count(Subquery(test_sessions.filter(status='in_progress').values('id'))),
        computed_best_score=Subquery(best_score_subquery)
    ).order_by("-created_at")

    results = []
    for test in queryset:
        attempts_left = 999 if test.max_attempts == 0 else max(0, test.max_attempts - test.user_attempts_count)
        
        if test.has_in_progress > 0:
            user_status = "in_progress"
        elif test.user_attempts_count > 0:
            user_status = "completed"
        else:
            user_status = "not_started"

        results.append(TestListOut(
            id=test.id, title=test.title, duration_minutes=test.duration_minutes,
            question_count=test.question_count, start_time=test.start_time, end_time=test.end_time,
            min_pass_percentage=test.min_pass_percentage, max_attempts=test.max_attempts,
            attempts_left=attempts_left, user_status=user_status, best_score=test.computed_best_score
        ))
    return results

@router.post("/tests/{test_id}/start", response=TestStartOut, auth=JWTAuth())
def start_test_session(request, test_id: int):
    user = request.auth
    now = timezone.now()

    # 1. Test mavjudligi va faolligini tekshirish
    try:
        test = Test.objects.get(id=test_id, is_active=True)
    except Test.DoesNotExist:
        raise HttpError(404, "Test topilmadi!")

    # 2. Test vaqtinchalik muddati faolligini tekshirish
    if not (test.start_time <= now <= test.end_time):
        raise HttpError(400, "Ushbu test muddati hozir faol emas!")

    # 3. Avval ochilgan va yakunlanmagan (IN_PROGRESS) seansni tekshirish
    existing_session = TestSession.objects.filter(
        user=user, 
        test=test, 
        status=TestSession.Status.IN_PROGRESS
    ).first()

    if existing_session:
        elapsed_time = now - existing_session.started_at
        seconds_left = int((test.duration_minutes * 60) - elapsed_time.total_seconds())

        # Agar vaqt tugab bo'lgan bo'lsa, sessiyani yopamiz
        if seconds_left <= 0:
            existing_session.status = TestSession.Status.EXPIRED
            existing_session.completed_at = now
            existing_session.save()
            raise HttpError(400, "Test topshirish vaqti tugagan!")

        # Vaqt tugamagan bo'lsa, eski sessiyani aniq 200 kodi bilan qaytaramiz
        questions = test.questions.prefetch_related('choices').all()
        return 200, {
            "session_id": existing_session.id,
            "duration_minutes": test.duration_minutes,
            "seconds_left": seconds_left,
            "questions": list(questions)
        }

    # 4. Maksimal urinishlar sonini tekshirish
    completed_attempts = TestSession.objects.filter(user=user, test=test).count()
    if test.max_attempts > 0 and completed_attempts >= test.max_attempts:
        raise HttpError(400, "Sizda urinishlar soni qolmagan!")

    # 5. Mutlaqo yangi sessiya ochish (Muvaffaqiyatli holat)
    new_session = TestSession.objects.create(
        user=user, 
        test=test, 
        status=TestSession.Status.IN_PROGRESS, 
        started_at=now
    )
    questions = test.questions.prefetch_related('choices').all()
    
    # Aniq 200 status kodi bilan yangi ma'lumotlarni qaytaramiz
    return 200, {
        "session_id": new_session.id,
        "duration_minutes": test.duration_minutes,
        "seconds_left": test.duration_minutes * 60,
        "questions": list(questions)
    }

class ErrorOut(Schema):
    message: str

@router.post("/tests/submit", response={200: TestResultOut, 400: ErrorOut}, auth=JWTAuth())
def submit_test(request, payload: TestSubmitPayload):
    user = request.auth
    now = timezone.now()

    # 1. IN_PROGRESS holatidagi faol sessiyani bazadan qidirish
    try:
        # N+1 muammosini oldini olish uchun test ma'lumotlarini select_related bilan yuklaymiz
        session = TestSession.objects.select_related('test').get(
            user=user, 
            test_id=payload.test_id, 
            status=TestSession.Status.IN_PROGRESS
        )
    except TestSession.DoesNotExist:
        return 400, {"message": "Faol test seansi topilmadi!"}

    # 2. 1 daqiqa tarmoq zapasi bilan qat'iy vaqt tekshiruvi
    test = session.test
    max_time = session.started_at + timezone.timedelta(minutes=test.duration_minutes + 1)

    if now > max_time:
        with transaction.atomic():
            session.status = TestSession.Status.EXPIRED
            session.completed_at = now
            session.save()
        return 400, {"message": "Vaqt o'tib ketganligi sababli test rad etildi!"}

    # 3. Tranzaksiya ichida javoblarni yozish va sertifikat yaratish
    with transaction.atomic():
        # Javoblarni bittada yozish (Bulk create)
        responses = [
            UserResponse(session=session, question_id=ans.question_id, selected_choice_id=ans.selected_choice_id)
            for ans in payload.answers
        ]
        UserResponse.objects.bulk_create(responses)
        
        # Matematika formulasini yuritish (Model ichidagi mantiq)
        final_score = session.calculate_mathematical_score()
        
        # Bazadan yangilangan hisob-kitob ballarini (score, correct_count va hk) joriy obyektga yuklash
        session.refresh_from_db()

        # Sertifikat va o'tish foizini tekshirish
        total_xp = sum(q.xp for q in test.questions.all())
        percentage = (max(0, final_score) / total_xp) * 100 if total_xp > 0 else 0
        is_passed = percentage >= test.min_pass_percentage

        cert_issued, cert_url = False, None
        if is_passed and hasattr(test, 'certificate_template') and test.certificate_template:
            template = test.certificate_template
            if percentage >= template.min_percentage:
                cert, _ = Certificate.objects.get_or_create(
                    user=user, 
                    template=template, 
                    test_session=session, 
                    test=test
                )
                cert_issued = True
                cert_url = cert.pdf_file.url if cert.pdf_file else None

    # 4. Foydalanuvchi unvonini (Rank) xavfsiz aniqlash
    user_rank = getattr(user, 'rank_profile', None)
    rank_level_value = user_rank.get_level_display() if user_rank else "Yangi boshlovchi"

    # 5. Django Ninja formatida muvaffaqiyatli 200 javobini qaytarish
    return 200, {
        "session_id": session.id,
        "score": getattr(session, 'score', 0),
        "correct_count": getattr(session, 'correct_count', 0),
        "wrong_count": getattr(session, 'wrong_count', 0),
        "unanswered_count": getattr(session, 'unanswered_count', 0),
        "rank_level": rank_level_value,
        "is_passed": is_passed,
        "certificate_issued": cert_issued,
        "certificate_url": cert_url
    }


@router.get("/dashboard/history", response=List[HistoryOut], auth=JWTAuth())
def get_user_history(request):
    """Foydalanuvchining barcha topshirgan testlari tarixi ro'yxati"""
    sessions = TestSession.objects.filter(
        user=request.auth
    ).select_related('test').order_by('-started_at')
    
    return [
        HistoryOut(
            session_id=s.id,
            test_title=s.test.title,
            score=s.score,
            status=s.get_status_display(),
            completed_at=s.completed_at
        ) for s in sessions
    ]


@router.get("/certificates", response=List[CertificateOut], auth=JWTAuth())
def get_my_certificates(request):
    """Talabaning yutib olgan barcha sertifikatlari ro'yxati"""
    certs = Certificate.objects.filter(
        user=request.auth
    ).select_related('test').order_by('-issued_at')
    
    return [
        CertificateOut(
            id=c.id,
            test_title=c.test.title if c.test else "Umumiy Kurs",
            certificate_code=c.certificate_code,
            pdf_url=c.pdf_file.url if c.pdf_file else None,
            issued_at=c.issued_at
        ) for c in certs
    ]


@router.get("/leaderboard", response=List[LeaderboardUserOut])
def global_leaderboard(request):
    """Eng yuqori ball to'plagan Top-20 foydalanuvchilar reytingi"""
    ranks = UserRank.objects.select_related('user')[:20]
    
    return [
        LeaderboardUserOut(
            username=r.user.username if r.user.username else f"user#{r.user.telegram_id}",
            total_xp=r.total_xp,
            level_display=r.get_level_display()
        ) for r in ranks
    ]
