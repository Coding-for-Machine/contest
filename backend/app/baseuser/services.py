# apps/users/services.py

import httpx
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class AsyncAuthService:
    """
    Auth server bilan aloqa — to'liq async (httpx.AsyncClient).

    GET /api/user  →  200 OK:
        {
            "id": 7142908334,                        # telegram_id
            "u":  "Coding_for_Machines",             # username
            "p":  "998979437674",                    # phone
            "f":  "CfM 🐾 ✨🌙",                    # full_name
            "l":  "2026-06-26 07:03:36.747693+00:00" # last_login
        }
    """

    def __init__(self):
        self.base_url = settings.AUTH_SERVER_BASE_URL
        self.timeout  = httpx.Timeout(10.0)

    async def get_user_info(self, token: str) -> tuple[dict, int | None]:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/user",
                    headers=headers,
                )
                response.raise_for_status()
                return response.json(), response.status_code

        except httpx.HTTPStatusError as e:
            try:
                err_data = e.response.json()
            except Exception:
                err_data = {"error": "Auth server xatoligi yoki yaroqsiz token"}
            status = e.response.status_code if e.response else None
            logger.warning("Auth server %s qaytardi: %s", status, err_data)
            return err_data, status

        except httpx.RequestError as e:
            logger.error("Auth serverga ulanib bo'lmadi: %s", e)
            return {"error": f"Auth serverga ulanib bo'lmadi: {e}"}, None


auth_service = AsyncAuthService()