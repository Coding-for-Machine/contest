# services.py
from .piston import piston_client

class PistonStreamService:
    """
    Kodni Piston API orqali bajarib, barcha holatlarni yagona o'zbekcha 
    qisqartmalar (AC, RE, CE, TO, SG, OL, EL, XX) qolipida return qiluvchi xizmat.
    """

    @classmethod
    async def process_and_stream_code(cls, language: str, version: str, source_code: str, stdin: str = "") -> str:
        try:
            res = await piston_client.execute_code(
                language=language,
                version=version,
                code_content=source_code,
                stdin=stdin,
                run_timeout=3000,
                run_cpu_time=3000,
                compile_timeout=10000,
                compile_cpu_time=10000,
                run_memory_limit=128 * 1024 * 1024,
                compile_memory_limit=-1
            )

            # 1. CE - Kompilyatsiya xatoligi
            if res.compile and res.compile.code != 0:
                err_msg = res.compile.stderr.strip() or res.compile.output.strip()
                return f"KOMPILYATSIYA: [CE]\n[Xatolik matni]:\n{err_msg}"

            # 2. TO - Vaqt tugashi (Timeout)
            if res.run.signal in ["SIGKILL", "SIGXCPU"]:
                return "IJRO: [TO] (Vaqt tugadi)"

            # 3. SG - Tizim signalida o'lish (Crash)
            if res.run.signal:
                return f"IJRO: [SG] (Tizim signali: {res.run.signal})"

            # 4. RE - Ish vaqtidagi xato
            if res.run.code != 0 or res.run.stderr:
                err_msg = res.run.stderr.strip() or f"Exit code: {res.run.code}"
                return f"IJRO: [RE]\n[Xatolik matni]:\n{err_msg}"

            # 5. OL / EL - Uzunlik cheklovlari oshishi
            MAX_LENGTH = 10000
            if len(res.run.stdout) > MAX_LENGTH:
                return "IJRO: [OL] (Uzunlik oshib ketdi)"
            if len(res.run.stderr) > MAX_LENGTH:
                return "IJRO: [EL] (Uzunlik oshib ketdi)"

            # 6. AC - Muvaffaqiyatli yakunlanish
            # Agar stdout bo'lsa natijani, bo'sh bo'lsa shunchaki [AC] xabarini beradi
            if res.run.stdout:
                return f"IJRO: [AC]\n[Natija]:\n{res.run.stdout}"
            return "IJRO: [AC] (Muvaffaqiyatli, dastur bo'sh)"

        except Exception as e:
            # XX - Ichki tizim xatoligi (Piston o'chganda yoki ulanish uzilganda)
            # Ortiqcha chiziqlarsiz, faqat xato kodi va sababi
            return f"TIZIM: [XX]\n[Xatolik matni]:\n{str(e)}"
