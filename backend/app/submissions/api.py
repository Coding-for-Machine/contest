import uuid
from django_bolt import Depends, Router, Request
import msgspec

from baseuser.authenticate import get_current_user
from baseuser.models import BaseUser
from .tasks import run_code_task, submit_code_task

api = Router(tags=["Run!"])


class TestCaseStruct(msgspec.Struct):
    input: str
    output: str


class RunCode(msgspec.Struct):
    problem_id: int
    language_id: int
    code: str
    testcases: list[TestCaseStruct] | None = None


class SubmissionCode(msgspec.Struct):
    problem_id: int
    language_id: int
    code: str


@api.post("/run")
async def run(request: Request, body: RunCode, request_user: BaseUser = Depends(get_current_user)):
    task_id = str(uuid.uuid4())

    run_code_task.apply_async(
        task_id=task_id,
        kwargs=dict(
            task_id=task_id,
            user_id=request_user.id,
            mode="run",
            language_id=body.language_id,
            code=body.code,
            testcases=[{"input": tc.input, "output": tc.output} for tc in (body.testcases or [])],
        ),
    )

    return {"queued": True, "task_id": task_id}


@api.post("/submit")
async def submit(request: Request, body: SubmissionCode, request_user: BaseUser = Depends(get_current_user)):
    task_id = str(uuid.uuid4())

    submit_code_task.apply_async(
        task_id=task_id,
        kwargs=dict(
            task_id=task_id,
            user_id=request_user.id,
            mode="submit",
            problem_id=body.problem_id,
            language_id=body.language_id,
            code=body.code,
        ),
    )

    return {"queued": True, "task_id": task_id}