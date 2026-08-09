import asyncio
import base64
import msgspec
import uuid

from django_bolt import Depends, Router, Request
from baseuser.authenticate import get_current_user, get_current_user_option
from baseuser.models import BaseUser

from .tasks import submit_code_task
from .piston_client import piston

from problems.models import Language, Problem, ExecutionTestCase, TestCase

api = Router(tags=["Run!"])


class RunCode(msgspec.Struct):
    """
    POST /run tanasi.

    DIQQAT: `testcases` maydoni ATAYLAB YO'Q — frontend hech qanday test
    ma'lumotini yubormaydi. Namuna testlar (`is_sample=True`) BAZADAN
    o'qiladi, xuddi yashirin testlar submit'da bazadan olinganidek.

    `stdin` — FAQAT konsol rejimida (masalada umuman test case yo'q holatda)
    ishlatiladi: frontend to'plagan TO'LIQ input matni shu yerga qo'yiladi.
    """
    problem_id: int
    language_id: int
    code: str
    stdin: str | None = None

class SubmissionCode(msgspec.Struct):
    """
    POST /submit tanasi.

    DIQQAT: bu yerda `testcases` YO'Q — ataylab! Yashirin testlarni
    frontend UMUMAN bilmaydi va yubormaydi ham. Backend ularni
    `problem_id` orqali BAZADAN o'zi oladi (tasks.py'dagi
    `submit_code_task` ichida).
    """
    problem_id: int
    language_id: int
    code: str


def _judge_result(run_info: dict, expected_output: str) -> str:
    """Namuna test uchun to'liq solishtiruv: AC/WA/TLE/MLE/RE."""
    stderr = run_info.get("stderr", "")
    stdout = run_info.get("stdout", "").strip()
    exit_code = run_info.get("code", 0)
    signal = run_info.get("signal")
    msg = str(run_info.get("message", "")).lower()

    if signal == "SIGKILL" or "timeout" in msg:
        return "TLE"
    if "memory limit" in msg:
        return "MLE"
    if exit_code != 0 or stderr:
        return "RE"
    return "AC" if stdout == expected_output.strip() else "WA"


def _judge_console_result(run_info: dict) -> str:
    """Konsol rejimi uchun: WA yo'q, chunki solishtiradigan kutilgan
    natija yo'q — faqat ijro xatolari tekshiriladi."""
    stderr = run_info.get("stderr", "")
    exit_code = run_info.get("code", 0)
    signal = run_info.get("signal")
    msg = str(run_info.get("message", "")).lower()

    if signal == "SIGKILL" or "timeout" in msg:
        return "TLE"
    if "memory limit" in msg:
        return "MLE"
    if exit_code != 0 or stderr:
        return "RE"
    return "AC"


def _needs_more_input(run_info: dict) -> bool:
    """
    Dastur STDIN tugagani sababli to'xtadimi (EOF) — demak frontend yana
    bitta qator so'rashi kerak. Bir nechta keng tarqalgan til uchun EOF
    belgilarini tekshiradi (Python, Java, Go va h.k.).

    CHEKLOV: 100% aniq emas — ba'zi tillar EOF holatida xato bermasdan
    jim to'xtashi mumkin, bunday holat oddiy tugash deb hisoblanadi.
    """
    if run_info.get("signal") or run_info.get("code", 0) == 0:
        return False

    stderr_lower = (run_info.get("stderr") or "").lower()
    eof_markers = (
        "eof when reading a line",
        "eoferror",
        "end of file",
        "no line found",
        "nosuchelementexception",
        "unexpected eof",
        "eof",
    )
    return any(marker in stderr_lower for marker in eof_markers)


async def _run_single_sample(language, piston_time_limit, piston_memory_limit, text_full_code, tc):
    """Bitta namuna testni ishga tushiradi va formatlangan natija qaytaradi.
    `asyncio.gather` orqali barcha testlar bilan PARALLEL chaqiriladi."""
    try:
        piston_res = await piston.async_execute_code(
            language=language.name,
            version=language.version,
            code=text_full_code,
            stdin=tc.input_txt,
            run_timeout=piston_time_limit,
            run_memory_limit=piston_memory_limit,
            encoding="utf8",
        )
    except Exception as api_err:
        return {
            "index": tc.order or tc.id,
            "input": tc.input_txt,
            "expected_output": tc.output_txt,
            "output": "",
            "status": "Server Error",
            "memory": None,
            "cpu_time": None,
            "wall_time": None,
            "message": str(api_err),
        }

    run_info = piston_res.get("run", {})
    verdict = _judge_result(run_info, tc.output_txt)

    return {
        "index": tc.order or tc.id,
        "input": tc.input_txt,
        "expected_output": tc.output_txt,
        "output": run_info.get("stdout", ""),
        "status": verdict,
        "memory": run_info.get("memory"),
        "cpu_time": run_info.get("cpu_time"),
        "wall_time": run_info.get("wall_time"),
        "message": run_info.get("stderr", ""),
    }


@api.post("/run")
async def run(request: Request, body: RunCode, request_user: BaseUser = Depends(get_current_user_option)):
    """
    Kodni sinab ko'rish:
      - Agar masalada test case umuman bo'lmasa -> KONSOL REJIMI
        (frontend to'plagan `stdin` bilan ishga tushiriladi, EOF chiqsa
        "input_required" qaytariladi).
      - Aks holda -> faqat `is_sample=True` testlar BAZADAN olinib,
        PARALLEL ishga tushiriladi.
    """
    print("BODY:", body)
    print(body.code, "\n", body.language_id, "\n", body.problem_id)
    # 1) Til va masalani olamiz
    try:
        language = await Language.objects.aget(id=body.language_id)
        problem = await Problem.objects.aget(id=body.problem_id)
    except (Language.DoesNotExist, Problem.DoesNotExist) as e:
        return {"status": "error", "message": f"Ma'lumot topilmadi: {str(e)}"}

    # 2) Wrapper kodlarni olamiz (bo'lmasa bo'sh — xavfsiz rejim)
    try:
        execode_testcase = await ExecutionTestCase.objects.aget(language=language, problem_id=body.problem_id)
        top_code = execode_testcase.top_code or ""
        bottom_code = execode_testcase.bottom_code or ""
    except ExecutionTestCase.DoesNotExist:
        top_code = ""
        bottom_code = ""

    # 3) base64 dekod -> wrap (qayta base64 YO'Q, Piston toza matn kutadi)
    try:
        decoded_user_code = base64.b64decode(body.code).decode("utf-8")
    except Exception:
        return {"status": "error", "message": "Foydalanuvchi kodi noto'g'ri Base64 formatida!"}
    text_full_code = f"{top_code}\n{decoded_user_code}\n{bottom_code}"

    piston_time_limit = int(problem.time_limit)
    piston_memory_limit = int(problem.memory_limit)

    # 4) Masalada UMUMAN test case bormi (sample + yashirin)?
    total_test_count = await TestCase.objects.filter(problem_id=body.problem_id).acount()

    # ============================================================
    # KONSOL REJIMI — test case umuman yo'q
    # ============================================================
    if total_test_count == 0:
        accumulated_stdin = body.stdin or ""

        try:
            piston_res = await piston.async_execute_code(
                language=language.name, version=language.version,
                code=text_full_code, stdin=accumulated_stdin,
                run_timeout=piston_time_limit, run_memory_limit=piston_memory_limit,
                encoding="utf8",
            )
        except Exception as api_err:
            return {"status": "error", "message": f"Piston API xatosi: {api_err}"}

        run_info = piston_res.get("run", {})

        if _needs_more_input(run_info):
            return {
                "status": "input_required",
                "partial_output": run_info.get("stdout", ""),
                "stdin_so_far": accumulated_stdin,
            }

        verdict = _judge_console_result(run_info)
        return {
            "status": "done",
            "problem_id": body.problem_id,
            "language": language.name,
            "results": [{
                "index": 1,
                "lang": language.name,
                "ver": language.version,
                "input": accumulated_stdin,
                "expected_output": "",
                "output": run_info.get("stdout", ""),
                "status": verdict,
                "memory": run_info.get("memory"),
                "cpu_time": run_info.get("cpu_time"),
                "wall_time": run_info.get("wall_time"),
                "message": run_info.get("stderr", ""),
            }],
        }

    # ============================================================
    # ODDIY REJIM — faqat NAMUNA (is_sample=True) testlar, BAZADAN,
    # PARALLEL ishga tushiriladi
    # ============================================================
    sample_tests = [
        tc async for tc in TestCase.objects.filter(
            problem_id=body.problem_id, is_sample=True
        ).order_by("order")
    ]

    if not sample_tests:
        # Masalada yashirin testlar bor, lekin sample yo'q — /run uchun
        # ko'rsatadigan hech narsa yo'q, foydalanuvchiga aniq xabar beramiz.
        return {
            "status": "error",
            "message": "Bu masala uchun namuna (sample) testlar mavjud emas. To'g'ridan-to'g'ri 'Submit' qiling.",
        }

    results = await asyncio.gather(*[
        _run_single_sample(language, piston_time_limit, piston_memory_limit, text_full_code, tc)
        for tc in sample_tests
    ])

    return {
        "status": "done",
        "problem_id": body.problem_id,
        "language": language.name,
        "results": results,
    }


@api.post("/submit")
async def submit(request: Request, body: SubmissionCode, request_user: BaseUser = Depends(get_current_user)):
    print("BODY:", body)
    print(body.code, "\n", body.language_id, "\n", body.problem_id)
    task_id = uuid.uuid4()
    result = submit_code_task.apply_async(
        kwargs=dict(
            user_id=request_user.id,
            problem_id=body.problem_id,
            language_id=body.language_id,
            code=body.code,
        ),
    )
    return {"queued": True, "task_id": result.id}