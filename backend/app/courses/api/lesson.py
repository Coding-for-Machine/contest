import asyncio
from django.db import IntegrityError
import httpx
from collections.abc import AsyncIterable
from django_bolt import Router, Request, Depends
from django_bolt.responses import EventSourceResponse, ServerSentEvent
from django_bolt.exceptions import HTTPException
from django.apps import apps
from django.db.models import Prefetch
from problems.models import Problem, Tags, Language, Hint, Challenge, Function

from problems.models import ExecutionTestCase, Language, Problem, Tags, TestCase
from quizs.models import Choice, Question, UserResponse
from courses.models import Lesson, Lecture
from baseuser.models import BaseUser
from status.models import LectureStatus, LessonStatus
from baseuser.authenticate import get_current_user_option

api = Router(tags=["lesson api"])


# ─── 1. DARS ──────────────────────────────────────────────────────────────────
@api.get("/{slug}/")
async def get_lesson_api(
    request: Request,
    slug: str,
    request_user: BaseUser | None = Depends(get_current_user_option)
):
    if not request_user:
        raise HTTPException(status_code=401, detail="Tizimga kirish talab qilinadi!")

    lesson = await (
        Lesson.objects
        .filter(slug=slug)
        .select_related('modul')
        .prefetch_related(
            Prefetch(
                'lectures',
                queryset=Lecture.objects.only('id', 'lesson_id', 'title', 'slug', 'order').order_by('id')
            ),
            Prefetch(
                'problems',
                queryset=Problem.objects.only('id', 'title', 'slug', 'is_active').order_by('id')
            ),
            Prefetch(
                'quiz_questions',
                queryset=Question.objects.only('id', 'order', 'difficulty').order_by('id')
            )
        )
        .afirst()
    )

    if not lesson:
        raise HTTPException(status_code=404, detail="Darslik topilmadi!")

    # Oldingi dars bloklash
    prev_lesson = await (
        Lesson.objects
        .filter(modul__course_id=lesson.modul.course_id, id__lt=lesson.id)
        .order_by('-id')
        .only('id')
        .afirst()
    )

    if prev_lesson:
        prev_done = await LessonStatus.objects.filter(
            user_id=request_user.id, lesson_id=prev_lesson.id, is_completed=True
        ).aexists()

        if not prev_done:
            raise HTTPException(
                status_code=403,
                detail="Ushbu dars bloklangan! Avvalgi darsni to'liq yakunlashingiz shart."
            )

    # prefetch cache → oddiy for (async for emas!)
    return {
        "title":       lesson.title,
        "slug":        lesson.slug,
        "total_tasks": lesson.total_tasks_count,
        "complate":    True,
        "lectures": [
            {"title": lec.title, "slug": lec.slug, "order": lec.order}
            for lec in lesson.lectures.all()
        ],
        "problems": [
            {"title": p.title, "slug": p.slug}
            for p in lesson.problems.all() if p.is_active
        ],
        "questions": [
            {"id": q.id, "order": q.order, "diff": q.difficulty}
            for q in lesson.quiz_questions.all()
        ],
    }


# ─── 2. MA'RUZA ───────────────────────────────────────────────────────────────
@api.get("/{slug}/lectures/{lecture_slug}/")
async def get_single_lecture_api(
    request: Request,
    slug: str,
    lecture_slug: str,
    request_user: BaseUser | None = Depends(get_current_user_option)
):
    if not request_user:
        raise HTTPException(status_code=401, detail="Tizimga kirish talab qilinadi!")

    # is_completed + lecture parallel
    lecture, is_completed = await asyncio.gather(
        Lecture.objects
            .filter(slug=lecture_slug, lesson__slug=slug)
            .select_related('video')
            .only(
                'id', 'title', 'body', 'xp',
                'video__id', 'video__hls_url', 'video__video',
                'video__thumbnail', 'video__duration'
            )
            .afirst(),

        LectureStatus.objects
            .filter(user_id=request_user.id, lecture__slug=lecture_slug, is_completed=True)
            .aexists(),
    )

    if not lecture:
        raise HTTPException(status_code=404, detail="Ma'ruza topilmadi!")

    video_data = None
    if lecture.video:
        v = lecture.video
        video_data = {
            "src":   v.hls_url or (v.video.url if v.video else None),
            "thumb": v.thumbnail.url if v.thumbnail else None,
            "dur":   v.duration,
        }

    return {
        "title":  lecture.title,
        "body":   lecture.body,
        "xp":     lecture.xp,
        "is_cmp": is_completed,
        "video":  video_data,
    }


# ─── 3. MA'RUZA COMPLETE ──────────────────────────────────────────────────────
@api.post("/{lesson_slug}/lectures/{lecture_slug}/complete/")
async def mark_lecture_complete(
    request: Request,
    lesson_slug: str,
    lecture_slug: str,
    request_user: BaseUser | None = Depends(get_current_user_option)
):
    if not request_user:
        raise HTTPException(status_code=401, detail="Tizimga kirish talab qilinadi!")
    lecture_data = await (
        Lecture.objects
        .filter(slug=lecture_slug, lesson__slug=lesson_slug)
        .values('id', 'xp')
        .afirst()
    )

    if not lecture_data:
        raise HTTPException(status_code=404, detail="Ma'ruza topilmadi!")

    lecture_id = lecture_data['id']
    lecture_xp = lecture_data['xp']

    try:
        # aget_or_create — parallel so'rovlar (Race Condition) oldini oladi
        status, created = await LectureStatus.objects.aget_or_create(
            user_id=request_user.id,
            lecture_id=lecture_id,
            defaults={'is_completed': True}
        )
    except IntegrityError:
        created = False

    return {
        "ok": True, 
        "already_completed": not created,
        "xp": lecture_xp if created else 0
    }


# ─── 4. QUIZ SAVOL ────────────────────────────────────────────────────────────
@api.get("/{slug}/quizzes/{question_id}/")
async def get_single_quiz_api(
    request: Request,
    slug: str,
    question_id: int,
    request_user: BaseUser | None = Depends(get_current_user_option)
):
    if not request_user:
        raise HTTPException(status_code=401, detail="Tizimga kirish talab qilinadi!")

    # question + last_resp parallel
    question, last_resp = await asyncio.gather(
        Question.objects
            .filter(id=question_id, lesson__slug=slug)
            .select_related('explanation_video')
            .prefetch_related(
                Prefetch(
                    'choices',
                    queryset=Choice.objects.only('id', 'question_id', 'text', 'order').order_by('order', 'id')
                )
            )
            .only(
                'id', 'lesson_id', 'text', 'difficulty', 'xp',
                'explanation_video__id', 'explanation_video__hls_url',
                'explanation_video__video', 'explanation_video__thumbnail',
                'explanation_video__duration'
            )
            .afirst(),

        UserResponse.objects
            .filter(user_id=request_user.id, question_id=question_id, session=None)
            .select_related('choice')
            .only('id', 'choice__id', 'choice__is_correct', 'choice__explanation')
            .order_by('-created_at')
            .afirst(),
    )

    if not question:
        raise HTTPException(status_code=404, detail="Savol topilmadi!")

    user_answer = None
    if last_resp and last_resp.choice:
        user_answer = {
            "c_id": last_resp.choice_id,
            "ok":   last_resp.choice.is_correct,
            "exp":  last_resp.choice.explanation,
        }

    exp_video = None
    if user_answer and question.explanation_video:
        v = question.explanation_video
        exp_video = {
            "src":   v.hls_url or (v.video.url if v.video else None),
            "thumb": v.thumbnail.url if v.thumbnail else None,
            "dur":   v.duration,
        }

    return {
        "id":       question.id,
        "text":     question.text,
        "diff":     question.difficulty,
        "xp":       question.xp,
        "choices":  [{"id": c.id, "text": c.text} for c in question.choices.all()],
        "user_ans": user_answer,
        "exp_video": exp_video,
    }


# ─── 5. QUIZ SUBMIT ───────────────────────────────────────────────────────────
@api.post("/{slug}/quizzes/{question_id}/submit/")
async def submit_quiz_api(
    request: Request,
    slug: str,
    question_id: int,
    request_user: BaseUser | None = Depends(get_current_user_option)
):
    if not request_user:
        raise HTTPException(status_code=401, detail="Tizimga kirish talab qilinadi!")

    body      = await request.json()
    choice_id = body.get("choice_id")

    if not choice_id:
        raise HTTPException(status_code=400, detail="'choice_id' majburiy!")

    # question + choice + already — 3 ta parallel
    question, choice, already = await asyncio.gather(
        Question.objects
            .filter(id=question_id, lesson__slug=slug)
            .only('id')
            .afirst(),

        Choice.objects
            .filter(id=choice_id, question_id=question_id)
            .only('id', 'is_correct', 'explanation')
            .afirst(),

        UserResponse.objects
            .filter(user_id=request_user.id, question_id=question_id, session=None)
            .aexists(),
    )

    if not question:
        raise HTTPException(status_code=404, detail="Savol topilmadi!")
    if not choice:
        raise HTTPException(status_code=400, detail="Variant topilmadi!")
    if already:
        raise HTTPException(status_code=204, detail="")

    # Signal: XP + LessonStatus
    await UserResponse.objects.acreate(
        user_id=request_user.id,
        question_id=question_id,
        choice_id=choice_id,
        session=None,
    )

    return {"ok": choice.is_correct, "exp": choice.explanation}



# @api.get("/{slug}/problems/{problem_slug}")
# async def get_single_problem_api(
#     request: Request,
#     slug: str,
#     problem_slug: str,
#     request_user: BaseUser | None = Depends(get_current_user_option)
# ):
#     # 1. Avtorizatsiya tekshiruvi (agar masala sahifasiga faqat login qilganlar kira olsa)
#     if not request_user:
#         raise HTTPException(status_code=401, detail="Tizimga kirish talab qilinadi!")

#     # 2. Faqat masalaning o'zi va unga bog'liq tarkibiy qismlarni yuklaymiz (Parallel so'rov shartmas)
#     problem = await (
#         Problem.objects
#         .filter(slug=problem_slug, lesson__slug=slug, is_active=True)
#         .select_related('category') # solution_video olib tashlandi
#         .prefetch_related(
#             Prefetch('tags',        queryset=Tags.objects.only('id', 'name')),
#             Prefetch('language',    queryset=Language.objects.only('id', 'name', 'version')),
#             Prefetch('hints',       queryset=Hint.objects.only('id', 'text')),
#             Prefetch('challenges',  queryset=Challenge.objects.only('id', 'text')),
#             Prefetch('functions',   queryset=Function.objects.only('id', 'function', 'language_id')),
#         )
#         .only(
#             'id', 'lesson_id', 'category_id', 'title', 'slug', 'description',
#             'difficulty', 'time_limit', 'memory_limit', 'xp', 'is_active'
#         )
#         .afirst()
#     )

#     # 3. Agar masala topilmasa 404 qaytaramiz
#     if not problem:
#         raise HTTPException(status_code=404, detail="Masala topilmadi!")

#     # 4. JSON formatida eng toza va ixcham javob qaytarish
#     return {
#         "id":           problem.id,
#         "title":        problem.title,
#         "slug":         problem.slug,
#         "desc":         problem.description,
#         "diff":         problem.difficulty,
#         "xp":           problem.xp,
#         "tl":           problem.time_limit,
#         "ml":           problem.memory_limit,
#         "is_active":    problem.is_active,
#         "category_id":  problem.category_id,

#         "tags":       [{"id": t.id, "name": t.name} for t in problem.tags.all()],
#         "langs":      [{"id": l.id, "name": l.name, "ver": l.version} for l in problem.language.all()],
#         "hints":      [{"id": h.id, "text": h.text} for h in problem.hints.all()],
#         "challenges": [{"id": c.id, "text": c.text} for c in problem.challenges.all()],

#         "functions": {
#             fn.language_id: {"id": fn.id, "code": fn.function}
#             for fn in problem.functions.all()
#         },
#     }

# ─── 7. PROBLEM SUBMIT (SSE) ──────────────────────────────────────────────────
@api.post("/{slug}/problems/{problem_slug}/submit/", response_class=EventSourceResponse)
async def submit_problem_api(
    request: Request,
    slug: str,
    problem_slug: str,
    request_user: BaseUser | None = Depends(get_current_user_option)
) -> AsyncIterable[ServerSentEvent]:
    if not request_user:
        raise HTTPException(status_code=401, detail="Tizimga kirish talab qilinadi!")

    body        = await request.json()
    code        = body.get("code", "").strip()
    language_id = body.get("lang_id")

    if not code or not language_id:
        raise HTTPException(status_code=400, detail="'code' va 'lang_id' majburiy!")

    problem, language, exec_case = await asyncio.gather(
        Problem.objects
            .filter(slug=problem_slug, lesson__slug=slug, is_active=True)
            .only('id', 'time_limit', 'memory_limit')
            .afirst(),

        Language.objects
            .filter(id=language_id)
            .only('id', 'name', 'version')
            .afirst(),

        ExecutionTestCase.objects
            .filter(problem__slug=problem_slug, language_id=language_id)
            .only('top_code', 'bottom_code')
            .afirst(),
    )

    if not problem:
        raise HTTPException(status_code=404, detail="Masala topilmadi!")
    if not language:
        raise HTTPException(status_code=400, detail="Til topilmadi!")

    raw_tests = [
        tc async for tc in
        TestCase.objects.filter(problem_id=problem.id).only('input_txt', 'output_txt')
    ]

    if not raw_tests:
        raise HTTPException(status_code=500, detail="Test case'lar topilmadi!")

    full_code = "\n".join(filter(None, [
        exec_case.top_code    if exec_case else None,
        code,
        exec_case.bottom_code if exec_case else None,
    ]))

    total   = len(raw_tests)
    passed  = 0
    results = []

    async def generate() -> AsyncIterable[ServerSentEvent]:
        nonlocal passed

        yield ServerSentEvent(event="start", data={"total": total})

        async with httpx.AsyncClient(timeout=15) as client:
            responses = await asyncio.gather(*[
                client.post(
                    "https://emkc.org/api/v2/piston/execute",
                    json={
                        "language": language.name,
                        "version":  language.version,
                        "files":    [{"content": full_code}],
                        "stdin":    tc.input_txt,
                    }
                )
                for tc in raw_tests
            ], return_exceptions=True)

        for idx, (tc, resp) in enumerate(zip(raw_tests, responses), start=1):
            if isinstance(resp, Exception):
                result = {"idx": idx, "ok": False, "stderr": "TLE"}
            else:
                run    = resp.json().get("run", {})
                stdout = run.get("stdout", "").strip()
                stderr = run.get("stderr", "").strip()
                ok     = stdout == tc.output_txt.strip()
                if ok:
                    passed += 1
                result = {
                    "idx":    idx,
                    "ok":     ok,
                    "stdout": stdout[:200],
                    "stderr": stderr[:200] if stderr else None,
                }

            results.append(result)
            yield ServerSentEvent(event="result", data=result)

        is_ac = passed == total

        try:
            Submission = apps.get_model('submissions', 'Submission')
        except (LookupError, ValueError):
            Submission = apps.get_model('problems', 'Submission')

        await Submission.objects.acreate(
            user=request_user,
            problem_id=problem.id,
            language_id=language_id,
            code=code,
            status=is_ac,
            verdict="AC" if is_ac else "WA",
            passed_test_count=passed,
            total_test_count=total,
            test_results=results,
        )

        yield ServerSentEvent(event="done", data={"ac": is_ac, "passed": passed, "total": total})

    return EventSourceResponse(generate())