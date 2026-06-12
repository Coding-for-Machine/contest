# apps/users/services.py

import httpx
import logging
from typing import Tuple, Dict, Optional
from django.conf import settings


logger = logging.getLogger(__name__)


class AuthService:
    """
    Auth server bilan aloqa (SYNC VERSION)
    """

    def __init__(self):
        self.base_url = settings.AUTH_SERVER_BASE_URL
        self.timeout = 10.0

    def verify_token(self, token: str) -> Tuple[bool, Optional[int]]:

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        try:
            response = httpx.get(
                f"{self.base_url}/api/verify",
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return True, response.status_code

        except httpx.HTTPStatusError as e:
            return False, e.response.status_code if e.response else None

        except httpx.RequestError:
            return False, None

    def get_user_info(self, token: str) -> Tuple[Dict, Optional[int]]:

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        try:
            response = httpx.get(
                f"{self.base_url}/api/user",
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json(), response.status_code

        except httpx.HTTPStatusError as e:
            return {"error": "Auth failed"}, e.response.status_code if e.response else None

        except httpx.RequestError as e:
            return {"error": str(e)}, None


auth_service = AuthService()
