# services/piston_client.py

import httpx
from typing import Dict, Any, List
from decouple import config


PISTON_URL = config("PISTON_URL", default="http://localhost:2000/api/v2")


class PistonClient:
    def __init__(self):
        self.client = httpx.Client(timeout=30)

    def get_runtimes(self):
        return self.client.get(f"{PISTON_URL}/runtimes").json()

    def execute(
        self,
        language: str,
        version: str,
        code: str,
        stdin: str = "",
        args: List[str] = None,
    ) -> Dict[str, Any]:

        payload = {
            "language": language,
            "version": version,
            "files": [{"content": code}],
            "stdin": stdin,
            "args": args or [],
        }

        r = self.client.post(f"{PISTON_URL}/execute", json=payload)

        if r.status_code != 200:
            return {
                "run": {
                    "stdout": "",
                    "stderr": r.text,
                    "code": -1,
                    "status": "XX",
                }
            }

        return r.json()


piston_client = PistonClient()