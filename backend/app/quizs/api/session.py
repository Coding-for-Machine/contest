"""
Test Session API
================
Ushbu modul foydalanuvchining testni REAL vaqtda topshirish jarayonini boshqaradi:
boshlash (start), javob berish (bitta yoki ro'yxat), 50/50 lifeline, yakunlash (finish),
progress kuzatish va yakuniy TAHLIL (review).

MUHIM PRINSIP — JAVOBLAR QANDAY TEKSHIRILADI:
    Har bir /answer chaqiruvi FAQAT saqlaydi (UserResponse.update_or_create),
    HECH QANDAY tekshirish (grading) qilmaydi. Grading FAQAT /finish
    chaqirilganda, bitta atomik blokda, SESSIYADAGI BARCHA javoblar
    BIRGALIKDA (bittalab emas) TestSession.calculate_rasch_theta()
    orqali hisoblanadi.
"""

import random
import uuid
from datetime import timedelta
from typing import Annotated, List, Optional

import msgspec
from django_bolt import Router, Request, Depends
from django_bolt.params import Query
from django_bolt.exceptions import HTTPException
from asgiref.sync import sync_to_async

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from baseuser.models import BaseUser
from baseuser.authenticate import get_current_user_option, get_current_user
from quizs.models import Test, TestSession, TestEnrollment, Question, Choice, UserResponse

session_api = Router(tags=["Test Session API"])


# =========================================================
#              REQUEST / QUERY STRUKTURALARI (msgspec)
# =========================================================
class StartTestIn(msgspec.Struct):
    access_code: Optional[str] = None


class AnswerIn(msgspec.Struct):
    question_id: int
    choice_id: Optional[int] = None  # None = javobsiz qoldirish


class BulkAnswersIn(msgspec.Struct):
    answers: List[AnswerIn]


class LifelineIn(msgspec.Struct):
    question_id: int


class SessionHistoryParams(msgspec.Struct):
    limit: int = 10
    offset: int = 0


# =========================================================
#                    YORDAMCHI FUNKSIYALAR
# =========================================================
def _deadline(session: TestSession):
    return session.started_at + timedelta(minutes=session.test.duration_minutes)


def _is_time_expired(session: TestSession) -> bool:
    return timezone.now() > _deadline(session)


def _check_time_window(test: Test):
    """Test hozir ochiqmi (is_active + start_time/end_time oralig'i)."""
    now = timezone.now()
    if not test.is_active:
        raise HTTPException(status_code=403, detail="Bu test hozircha faol emas.")
    if now < test.start_time:
        raise HTTPException(status_code=403, detail="Test hali boshlanmagan.")
    if now > test.end_time:
        raise HTTPException(status_code=403, detail="Testni topshirish muddati tugagan.")


def _check_access_code(test: Test, provided_code: Optional[str]):
    """
    KIRISH OCHIQ / YOPIQ MANTIQI:
    - test.access_code bo'sh (None yoki "")  -> kirish OCHIQ, kod so'ralmaydi.
    - test.access_code to'ldirilgan bo'lsa   -> kirish YOPIQ, foydalanuvchidan
      aynan shu kod so'raladi.
    """
    if not test.access_code:
        return

    if not provided_code:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "access_code_required",
                "message": "Bu test yopiq. Davom etish uchun kirish kodini kiriting.",
            },
        )

    if provided_code != test.access_code:
        raise HTTPException(status_code=403, detail="Kirish kodi noto'g'ri.")


def _check_purchase(test: Test, user: BaseUser):
    if float(test.price) <= 0:
        return
    purchased = TestEnrollment.objects.filter(user=user, test=test).exists()
    if not purchased:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "payment_required",
                "message": "Ushbu test pullik. Davom etish uchun sotib oling.",
                "price": float(test.price),
            },
        )


def _check_attempts(test: Test, user: BaseUser):
    if test.max_attempts <= 0:
        return
    completed = TestSession.objects.filter(
        user=user, test=test, status=TestSession.Status.COMPLETED
    ).count()
    if completed >= test.max_attempts:
        raise HTTPException(
            status_code=403,
            detail=f"Siz ushbu testni maksimal {test.max_attempts} marta topshirib bo'lgansiz.",
        )


def _selected_questions_for(session: TestSession) -> List[dict]:
    """
    Agar test tasodifiy (random) savol tanlovidan foydalansa, tanlangan savol
    ID-lari seans davomida keshda saqlanadi.
    """
    test = session.test
    cache_key = f"quiz_session_questions_{session.id}"
    cached_ids = cache.get(cache_key)

    if cached_ids:
        ids = cached_ids
    else:
        is_rand = test.random_questions_count > 0 and test.question_count > test.random_questions_count
        if is_rand:
            ids = list(
                test.questions.order_by("?").values_list("id", flat=True)[: test.random_questions_count]
            )
        else:
            ids = list(test.questions.order_by("order", "created_at").values_list("id", flat=True))

        cache.set(cache_key, ids, timeout=test.duration_minutes * 60 + 300)

    questions = list(Question.objects.filter(id__in=ids).prefetch_related("choices"))
    by_id = {q.id: q for q in questions}
    ordered = [by_id[qid] for qid in ids if qid in by_id]

    return [
        {
            "id": q.id,
            "text": q.text,
            "order": q.order,
            # is_correct va explanation ATAYLAB chiqarilmaydi — javob sizib chiqmasligi uchun
            "choices": [
                {"id": c.id, "text": c.text, "order": c.order}
                for c in sorted(q.choices.all(), key=lambda c: c.order)
            ],
        }
        for q in ordered
    ]


def _session_progress(session: TestSession) -> dict:
    answered = UserResponse.objects.filter(session=session).exclude(choice__isnull=True).count()
    cache_key = f"quiz_session_questions_{session.id}"
    cached_ids = cache.get(cache_key)
    total = len(cached_ids) if cached_ids else session.test.questions.count()
    remaining = max(0, int((_deadline(session) - timezone.now()).total_seconds()))
    return {
        "session_id": str(session.id),
        "status": session.status,
        "answered_count": answered,
        "total_questions": total,
        "remaining_seconds": remaining if session.status == TestSession.Status.IN_PROGRESS else 0,
    }


def _get_owned_session(session_id: uuid.UUID, user: BaseUser) -> TestSession:
    try:
        return TestSession.objects.select_related("test").get(id=session_id, user=user)
    except TestSession.DoesNotExist:
        raise HTTPException(status_code=404, detail="Seans topilmadi.")


def _lifelines_left(session: TestSession) -> int:
    return max(0, session.test.max_lifelines - session.lifelines_used)


# =========================================================
#            1. TESTNI BOSHLASH   (POST /{slug}/start)
# =========================================================
@session_api.post("/{slug}/start")
async def start_test_session(
    request: Request,
    slug: str,
    payload: StartTestIn,
    request_user: BaseUser = Depends(get_current_user),
):
    def _run():
        try:
            test = Test.objects.select_related("intro_video").get(slug=slug)
        except Test.DoesNotExist:
            raise HTTPException(status_code=404, detail="Test topilmadi.")

        # --- Xavfsizlik zanjiri ---
        _check_time_window(test)
        _check_access_code(test, payload.access_code)
        _check_purchase(test, request_user)

        with transaction.atomic():
            existing = (
                TestSession.objects.select_for_update()
                .select_related("test")
                .filter(user=request_user, test=test, status=TestSession.Status.IN_PROGRESS)
                .order_by("-started_at")
                .first()
            )

            if existing:
                if _is_time_expired(existing):
                    existing.status = TestSession.Status.EXPIRED
                    existing.completed_at = timezone.now()
                    existing.save(update_fields=["status", "completed_at"])
                else:
                    # Tugallanmagan seans mavjud — uni davom ettiramiz
                    return existing, _selected_questions_for(existing), False

            # Yangi seans ochishdan oldin urinishlar sonini tekshiramiz
            _check_attempts(test, request_user)

            session = TestSession.objects.create(user=request_user, test=test)
            questions = _selected_questions_for(session)
            return session, questions, True

    session, questions, is_new = await sync_to_async(_run, thread_sensitive=True)()

    return {
        "session_id": str(session.id),
        "test_id": session.test_id,
        "test_slug": session.test.slug,
        "test_title": session.test.title,
        "is_new": is_new,
        "status": session.status,
        "duration_minutes": session.test.duration_minutes,
        "expires_at": _deadline(session).isoformat(),
        "lifelines": _lifelines_left(session),
        "questions": questions,
    }


# =========================================================
#      2. BITTA JAVOB YUBORISH  (POST /session/{id}/answer)
#         — darhol, sinxron tarzda qayta ishlanadi.
#         DIQQAT: bu yerda HECH QANDAY grading qilinmaydi.
# =========================================================
@session_api.post("/session/{session_id}/answer")
async def submit_single_answer(
    request: Request,
    session_id: uuid.UUID,
    payload: AnswerIn,
    request_user: BaseUser = Depends(get_current_user),
):
    def _run():
        session = _get_owned_session(session_id, request_user)

        if session.status != TestSession.Status.IN_PROGRESS:
            raise HTTPException(status_code=400, detail="Seans faol emas (yakunlangan yoki muddati o'tgan).")

        if _is_time_expired(session):
            session.status = TestSession.Status.EXPIRED
            session.completed_at = timezone.now()
            session.save(update_fields=["status", "completed_at"])
            raise HTTPException(status_code=410, detail="Test vaqti tugagan.")

        if not session.test.questions.filter(id=payload.question_id).exists():
            raise HTTPException(status_code=400, detail="Bu savol ushbu testga tegishli emas.")

        if payload.choice_id is not None and not Choice.objects.filter(
            id=payload.choice_id, question_id=payload.question_id
        ).exists():
            raise HTTPException(status_code=400, detail="Bu variant ushbu savolga tegishli emas.")

        UserResponse.objects.update_or_create(
            session=session,
            question_id=payload.question_id,
            user=request_user,
            defaults={"choice_id": payload.choice_id},
        )

    await sync_to_async(_run, thread_sensitive=True)()
    return {"question_id": payload.question_id, "accepted": True}


# =========================================================
#  3. RO'YXAT (LIST) KO'RINISHIDAGI JAVOBLAR
#     (POST /session/{id}/answers/bulk)
#     — barcha javoblarni bitta so'rovda saqlaydi.
# =========================================================
@session_api.post("/session/{session_id}/answers/bulk")
async def submit_bulk_answers(
    request: Request,
    session_id: uuid.UUID,
    payload: BulkAnswersIn,
    request_user: BaseUser = Depends(get_current_user),
):
    def _run():
        session = _get_owned_session(session_id, request_user)

        if session.status != TestSession.Status.IN_PROGRESS:
            raise HTTPException(status_code=400, detail="Seans faol emas.")

        if _is_time_expired(session):
            session.status = TestSession.Status.EXPIRED
            session.completed_at = timezone.now()
            session.save(update_fields=["status", "completed_at"])
            raise HTTPException(status_code=410, detail="Test vaqti tugagan.")

        # Barcha javoblarni bitta transactionda saqlaymiz
        with transaction.atomic():
            test_question_ids = set(session.test.questions.values_list("id", flat=True))
            
            for answer in payload.answers:
                if answer.question_id not in test_question_ids:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Savol ID {answer.question_id} ushbu testga tegishli emas."
                    )

                if answer.choice_id is not None and not Choice.objects.filter(
                    id=answer.choice_id, question_id=answer.question_id
                ).exists():
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Variant ID {answer.choice_id} savol {answer.question_id} ga tegishli emas."
                    )

                UserResponse.objects.update_or_create(
                    session=session,
                    question_id=answer.question_id,
                    user=request_user,
                    defaults={"choice_id": answer.choice_id},
                )

        return True

    await sync_to_async(_run, thread_sensitive=True)()
    return {"accepted": True, "count": len(payload.answers)}


# =========================================================
#      4. 50/50 LIFELINE   (POST /session/{id}/lifeline)
# =========================================================
@session_api.post("/session/{session_id}/lifeline")
async def use_lifeline(
    request: Request,
    session_id: uuid.UUID,
    payload: LifelineIn,
    request_user: BaseUser = Depends(get_current_user),
):
    def _run():
        session = _get_owned_session(session_id, request_user)

        if session.status != TestSession.Status.IN_PROGRESS:
            raise HTTPException(status_code=400, detail="Seans faol emas.")

        if _is_time_expired(session):
            session.status = TestSession.Status.EXPIRED
            session.completed_at = timezone.now()
            session.save(update_fields=["status", "completed_at"])
            raise HTTPException(status_code=410, detail="Test vaqti tugagan.")

        with transaction.atomic():
            locked_session = TestSession.objects.select_for_update().select_related("test").get(id=session.id)

            if locked_session.lifelines_used >= locked_session.test.max_lifelines:
                raise HTTPException(status_code=403, detail="Lifeline'lar tugagan.")

            try:
                question = locked_session.test.questions.get(id=payload.question_id)
            except Question.DoesNotExist:
                raise HTTPException(status_code=400, detail="Bu savol ushbu testga tegishli emas.")

            wrong_ids = list(question.choices.filter(is_correct=False).values_list("id", flat=True))
            if len(wrong_ids) < 2:
                raise HTTPException(status_code=400, detail="Bu savolda 50/50 uchun yetarli variant yo'q.")

            eliminate_ids = random.sample(wrong_ids, 2)

            locked_session.lifelines_used += 1
            locked_session.save(update_fields=["lifelines_used"])

            return eliminate_ids, _lifelines_left(locked_session)

    eliminate_ids, lifelines_left = await sync_to_async(_run, thread_sensitive=True)()
    return {"eliminated_choice_ids": eliminate_ids, "lifelines_left": lifelines_left}


# =========================================================
#      5. TESTNI YAKUNLASH   (POST /session/{id}/finish)
#
#      BU YERDA (va FAQAT SHU YERDA) grading amalga oshadi.
#      Rasch MLE + XP + JMLE Celery task.
# =========================================================
@session_api.post("/session/{session_id}/finish")
async def finish_test_session(
    request: Request,
    session_id: uuid.UUID,
    request_user: BaseUser = Depends(get_current_user),
):
    def _validate():
        session = _get_owned_session(session_id, request_user)

        if session.status == TestSession.Status.COMPLETED:
            return session, True  # Allaqachon yakunlangan

        if session.status == TestSession.Status.IN_PROGRESS and _is_time_expired(session):
            session.status = TestSession.Status.EXPIRED
            session.save(update_fields=["status"])

        return session, False

    session, already_completed = await sync_to_async(_validate, thread_sensitive=True)()

    # Agar hali yakunlanmagan va faol bo'lsa — Rasch hisoblash
    if not already_completed and session.status == TestSession.Status.IN_PROGRESS:
        await session.calculate_rasch_theta()
        # DB dan yangilangan qiymatlarni o'qiymiz
        session = await TestSession.objects.select_related("test").aget(pk=session.id)

    return {
        "session_id": str(session.id),
        "status": session.status,
        "rasch_theta": session.rasch_theta,
        "rasch_se": session.rasch_se,
        "raw_percentage": session.raw_percentage,
        "progress": round(session.calculate_percentage(), 2) if session.rasch_theta is not None else 0.0,
        "passed": session.passed,
        "correct_count": session.correct_count,
        "wrong_count": session.wrong_count,
        "unanswered_count": session.unanswered_count,
        "total_xp_earned": session.total_xp_earned,
    }


# =========================================================
#   6. JORIY SEANS HOLATI   (GET /session/{id})
# =========================================================
@session_api.get("/session/{session_id}")
async def get_session_status(
    request: Request,
    session_id: uuid.UUID,
    request_user: BaseUser = Depends(get_current_user),
):
    def _run():
        session = _get_owned_session(session_id, request_user)
        return _session_progress(session)

    return await sync_to_async(_run, thread_sensitive=True)()


# =========================================================
#   7. SEANSNING SAVOLLARINI QAYTA OLISH  (GET /session/{id}/questions)
# =========================================================
@session_api.get("/session/{session_id}/questions")
async def get_session_questions(
    request: Request,
    session_id: uuid.UUID,
    request_user: BaseUser = Depends(get_current_user),
):
    def _run():
        session = _get_owned_session(session_id, request_user)
        questions = _selected_questions_for(session)

        saved_answers = {
            r.question_id: r.choice_id
            for r in UserResponse.objects.filter(session=session)
        }

        return {
            "session_id": str(session.id),
            "test_id": session.test_id,
            "test_slug": session.test.slug,
            "test_title": session.test.title,
            "status": session.status,
            "duration_minutes": session.test.duration_minutes,
            "expires_at": _deadline(session).isoformat(),
            "lifelines": _lifelines_left(session),
            "questions": questions,
            "saved_answers": saved_answers,
        }

    return await sync_to_async(_run, thread_sensitive=True)()


# =========================================================
#   8. YAKUNIY TAHLIL  (GET /session/{id}/review)
# =========================================================
@session_api.get("/session/{session_id}/review")
async def get_session_review(
    request: Request,
    session_id: uuid.UUID,
    request_user: BaseUser = Depends(get_current_user),
):
    def _run():
        session = _get_owned_session(session_id, request_user)
        if session.status not in (TestSession.Status.COMPLETED, TestSession.Status.EXPIRED):
            raise HTTPException(status_code=400, detail="Tahlil faqat yakunlangan seanslar uchun mavjud.")

        questions = list(
            session.test.questions.order_by("order", "created_at").prefetch_related("choices")
        )
        responses = {
            r.question_id: r.choice_id
            for r in UserResponse.objects.filter(session=session)
        }

        items = []
        for q in questions:
            choices = sorted(q.choices.all(), key=lambda c: c.order)
            correct = next((c for c in choices if c.is_correct), None)
            chosen_id = responses.get(q.id)
            items.append({
                "id": q.id,
                "text": q.text,
                "chosen_choice_id": chosen_id,
                "correct_choice_id": correct.id if correct else None,
                "is_correct": chosen_id is not None and correct is not None and chosen_id == correct.id,
                "choices": [
                    {"id": c.id, "text": c.text, "is_correct": c.is_correct, "is_chosen": c.id == chosen_id}
                    for c in choices
                ],
                "explanation": correct.explanation if correct else None,
                "explanation_video": (
                    {
                        "hls": q.explanation_video.hls_url,
                        "img": q.explanation_video.thumbnail.url if q.explanation_video.thumbnail else None,
                    } if q.explanation_video else None
                ),
            })

        return {
            "session_id": str(session.id),
            "test_title": session.test.title,
            "status": session.status,
            "rasch_theta": session.rasch_theta,
            "rasch_se": session.rasch_se,
            "raw_percentage": session.raw_percentage,
            "progress": round(session.calculate_percentage(), 2) if session.rasch_theta is not None else 0.0,
            "passed": session.passed,
            "correct_count": session.correct_count,
            "wrong_count": session.wrong_count,
            "unanswered_count": session.unanswered_count,
            "total_xp_earned": session.total_xp_earned,
            "started_at": session.started_at.isoformat(),
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "questions": items,
        }

    return await sync_to_async(_run, thread_sensitive=True)()


# =========================================================
#   9. FOYDALANUVCHINING USHBU TEST BO'YICHA URINISHLARI
#      (GET /{slug}/sessions?limit=&offset=)
# =========================================================
@session_api.get("/{slug}/sessions")
async def get_my_sessions_for_test(
    request: Request,
    slug: str,
    params: Annotated[SessionHistoryParams, Query()],
    request_user: BaseUser = Depends(get_current_user),
):
    test_id = await (
        Test.objects
        .filter(slug=slug)
        .values_list("id", flat=True)
        .afirst()
    )

    if not test_id:
        raise HTTPException(
            status_code=404,
            detail="Test topilmadi.",
        )

    queryset = (
        TestSession.objects
        .filter(
            user_id=request_user.id,
            test_id=test_id,
        )
        .select_related("test")
        .only(
            "id",
            "status",
            "rasch_theta",
            "rasch_se",
            "raw_percentage",
            "correct_count",
            "wrong_count",
            "unanswered_count",
            "total_xp_earned",
            "started_at",
            "completed_at",

            # s.passed / test threshold uchun
            "test__rasch_theta_pass_threshold",
        )
        .order_by("-started_at")[
            params.offset : params.offset + params.limit
        ]
    )

    data = []

    async for s in queryset:
        passed = (
            s.rasch_theta is not None
            and s.rasch_theta >= s.test.rasch_theta_pass_threshold
        )

        progress = (
            round(s.calculate_percentage(), 2)
            if s.rasch_theta is not None
            else 0.0
        )

        data.append({
            "session_id": str(s.id),
            "status": s.status,
            "rasch_theta": s.rasch_theta,
            "rasch_se": s.rasch_se,
            "raw_percentage": s.raw_percentage,
            "progress": progress,
            "passed": passed,
            "correct": s.correct_count,
            "wrong": s.wrong_count,
            "unanswered": s.unanswered_count,
            "xp": s.total_xp_earned,
            "started_at": s.started_at.strftime("%Y-%m-%d %H:%M"),
            "completed_at": (
                s.completed_at.strftime("%Y-%m-%d %H:%M")
                if s.completed_at
                else None
            ),
        })

    total_count = await (
        TestSession.objects
        .filter(
            user_id=request_user.id,
            test_id=test_id,
        )
        .acount()
    )

    return {
        "count": total_count,
        "limit": params.limit,
        "offset": params.offset,
        "data": data,
    }
# =========================================================
#   10. UMUMIY STATISTIKA WIDJETI   (GET /stats/)
# =========================================================
@session_api.get("/stats")
async def test_stats(request: Request, request_user: Optional[BaseUser] = Depends(get_current_user_option)):
    cache_key = "tests_stats_total_active"
    total_active = await cache.aget(cache_key)
    if total_active is None:
        total_active = await Test.objects.filter(is_active=True).acount()
        await cache.aset(cache_key, total_active, timeout=300)

    if not request_user:
        return {"total": total_active, "attempted": 0, "passed": 0, "total_xp": 0}

    def _compute_user_stats():
        attempted_count = (
            TestSession.objects.filter(user_id=request_user.id)
            .values("test_id")
            .distinct()
            .count()
        )

        best_sessions = {}
        completed_qs = TestSession.objects.filter(
            user_id=request_user.id, status=TestSession.Status.COMPLETED
        ).select_related("test")

        for s in completed_qs:
            prev = best_sessions.get(s.test_id)
            if not prev or (s.rasch_theta or -999) > (prev.rasch_theta or -999):
                best_sessions[s.test_id] = s

        passed_count = 0
        total_xp = 0
        for s in best_sessions.values():
            total_xp += s.total_xp_earned
            if s.passed:
                passed_count += 1

        return attempted_count, passed_count, total_xp

    attempted_count, passed_count, total_xp = await sync_to_async(
        _compute_user_stats, thread_sensitive=True
    )()

    return {
        "total": total_active,
        "attempted": attempted_count,
        "passed": passed_count,
        "xp": total_xp,
    }