# router.py
"""
HTTP endpointlar — /run va /submit.

Bu ikkalasi ham BIR XIL naqshga amal qiladi:
  1) task_id generatsiya qilinadi (uuid4)
  2) Tegishli Celery vazifasi shu task_id bilan navbatga qo'yiladi
     (натижа кутилмайди — .apply_async() darhol qaytadi)
  3) {"queued": True, "task_id": task_id} javobi DARHOL (millisekundlarda)
     qaytariladi

Natijaning o'zi bu yerda YO'Q — u alohida, asinxron kanal (Celery worker
-> Redis PUBLISH -> Django Bolt SSE endpoint -> brauzerdagi global
RCEvents) orqali keladi. Bu fayl faqat "ishni boshlash" nuqtasi.
"""

import uuid
import msgspec

from django_bolt import Depends, Router, Request
from baseuser.authenticate import get_current_user
from baseuser.models import BaseUser

from .tasks import run_code_task, submit_code_task

api = Router(tags=["Run!"])


# ============================================================
# SO'ROV STRUKTURALARI (msgspec.Struct — avtomatik validatsiya qiladi:
# noto'g'ri tipdagi maydon kelsa, django_bolt o'zi 422 xatolik qaytaradi,
# view funksiyasi ichida qo'lda tekshirish shart emas)
# ============================================================

class TestCaseStruct(msgspec.Struct):
    """Frontend RUN so'rovida yuboradigan bitta namunaviy testcase."""
    input: str
    output: str


class RunCode(msgspec.Struct):
    """
    POST /run tanasi.

    `testcases` — FAQAT namunaviy (misol) testlar, ya'ni masala sahifasida
    ko'rinib turgan Example 1/2/3. Bular frontend orqali keladi, chunki
    ular ochiq ma'lumot — hech qanday sirni oshkor qilmaydi.
    """
    problem_id: int
    language_id: int
    code: str
    testcases: list[TestCaseStruct] | None = None


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


# ============================================================
# ENDPOINTLAR
# ============================================================

@api.post("/run")
async def run(request: Request, body: RunCode, request_user: BaseUser = Depends(get_current_user)):
    """
    Kodni NAMUNAVIY testlar ustida sinab ko'rish (natija bazaga yozilmaydi).
    """
    task_id = str(uuid.uuid4())

    # 🔑 task_id IKKI JOYDA ishlatiladi:
    #   1) `apply_async(task_id=...)` — Celery buni O'ZINING vazifa ID'si
    #      sifatida ham qabul qiladi, ya'ni kerak bo'lsa keyinchalik
    #      `AsyncResult(task_id)` orqali holatini so'rash mumkin bo'ladi
    #      (SSE biror sababga ko'ra ishlamay qolsa, zaxira variant sifatida).
    #   2) `kwargs`dagi `task_id` — Celery worker Redisga PUBLISH qilganda
    #      xuddi shu qiymatni xabar ichiga qo'shadi (`{"task_id": ...}`).
    #      Frontend `RCEvents.onTask(taskId, ...)` orqali aynan shu
    #      qiymatga obuna bo'ladi — ikkalasi (bu yerdagi va Redis xabaridagi)
    #      BIR XIL bo'lishi SHART, aks holda natija hech qachon frontendga
    #      "yetib bormaydi" (chunki task_id mos kelmasa, dispatch ishlamaydi).
    run_code_task.apply_async(
        task_id=task_id,
        kwargs=dict(
            task_id=task_id,
            user_id=request_user.id,   # qaysi "sse:user:{id}" kanaliga PUBLISH qilishni bilish uchun
            mode="run",
            language_id=body.language_id,
            code=body.code,
            testcases=[
                {"input": tc.input, "output": tc.output}
                for tc in (body.testcases or [])
            ],
        ),
    )

    # Darhol qaytadi — Celery worker hali ishni boshlagani ham yo'q.
    # Frontend shu javobni olgach, `RCEvents.onTask(task_id, ...)` orqali
    # natijalarni "tinglashni" boshlaydi.
    return {"queued": True, "task_id": task_id}


@api.post("/submit")
async def submit(request: Request, body: SubmissionCode, request_user: BaseUser = Depends(get_current_user)):
    """
    Kodni RASMIY yuborish — yashirin testlar ustida tekshiriladi,
    natija Submission jadvaliga yoziladi.

    ESLATMA: avvalgi versiyada bu funksiyada `request_user` UMUMAN yo'q edi
    — bu jiddiy xato, chunki Celery vazifasiga `user_id` bermasak, u qaysi
    Redis kanaliga natijani PUBLISH qilishni bilmaydi (demak natija
    hech qachon brauzerga yetib bormaydi). Pastda tuzatilgan.
    """
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
            # testcases YO'Q — submit_code_task ularni bazadan o'zi oladi
        ),
    )

    return {"queued": True, "task_id": task_id}