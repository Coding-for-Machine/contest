# piston_client.py
"""
Piston API v2 bilan ishlovchi asinxron klient.

Piston (https://piston.readthedocs.io/en/latest/api-v2/) — kodni xavfsiz
"sandbox" muhitida bajarib beruvchi ochiq API. Biz unga POST /execute orqali
til, versiya, kod va stdin yuboramiz, u esa kompilyatsiya (agar kerak bo'lsa)
va ijro natijasini (stdout, stderr, exit code, signal) qaytaradi.

MUHIM: bu klient faqat Piston bilan "gaplashadi" — natijani AC/WA/CE kabi
verdiktga aylantirish ishi bu yerda emas, `services.py`dagi
`PistonStreamService`da bajariladi. Shunday qilib javobgarliklar aniq
ajratilgan (single responsibility):
    piston_client.py -> faqat HTTP so'rov va JSON->struct parsing
    services.py       -> Piston javobini o'zbekcha verdikt-stringga aylantirish
    tasks.py          -> Celery ichida servicening chaqirilishi va Redisga yozish
"""

import httpx
import msgspec
from typing import List, Optional
from decouple import config


class StageResult(msgspec.Struct):
    """
    Kompilyatsiya YOKI Ijro (Run) bosqichining natijasi.

    Piston ikkala bosqich uchun ham bir xil formatda javob beradi, shuning
    uchun bitta struct ikkalasiga ham xizmat qiladi (`compile` va `run`
    maydonlari xuddi shu StageResult tipida).
    """
    stdout: str                    # Dastur/kompilyator odatdagi chiqishi
    stderr: str                    # Xatolik oqimi (compile error, exception va h.k.)
    output: str                    # stdout + stderr birlashtirilgan (Piston shu nomda beradi)
    code: Optional[int] = None     # Process exit code — 0 bo'lsa muvaffaqiyatli tugagan
    signal: Optional[str] = None   # Agar dastur signal bilan o'ldirilgan bo'lsa (SIGKILL — odatda timeout,
                                    # SIGSEGV — segmentation fault, SIGXCPU — CPU vaqti tugashi va h.k.)


class PistonExecuteResponse(msgspec.Struct):
    """POST /api/v2/execute so'rovidan qaytadigan to'liq javob."""
    language: str
    version: str
    run: StageResult
    compile: Optional[StageResult] = None
    # ^ Faqat kompilyatsiya talab qiladigan tillarda keladi (C++, Java...).
    #   Python/JS kabi interpretatsiya qilinadigan tillarda bu maydon None bo'ladi.


class PistonClient:
    """
    Piston API v2 bilan ishlovchi asinxron, qayta ishlatiladigan (reusable)
    HTTP klient.

    Nega alohida klass (singleton)?
    - httpx.AsyncClient o'zining connection pool'iga ega — har safar yangi
      klient yaratish TCP handshake'larni behuda ko'paytiradi.
    - Butun ilova davomida BITTA client obyekti orqali so'rov yuborilsa,
      ulanishlar qayta ishlatiladi (keep-alive) — bu tezlik va resurs
      tejash uchun muhim, ayniqsa Celery worker ko'p vazifani ketma-ket
      bajarganda.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        # timeout: umumiy so'rov 15s, lekin javobni o'qish (read) uchun 30s —
        # chunki kod ijrosi (run_timeout) o'zi Piston tarafida cheklanadi,
        # HTTP darajasida esa shunchaki "javob juda kech kelmasin" degan
        # xavfsizlik chegarasi.
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(15.0, read=30.0))

    async def execute_code(
        self,
        language: str,
        version: str,
        code_content: str,
        file_name: Optional[str] = None,
        stdin: str = "",
        args: Optional[List[str]] = None,
        run_timeout: int = 2000,          # millisekund (2 soniya) — dastur shu vaqt ichida tugashi kerak
        compile_timeout: int = 10000,     # millisekund (10 soniya) — kompilyatsiya uchun
        run_memory_limit: int = -1,       # bayt (-1 = cheklovsiz)
        compile_memory_limit: int = -1
    ) -> PistonExecuteResponse:
        """
        Piston API orqali kodni cheklovlar ostida bajaradi va natijani
        struct (PistonExecuteResponse) sifatida qaytaradi.

        DIQQAT: bu funksiya faqat quyidagi parametrlarni qabul qiladi —
        `run_cpu_time` yoki `compile_cpu_time` kabi qo'shimcha nom Piston
        API'sida ham, bu funksiya signature'ida ham YO'Q. Agar chaqirganda
        shu nomlarni yuborsangiz — Python TypeError beradi ("unexpected
        keyword argument"), chunki ular hech qayerda qabul qilinmagan.
        (services.py'dagi eski versiyada aynan shu xato bor edi — pastda
        tuzatilgan holatini ko'rasiz.)
        """
        url = f"{self.base_url}/execute"

        file_obj = {"content": code_content}
        if file_name:
            file_obj["name"] = file_name

        payload = {
            "language": language,
            "version": version,
            "files": [file_obj],
            "stdin": stdin,
            "args": args or [],
            "run_timeout": run_timeout,
            "compile_timeout": compile_timeout,
            "run_memory_limit": run_memory_limit,
            "compile_memory_limit": compile_memory_limit,
        }

        response = await self.client.post(url, json=payload)

        if response.is_error:
            # Piston 4xx/5xx qaytarsa (masalan noto'g'ri til/versiya nomi,
            # yoki Piston serverining o'zida muammo) — ichki xabarni chiqaramiz,
            # aks holda faqat "500 Internal Server Error" kabi foydasiz xatolik ko'rinardi.
            try:
                err_msg = response.json().get("message", response.text)
            except Exception:
                err_msg = response.text
            raise Exception(f"Piston API Error: {response.status_code} - {err_msg}")

        # msgspec.json.decode — standart json.loads()dan bir necha barobar tez,
        # va bir vaqtning o'zida JSON'ni to'g'ridan-to'g'ri struct'ga aylantiradi
        # (validatsiya + parsing bitta amalda).
        return msgspec.json.decode(response.content, type=PistonExecuteResponse)

    async def close(self):
        """
        Ulanishlar pool'ini yopadi. Odatda ilova to'xtaganda (masalan Django
        AppConfig.ready()'da ro'yxatdan o'tkazilgan shutdown signalida)
        chaqiriladi — Celery worker uzluksiz ishlaganda bu chaqirilmasligi
        ham mumkin, chunki client butun worker umri davomida qayta ishlatiladi.
        """
        await self.client.close()


# ============================================================
# SINGLETON — butun tizim bo'yicha BITTA PistonClient obyekti.
#
# Nega global o'zgaruvchi sifatida (modul darajasida)?
# Bu fayl birinchi marta import qilinganda BIR MARTA yaratiladi va keyin
# har qanday joydan `from .piston_client import piston_client` orqali
# xuddi shu obyekt qayta ishlatiladi — connection pool har safar qayta
# yaratilmaydi.
# ============================================================
base_url = config("PISTON_URL", default="http://localhost:2000/api/v2")
piston_client = PistonClient(base_url=base_url)