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

        timeout = httpx.Timeout(connect=15.0, read=30.0, write=30.0, pool=15.0)
        self.async_client = httpx.AsyncClient(timeout=timeout, headers=self.headers)
        self.sync_client = httpx.Client(timeout=timeout, headers=self.headers)

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
        response = self.sync_client.post(self.url, json=payload)
        if response.is_error:
            self._handle_error(response)
        return response.json()

    def close(self):
        self.sync_client.close()


piston = PistonClient(base_url=config("PISTON_URL", default="https://pnqdbzm7-2000.jpe1.devtunnels.ms/api/v2"))
