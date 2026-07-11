# services.py
"""
PistonStreamService — Piston'ning xom (raw) javobini bitta, izchil,
o'zbekcha qisqartmali VERDIKT-STRINGGA aylantiruvchi xizmat qatlami.

Nega alohida qatlam kerak?
Piston o'zi faqat "dastur nima chiqardi" deydi (stdout/stderr/code/signal).
Lekin bizga kerak bo'lgan narsa — "bu yechim TO'G'RImi, va agar noto'g'ri
bo'lsa NIMA UCHUN" degan savolga aniq javob. Shu tarjima ishi shu yerda
bajariladi.

Chiqadigan format har doim BITTA QOLIPDA:

    "<BOSQICH>: [<KOD>]" + ixtiyoriy " (<qisqa izoh>)"
                         + ixtiyoriy "\n[<Yorliq>]:\n<tafsilot matni>"

Misollar:
    "IJRO: [AC]\n[Natija]:\n0 1"
    "KOMPILYATSIYA: [CE]\n[Xatolik matni]:\n<compiler error>"
    "IJRO: [TO] (Vaqt tugadi)"
    "IJRO: [SG] (Tizim signali: SIGSEGV)"
    "IJRO: [RE]\n[Xatolik matni]:\n<traceback>"
    "IJRO: [OL] (Uzunlik oshib ketdi)"
    "TIZIM: [XX]\n[Xatolik matni]:\n<internal exception>"

Bu format ataylab STRING qilib tanlangan (JSON emas), chunki:
1) Redis pub/sub orqali yuborishda eng sodda, eng kam joy oladigan format;
2) Frontenddagi `parseVerdictString()` (main.js) aynan shu qolipni regex
   bilan ochadi — backend va frontend o'rtasidagi "shartnoma" (contract)
   shu yagona string formati.

Qisqartmalar lug'ati (frontenddagi VERDICT_LABELS bilan bir xil bo'lishi SHART):
    AC — Accepted            (qabul qilindi, hammasi to'g'ri)
    CE — Compile Error       (kompilyatsiya xatosi)
    RE — Runtime Error       (ishga tushirish vaqtidagi xato)
    TO — Time Out            (vaqt tugadi)
    SG — Signal              (dastur signal bilan yiqildi, masalan segfault)
    OL — Output Limit        (chiqish juda uzun)
    EL — Error Limit         (xatolik matni juda uzun)
    XX — System Error        (bizning tizimimizdagi ichki xato, Piston bilan aloqa uzilishi va h.k.)
"""

from .piston_client import piston_client


class PistonStreamService:
    """
    Kodni Piston API orqali bajarib, natijani yuqoridagi qolipdagi
    STRING ko'rinishida qaytaruvchi xizmat.
    """

    # Har bir testcase uchun stdout/stderr necha belgidan oshsa cheklov
    # ishga tushishini belgilaydi. Bu Piston darajasidagi memory/timeout
    # cheklovidan FARQLI — bu shunchaki "javobni saqlash/ko'rsatish"
    # darajasidagi himoya (masalan cheksiz sikl `print` qilib, DB yoki
    # Redis xabarini shishirib yubormasligi uchun).
    MAX_OUTPUT_LENGTH = 10_000

    @classmethod
    async def process_and_stream_code(
        cls,
        language: str,
        version: str,
        source_code: str,
        stdin: str = "",
    ) -> str:
        """
        Bitta testcase uchun kodni bajaradi va natijani verdikt-string
        ko'rinishida qaytaradi.

        Bu funksiya Celery task ichida HAR BIR TESTCASE UCHUN alohida
        chaqiriladi (tasks.py'dagi `run_code_task`/`submit_code_task`ga
        qarang) — ya'ni 5 ta testcase bo'lsa, bu funksiya 5 marta
        chaqiriladi, har safar natija darhol Redisga PUBLISH qilinadi.
        """
        try:
            res = await piston_client.execute_code(
                language=language,
                version=version,
                code_content=source_code,
                stdin=stdin,
                run_timeout=3000,              # 3 soniya — ijro uchun
                compile_timeout=10000,          # 10 soniya — kompilyatsiya uchun
                run_memory_limit=128 * 1024 * 1024,  # 128 MB
                compile_memory_limit=-1,        # kompilyatsiya uchun xotira cheklanmagan
                # ❌ ESLATMA: `run_cpu_time` va `compile_cpu_time` OLIB TASHLANDI.
                # Bular avvalgi versiyada bor edi, lekin PistonClient.execute_code()
                # signature'ida bunday parametr yo'q — shuning uchun bu chaqiruv
                # har safar `TypeError: execute_code() got an unexpected keyword
                # argument 'run_cpu_time'` bilan yiqilar edi. Agar CPU vaqtini
                # ham cheklash kerak bo'lsa, buni PistonClient.execute_code()
                # ichiga (va Piston so'rov payload'iga) YANGI parametr sifatida
                # to'g'ri qo'shish kerak, bu yerda "bepul" qo'shib bo'lmaydi.
            )
        except Exception as e:
            # XX — Piston serveriga umuman ulanib bo'lmadi, yoki HTTP xatolik,
            # yoki msgspec parsing xatosi — sabab qanday bo'lishidan qat'iy
            # nazar, bu "bizning tizimimiz darajasidagi" muammo, foydalanuvchi
            # kodi bilan bog'liq emas.
            return f"TIZIM: [XX]\n[Xatolik matni]:\n{str(e)}"

        # ── 1. CE — Kompilyatsiya xatoligi ──────────────────────────────
        # Faqat compile bosqichi mavjud bo'lgan tillarda (C++, Java...) va
        # uning exit code'i 0 dan farqli bo'lsa ishga tushadi.
        if res.compile and res.compile.code != 0:
            err_msg = res.compile.stderr.strip() or res.compile.output.strip()
            return f"KOMPILYATSIYA: [CE]\n[Xatolik matni]:\n{err_msg}"

        # ── 2. TO — Vaqt tugashi ─────────────────────────────────────────
        # SIGKILL/SIGXCPU odatda Piston'ning o'zi run_timeout'ga yetganda
        # dasturni majburan o'ldirishi natijasida keladi.
        if res.run.signal in ("SIGKILL", "SIGXCPU"):
            return "IJRO: [TO] (Vaqt tugadi)"

        # ── 3. SG — Boshqa har qanday signal bilan yiqilish (crash) ──────
        # Masalan SIGSEGV (segmentation fault — noto'g'ri xotiraga murojaat),
        # SIGABRT va h.k.
        if res.run.signal:
            return f"IJRO: [SG] (Tizim signali: {res.run.signal})"

        # ── 4. RE — Runtime xato ─────────────────────────────────────────
        # Signal bilan o'lmagan, lekin baribir muvaffaqiyatsiz tugagan
        # (exit code != 0) yoki stderr'ga biror narsa yozilgan holatlar —
        # masalan Python traceback, unhandled exception.
        if res.run.code != 0 or res.run.stderr:
            err_msg = res.run.stderr.strip() or f"Exit code: {res.run.code}"
            return f"IJRO: [RE]\n[Xatolik matni]:\n{err_msg}"

        # ── 5. OL / EL — Uzunlik cheklovlari ─────────────────────────────
        # Bu ikkalasi RE'dan KEYIN tekshiriladi, chunki agar dastur baribir
        # xato bilan tugagan bo'lsa, "chiqish juda uzun" degan xabar chalg'ituvchi
        # bo'lardi — avval "nima uchun ishlamadi" (RE/CE/TO/SG), keyingina
        # "muvaffaqiyatli, lekin chiqish limitdan oshgan" tekshiriladi.
        if len(res.run.stdout) > cls.MAX_OUTPUT_LENGTH:
            return "IJRO: [OL] (Uzunlik oshib ketdi)"
        if len(res.run.stderr) > cls.MAX_OUTPUT_LENGTH:
            return "IJRO: [EL] (Uzunlik oshib ketdi)"

        # ── 6. AC — Muvaffaqiyatli yakunlanish ───────────────────────────
        # DIQQAT: bu yerda faqat "dastur toza ishladi" degan ma'noni
        # bildiradi (exit code 0, signal yo'q, xato yo'q). Bu ALI stdout'ning
        # kutilgan (`expected output`) bilan mos kelishini TEKSHIRMAYDI —
        # bu solishtiruv `tasks.py`da amalga oshiriladi (chunki faqat
        # tasks.py testcase'ning "expected output"ini biladi, bu servis
        # faqat Piston bilan ishlaydi, testcase haqida umuman xabari yo'q).
        if res.run.stdout:
            return f"IJRO: [AC]\n[Natija]:\n{res.run.stdout}"
        return "IJRO: [AC] (Muvaffaqiyatli, dastur bo'sh)"