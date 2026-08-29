import os
import base64
import httpx
from decouple import config


class PistonClient:
    """Piston API v2 bilan asinxron va sinxron ishlovchi professional klient."""

    def __init__(self, base_url: str, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.url = f"{self.base_url}/execute"
        self.headers = {"Content-Type": "application/json"}

        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

        self._timeout = httpx.Timeout(connect=15.0, read=30.0, write=30.0, pool=15.0)

        # ASYNC client — faqat Django async view (bitta event loop, bitta process)
        # ichida ishlatiladi, shuning uchun bu yerda darhol yaratish xavfsiz.
        self.async_client = httpx.AsyncClient(timeout=self._timeout, headers=self.headers)

        # SYNC client — Celery prefork worker fork qilingandan KEYIN yaratilishi
        # SHART, aks holda connection pool worker processlar orasida buziladi
        # va tasodifiy ConnectionResetError/RemoteProtocolError beradi (RE sifatida
        # ko'rinadi). Shuning uchun bu yerda darhol yaratmaymiz — lazy qilib,
        # PID o'zgarganda qayta yaratamiz (fork-safe).
        self._sync_client: httpx.Client | None = None
        self._sync_client_pid: int | None = None

    @property
    def sync_client(self) -> httpx.Client:
        current_pid = os.getpid()
        if self._sync_client is None or self._sync_client_pid != current_pid:
            # Eski client boshqa (parent) processga tegishli bo'lsa, uni yopishga
            # urinmaymiz — u process uchun kerak bo'lishi mumkin va yopish xavfli.
            self._sync_client = httpx.Client(timeout=self._timeout, headers=self.headers)
            self._sync_client_pid = current_pid
        return self._sync_client

    def _build_payload(
        self, language: str, version: str, code: str, stdin: str,
        run_timeout: int, run_memory_limit: int, encoding: str = "utf8",
    ) -> dict:
        file_entry = {"content": code}
        if encoding != "utf8":
            file_entry["encoding"] = encoding

        return {
            "language": language,
            "version": version,
            "files": [file_entry],
            "stdin": stdin,
            "run_timeout": run_timeout,
            "run_memory_limit": run_memory_limit,
        }

    @staticmethod
    def _handle_error(response: httpx.Response):
        try:
            err_msg = response.json().get("message", response.text)
        except Exception:
            err_msg = response.text
        raise Exception(f"Piston API Error [{response.status_code}]: {err_msg}")

    # ================= ASYNC (Views uchun) =================
    async def async_execute_code(
        self, language: str, version: str, code: str, stdin: str = "",
        run_timeout: int = 2000, run_memory_limit: int = -1, encoding: str = "utf8",
    ):
        payload = self._build_payload(
            language, version, code, stdin, run_timeout, run_memory_limit, encoding=encoding
        )
        response = await self.async_client.post(self.url, json=payload)
        if response.is_error:
            self._handle_error(response)
        return response.json()

    async def aclose(self):
        await self.async_client.aclose()

    # ================= SYNC (Celery Tasks uchun) =================
    def sync_execute_code(
        self, language: str, version: str, code: str, stdin: str = "",
        run_timeout: int = 2000, run_memory_limit: int = -1, encoding: str = "utf8",
    ):
        payload = self._build_payload(
            language, version, code, stdin, run_timeout, run_memory_limit, encoding=encoding
        )
        # self.sync_client — property, PID o'zgargan bo'lsa avtomatik qayta yaratadi
        response = self.sync_client.post(self.url, json=payload)
        if response.is_error:
            self._handle_error(response)
        return response.json()

    def close(self):
        if self._sync_client is not None:
            self._sync_client.close()


piston = PistonClient(base_url=config("PISTON_URL", default="http://localhost:2000/api/v2"))