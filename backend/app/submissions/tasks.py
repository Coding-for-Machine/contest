import base64
import logging

from celery import shared_task
from django.db import transaction

from problems.models import Language, Problem, ExecutionTestCase, TestCase
from submissions.models import Submission
from .piston_client import piston
from app.sse.events import Channel, SubmissionEvent
from app.sse.redis_client import sync_redis
from .services import handle_accepted_submission

logger = logging.getLogger(__name__)


def _publish(channel: str, event) -> None:
    try:
        payload = event.to_json()
        logger.info(
            "SSE publish: channel=%s event=%s id=%s",
            channel,
            event.event,
            event.id,
        )
        sync_redis.publish(channel, payload)
    except Exception:
        logger.exception("SSE publish xato berdi (channel=%s)", channel)


def _decode_and_wrap(raw_code_b64: str, top_code: str, bottom_code: str) -> str:
    decoded_user_code = base64.b64decode(raw_code_b64).decode("utf-8")
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
    if stdout == expected_output.strip():
        return "AC"
    return "WA"


@shared_task(bind=True)
def submit_code_task(
    self,
    user_id: int,
    problem_id: int,
    language_id: int,
    code: str,
) -> None:
    task_id = self.request.id
    channel = Channel.USER.format(user_id=user_id)

    logger.info(
        "Submission task started: task_id=%s user_id=%s problem_id=%s",
        task_id,
        user_id,
        problem_id,
    )

    try:
        language = Language.objects.get(id=language_id)
        problem = Problem.objects.get(id=problem_id)
    except (Language.DoesNotExist, Problem.DoesNotExist) as exc:
        logger.exception("Language yoki Problem topilmadi")
        _publish(channel, SubmissionEvent.error(task_id, f"Ma'lumot topilmadi: {exc}"))
        return

    _publish(channel, SubmissionEvent.queued(task_id))

    try:
        execode_testcase = ExecutionTestCase.objects.get(
            language=language,
            problem_id=problem_id,
        )
        top_code = execode_testcase.top_code or ""
        bottom_code = execode_testcase.bottom_code or ""
    except ExecutionTestCase.DoesNotExist:
        top_code = ""
        bottom_code = ""

    try:
        text_full_code = _decode_and_wrap(code, top_code, bottom_code)
    except Exception:
        logger.exception("User code Base64 decode xatosi")
        submission = Submission.objects.create(
            user_id=user_id,
            problem=problem,
            language=language,
            code=code,
            status=False,
            verdict=Submission.VerdictChoices.COMPILE_ERROR,
            passed_test_count=0,
            total_test_count=0,
            test_results=[],
        )
        _publish(
            channel,
            SubmissionEvent.result(
                task_id,
                lang=language.name,
                ver=language.version,
                output="",
                message="Kod noto'g'ri Base64 formatida",
            ),
        )
        _publish(channel, SubmissionEvent.final(submission, task_id=task_id))
        return

    piston_time_limit = int(problem.time_limit)
    piston_memory_limit = int(problem.memory_limit)

    test_cases = list(TestCase.objects.filter(problem_id=problem_id).order_by("order"))
    total = len(test_cases)
    passed = 0
    last_verdict = "AC"
    results_json = []
    max_time_ms = 0
    max_memory_kb = 0

    for index, tc in enumerate(test_cases, start=1):
        logger.info("Running testcase: task_id=%s index=%s/%s", task_id, index, total)

        try:
            piston_res = piston.sync_execute_code(
                language=language.name,
                version=language.version,
                code=text_full_code,
                stdin=tc.input_txt,
                run_timeout=piston_time_limit,
                run_memory_limit=piston_memory_limit,
                encoding="utf8",
            )
        except Exception as api_err:
            logger.exception("Piston API xatosi (problem_id=%s test_idx=%s)", problem_id, index)
            last_verdict = "RE"
            results_json.append(
                {
                    "idx": index,
                    "ok": False,
                    "verdict": "RE",
                    "input": tc.input_txt,
                    "expected": tc.output_txt,
                    "output": "",
                    "stderr": str(api_err),
                    "cpu_time": None,
                    "memory": None,
                }
            )
            _publish(
                channel,
                SubmissionEvent.testcase(
                    task_id,
                    index=index,
                    lang=language.name,
                    ver=language.version,
                    input=tc.input_txt,
                    expected_output=tc.output_txt,
                    output="",
                    status="RE",
                    memory=None,
                    cpu_time=None,
                    wall_time=None,
                    message=f"Piston API xatosi: {api_err}",
                ),
            )
            break

        run_info = piston_res.get("run", {})
        verdict = _judge_result(run_info, tc.output_txt)
        last_verdict = verdict
        if verdict == "AC":
            passed += 1

        wall_time = run_info.get("wall_time") or 0
        memory = run_info.get("memory") or 0
        cpu_time = run_info.get("cpu_time")

        max_time_ms = max(max_time_ms, wall_time)
        max_memory_kb = max(max_memory_kb, memory)

        stdout = run_info.get("stdout") or ""
        stderr = run_info.get("stderr") or ""
        message = run_info.get("message") or ""

        results_json.append(
            {
                "idx": index,
                "ok": verdict == "AC",
                "verdict": verdict,
                "input": tc.input_txt,
                "expected": tc.output_txt,
                "output": stdout,
                "stderr": stderr or None,
                "cpu_time": cpu_time,
                "memory": memory,
            }
        )

        logger.info(
            "Testcase finished: task_id=%s index=%s/%s verdict=%s",
            task_id,
            index,
            total,
            verdict,
        )

        testcase_event = SubmissionEvent.testcase(
            task_id,
            index=index,
            lang=language.name,
            ver=language.version,
            input=tc.input_txt,
            expected_output=tc.output_txt,
            output=stdout,
            status=verdict,
            memory=memory,
            cpu_time=cpu_time,
            wall_time=wall_time,
            message=message or stderr,
        )
        _publish(channel, testcase_event)

        if verdict != "AC":
            logger.info(
                "Stopping testcase execution: task_id=%s index=%s verdict=%s",
                task_id,
                index,
                verdict,
            )
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

    logger.info(
        "Submission saved: submission_id=%s task_id=%s verdict=%s passed=%s/%s",
        submission.id,
        task_id,
        submission.verdict,
        passed,
        total,
    )

    if all_passed:
        try:
            handle_accepted_submission(user_id=user_id, problem=problem)
        except Exception:
            logger.exception(
                "handle_accepted_submission xato berdi (submission_id=%s user_id=%s problem_id=%s)",
                submission.id,
                user_id,
                problem_id,
            )

    _publish(channel, SubmissionEvent.final(submission, task_id=task_id))

    logger.info(
        "Submission task finished: task_id=%s submission_id=%s verdict=%s",
        task_id,
        submission.id,
        submission.verdict,
    )