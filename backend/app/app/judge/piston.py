# piston_client.py
import httpx
import msgspec
from typing import List, Optional
from decouple import config

class StageResult(msgspec.Struct):
    """Kompilyatsiya yoki Ijro (Run) bosqichining to'liq tahlili"""
    stdout: str
    stderr: str
    output: str
    code: Optional[int] = None       # Jarayon yakunlanish kodi (0 - muvaffaqiyatli)
    signal: Optional[str] = None     # Tizim signali (Masalan: SIGKILL, SIGSEGV)

class PistonExecuteResponse(msgspec.Struct):
    """POST /api/v2/execute so'rovidan qaytadigan to'liq kontent"""
    language: str
    version: str
    run: StageResult
    compile: Optional[StageResult] = None  # Faqat kompilyatsiya qilinadigan tillarda keladi


class PistonClient:
    """Piston API v2 bilan ishlovchi asinxron professional klient"""
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        # Gorizontal masshtabda ulanishlar uzilib qolmasligi uchun pool va timeout sozlamalari
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(15.0, read=30.0))

    async def execute_code(
        self,
        language: str,
        version: str,
        code_content: str,
        file_name: Optional[str] = None,
        stdin: str = "",
        args: Optional[List[str]] = None,
        run_timeout: int = 2000,          # millisekund (2 soniya)
        compile_timeout: int = 10000,     # millisekund (10 soniya)
        run_memory_limit: int = -1,       # bayt (-1 cheklovsiz)
        compile_memory_limit: int = -1
    ) -> PistonExecuteResponse:
        """
        Piston API orqali kodni barcha cheklovlar ostida yugurtirish
        va natijani to'liq model holatida qaytarish.
        """
        url = f"{self.base_url}/execute"
        
        # Fayl obyektini shakllantirish
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
            "compile_memory_limit": compile_memory_limit
        }

        response = await self.client.post(url, json=payload)
        
        if response.is_error:
            # Piston 4xx/5xx xatolik berganda uning ichki xabarini ko'rsatamiz
            try:
                err_msg = response.json().get("message", response.text)
            except Exception:
                err_msg = response.text
            raise Exception(f"Piston API Error: {response.status_code} - {err_msg}")

        # msgspec yordamida kelgan JSONni PistonExecuteResponse modeliga parslaymiz (Juda tez)
        return msgspec.json.decode(response.content, type=PistonExecuteResponse)

    async def close(self):
        """Kompaniyaning ulanishlar poolini yopish"""
        await self.client.close()


base_url = config("PISTON_URL", default="http://localhost:2000/api/v2")

# Tizim bo'yicha yagona (Singleton) global asinxron klient obyekti
piston_client = PistonClient(base_url=base_url)


