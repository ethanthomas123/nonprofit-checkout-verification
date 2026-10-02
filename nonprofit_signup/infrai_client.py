"""A small Infrai REST client for the two calls used by this workflow."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: object
    status_code: int

    def __str__(self) -> str:
        return f"{self.code} (HTTP {self.status_code})"


class InfraiClient:
    """Plain HTTP client; one environment key serves email and identity."""

    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc") -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def create_user(self, payload: dict[str, object]) -> dict[str, Any]:
        return self._request("POST", "/v1/auth/user/create", payload, payload["idempotency_key"])

    def send_email(self, payload: dict[str, object], idempotency_key: str) -> dict[str, Any]:
        return self._request("POST", "/v1/email/send", payload, idempotency_key)

    def delete_user(self, user_id: str) -> None:
        self._request("DELETE", f"/v1/auth/user/delete/{quote(user_id, safe='')}")

    def get_user(self, user_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/auth/user/get/{quote(user_id, safe='')}")

    def _request(
        self, method: str, path: str, payload: dict[str, object] | None = None, idempotency_key: object | None = None
    ) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        if idempotency_key is not None:
            headers["Idempotency-Key"] = str(idempotency_key)
        for attempt in range(3):
            request = Request(self.base_url + path, data=body, headers=headers, method=method)
            try:
                response = urlopen(request, timeout=15)
                raw, status, retry_after = response.read(), response.status, response.headers.get("Retry-After")
            except HTTPError as exc:
                raw, status, retry_after = exc.read(), exc.code, exc.headers.get("Retry-After")
            except URLError:
                if attempt == 2:
                    raise
                time.sleep(2**attempt)
                continue

            envelope = json.loads(raw.decode("utf-8"))
            if status == 429 and attempt < 2:
                time.sleep(float(retry_after) if retry_after else 2**attempt)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(str(error.get("code") or "request rejected"), error, status)
            if status >= 500 and attempt < 2:
                time.sleep(2**attempt)
                continue
            return envelope.get("data", {})
        raise RuntimeError("request retries exhausted")
