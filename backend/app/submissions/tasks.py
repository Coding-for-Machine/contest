import base64
from celery import shared_task
from django.db import transaction
from problems.models import Language, Problem, ExecutionTestCase, TestCase
from submissions.models import Submission
from .piston_client import piston
from app.sse.events import Channel, SubmissionEvent
from app.sse.redis_client import sync_redis
from .services import handle_accepted_submission


def _publish(channel: str, event) -> None:
    sync_redis.publish(channel, event.to_json())

def _decode_and_wrap(raw_code_b64: str, top_code: str, bottom_code: str) -> str:
    decoded_user_code = base64.b64decode(raw_code_b64).decode('utf-8')
    return f"{top_code}\n{decoded_user_code}\n{bottom_code}"

def _judge_result(run_info: dict, expected_output: str) -> str:
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

@shared_task(bind=True)
def submit_code_task(
    self,
    user_id: int,
    problem_id: int,
    language_id: int,
    code: str,
) -> None:
    channel = Channel.USER.format(user_id=user_id)
    task_id = self.request.id

    try:
        language = Language.objects.get(id=language_id)
        problem = Problem.objects.get(id=problem_id)
    except (Language.DoesNotExist, Problem.DoesNotExist) as exc:
        _publish(channel, SubmissionEvent.error(task_id, f"Ma'lumot topilmadi: {exc}"))
        return

    _publish(channel, SubmissionEvent.queued(task_id))

    try:
        execode_testcase = ExecutionTestCase.objects.get(language=language, problem_id=problem_id)
        top_code = execode_testcase.top_code or ""
        bottom_code = execode_testcase.bottom_code or ""
    except ExecutionTestCase.DoesNotExist:
        top_code = ""
        bottom_code = ""

    try:
       text_full_code = _decode_and_wrap(code, top_code, bottom_code)
    except Exception:
        submission = Submission.objects.create(
            user_id=user_id, problem=problem, language=language, code=code,
            status=False, verdict=Submission.VerdictChoices.COMPILE_ERROR,
            passed_test_count=0, total_test_count=0, test_results=[],
        )
        _publish(channel, SubmissionEvent.result(
            task_id, lang=language.name, ver=language.version,
            output="", message="Kod noto'g'ri Base64 formatida",
        ))
        _publish(channel, SubmissionEvent.final(submission))
        return

    piston_time_limit = int(problem.time_limit)
    piston_memory_limit = int(problem.memory_limit)

    hidden_test_cases = list(TestCase.objects.filter(problem_id=problem_id).order_by("order"))
    total = len(hidden_test_cases)
    passed = 0
    last_verdict = "AC"
    results_json = []
    max_time_ms = 0
    max_memory_kb = 0

    for index, tc in enumerate(hidden_test_cases, start=1):
        try:
            piston_res = piston.sync_execute_code(
                language=language.name,
                version=language.version,
                code=text_full_code,
                stdin=tc.input_txt,
                run_timeout=piston_time_limit,
                run_memory_limit=piston_memory_limit,
                encoding="utf8"
            )
        except Exception as api_err:
            last_verdict = "RE"
            # DEBUG: to'liq ma'lumot saqlanadi
            results_json.append({
                "idx": index,
                "ok": False,
                "verdict": "RE",
                "input": tc.input_txt,
                "expected": tc.output_txt,
                "output": "",
                "stderr": str(api_err),
                "cpu_time": None,
                "memory": None,
            })
            _publish(channel, SubmissionEvent.result(
                task_id, lang=language.name, ver=language.version,
                output="", message=f"Piston API xatosi: {api_err}",
            ))
            break

        run_info = piston_res.get("run", {})
        verdict = _judge_result(run_info, tc.output_txt)
        last_verdict = verdict
        if verdict == "AC":
            passed += 1

        wall_time = run_info.get("wall_time") or 0
        memory = run_info.get("memory") or 0
        max_time_ms = max(max_time_ms, wall_time)
        max_memory_kb = max(max_memory_kb, memory)

        # DEBUG: har bir test uchun batafsil ma'lumot saqlanadi
        results_json.append({
            "idx": index,
            "ok": verdict == "AC",
            "verdict": verdict,
            "input": tc.input_txt,
            "expected": tc.output_txt,
            "output": run_info.get("stdout", ""),
            "stderr": run_info.get("stderr") or None,
            "cpu_time": run_info.get("cpu_time"),
            "memory": memory,
        })

        _publish(channel, SubmissionEvent.testcase(
            task_id, index=index, lang=language.name, ver=language.version,
            input=tc.input_txt, expected_output=tc.output_txt,
            output=run_info.get("stdout", ""), status=verdict,
            memory=memory, cpu_time=run_info.get("cpu_time"), wall_time=wall_time,
            message=run_info.get("stderr", ""),
        ))

        if verdict != "AC":
            break

    all_passed = total > 0 and passed == total
    with transaction.atomic():
        submission = Submission.objects.create(
            user_id=user_id,
            problem=problem,
            language=language,
            code=text_full_code,
            status=all_passed,
            verdict="AC" if all_passed else last_verdict,
            passed_test_count=passed,
            total_test_count=total,
            execution_time=max_time_ms or None,
            execution_memory=max_memory_kb or None,
            test_results=results_json,
        )
        if all_passed:
            handle_accepted_submission(
                user_id=user_id,
                problem=problem,
            )
    _publish(channel, SubmissionEvent.final(submission, task_id=task_id))