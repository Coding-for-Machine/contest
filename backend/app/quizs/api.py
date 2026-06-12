from ninja import Router, Schema
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from typing import List, Optional
from datetime import datetime, timedelta
from ninja.errors import HttpError

from .models import Test, Question, TestSession, UserAnswer, Choice
from status.models import UserStats # Avvalgi UserStats modeli
from baseuser.authenticate import JWTAuth
from baseuser.models import BaseUser
quiz_api = Router(tags=["Test"])


class QuizOut(Schema):
    id: int
    title: str
    duration_minutes: int
    question_count: int
    max_attempts: int
    has_access_code: bool
    updated_at: datetime

class ChoiceOut(Schema):
    id: int
    text: str

class QuestionOut(Schema):
    id: int
    text: str
    image: Optional[str] = None
    choices: List[ChoiceOut] # Savol bilan birga variantlarni ham yuboramiz

class AnswerIn(Schema):
    question_id: int
    choice_id: int

class SessionOut(Schema):
    session_id: int
    status: str
    started_at: datetime

class ResultOut(Schema):
    score: int
    total_questions: int
    percentage: float
    xp_earned: int
    status: str

class StartTestIn(Schema):
    access_code: Optional[str] = None 

def get_authenticated_user(request):
    user = getattr(request, "auth", None)
    return user if (user and user is not True) else None

# 1. Barcha ochiq testlarni olish
@quiz_api.get("/", response=List[QuizOut])
def get_all_quizzes(request):
    quizs = []
    for q in Test.objects.filter(is_active=True, lesson__isnull=True):
        quizs.append({
            "id": q.id,
            "title": q.title,
            "duration_minutes": q.duration_minutes,
            "question_count": q.question_count,
            "max_attempts": q.max_attempts,
            "has_access_code": True if q.access_code else False,
            "updated_at": q.updated_at,
        })
    return quizs

# 2. Test sessiyasini boshlash (Urinishlarni tekshirish bilan)
@quiz_api.post("/{test_id}/start", auth=[JWTAuth(), lambda request: True])
def start_test(request, test_id: int, data: StartTestIn):
    # user = get_authenticated_user(request)
    user = BaseUser.objects.get(id=1)

    test = get_object_or_404(Test, id=test_id, is_active=True)
    # 1. Avval tugallanmagan sessiya bor-yo'qligini tekshiramiz
    active_session = TestSession.objects.filter(
        user=user, 
        test=test, 
        status=TestSession.Status.IN_PROGRESS,
    ).first()

    # 2. Agar aktiv sessiya bo'lsa va muddati o'tmagan bo'lsa, o'shani qaytaramiz
    if active_session:
        if not active_session.is_expired: # is_expired property-sini modelda yozgan edik
            end_time = active_session.started_at + timedelta(minutes=test.duration_minutes)
            return {"session_id": active_session.id, "status": active_session.status, "end_time": end_time}
        else:
            # Muddati o'tgan bo'lsa, yopib qo'yamiz
            active_session.status = TestSession.Status.EXPIRED
            active_session.save()

    # 3. Yangi sessiya yaratishdan oldin urinishlar sonini tekshiramiz
    attempts_count = TestSession.objects.filter(user=user, test=test).count()
    if test.max_attempts > 0 and attempts_count >= test.max_attempts:
        raise HttpError(403, "Barcha urinishlaringiz tugagan!")
    
    duration = timedelta(minutes=test.duration_minutes)
    expected_end = timezone.now() + duration

    session = TestSession.objects.create(
        user=user,
        test=test,
        total_questions=test.questions.count(),
        ended_at=expected_end,  # <--- Bu qiymat None bo'lmasligi shart
        status=TestSession.Status.IN_PROGRESS
    )

    return {
        "session_id": session.id, 
        "status": session.status, 
        "end_time": session.ended_at
    }
# 3. Sessiya savollarini olish (Variantlari bilan)
@quiz_api.get("/session/{session_id}/questions")
def get_questions(request, session_id: int):
    # 1. Sessiyani olish (request.auth ishlatish tavsiya etiladi)
    # user = get_authenticated_user(request)
    user = BaseUser.objects.get(id=1)

    session = get_object_or_404(TestSession, id=session_id, user=user)
    
    # 2. Vaqtni tekshirish (oldindan yozgan is_expired property orqali)
    if session.is_expired:
        session.status = TestSession.Status.EXPIRED
        session.save()
        raise HttpError(403, "Vaqt tugagan, savollarni olib bo'lmaydi")

    # 3. Savollarni variantlari bilan olish
    questions = session.test.questions.prefetch_related('choices').all()
    
    result = []
    for q in questions:
        # Har bir savol uchun variantlarni dict ko'rinishida yig'amiz
        choices = []
        for c in q.choices.all():
            choices.append({
                "id": c.id,
                "text": c.text
            })
            
        # Savol ma'lumotlarini dict ko'rinishida qo'shamiz
        result.append({
            "id": q.id,
            "text": q.text,
            "difficulty": q.difficulty,
            "xp": q.xp,
            "image": q.image.url if q.image else None,
            "choices": choices  # Variantlar ro'yxati
        })
        
    return result

# 4. Javobni saqlash (Har bir savol uchun alohida)
@quiz_api.post("/session/{session_id}/answer")
def submit_answer(request, session_id: int, data: AnswerIn):
    # 1. Sessiyani olish (request.auth ishlatish tavsiya etiladi)
    # user = get_authenticated_user(request)
    user = BaseUser.objects.get(id=1)
    session = get_object_or_404(TestSession, id=session_id, user=user, status="in_progress")
    
    # 2. Vaqt o'tib ketganini tekshirish (is_expired property orqali)
    if session.is_expired:
        session.status = TestSession.Status.EXPIRED
        session.save()
        return {
            "message": "Vaqt tugagan! Javob qabul qilinmadi.",
            "status": session.status
        }

    # 3. XAVFSIZLIK: Choice aynan berilgan question_id ga tegishli ekanini tekshiramiz
    # Bu orqali foydalanuvchi boshqa savolning to'g'ri javob ID-sini ishlata olmaydi
    choice = get_object_or_404(Choice, id=data.choice_id, question_id=data.question_id)

    # 4. Javobni saqlash yoki yangilash
    answer, created = UserAnswer.objects.update_or_create(
        session=session, 
        question_id=data.question_id,
        defaults={
            'choice': choice, 
            'is_correct': choice.is_correct
        }
    )

    return {
        "is_updated": not created,
        "question_id": data.question_id,
        "remaining_seconds": session.time_left # Property orqali qolgan vaqtni qaytarish foydali
    }


# 5. Testni yakunlash va XP hisoblash
@quiz_api.post("/session/{session_id}/finish", response=ResultOut)
def finish_test(request, session_id: int):
    session = get_object_or_404(TestSession, id=session_id, user=request.user, status="in_progress")
    
    # 1. Natijalarni hisoblash
    answers = session.answers.all()
    correct_count = answers.filter(is_correct=True).count()
    total_xp = sum(a.question.xp for a in answers.filter(is_correct=True))
    
    # 2. Sessiyani yangilash
    session.score = correct_count
    session.total_xp_earned = total_xp
    if session.total_questions > 0:
        session.percentage = (correct_count / session.total_questions) * 100
    session.status = "completed"
    session.ended_at = timezone.now()
    session.save()

    # 3. UserStats ga XP qo'shish (Gamifikatsiya)
    stats, _ = UserStats.objects.get_or_create(user=request.user)
    stats.xp += total_xp
    stats.test_count += 1
    stats.save()

    return {
        "score": session.score,
        "total_questions": session.total_questions,
        "percentage": float(session.percentage),
        "xp_earned": total_xp,
        "status": session.status
    }
