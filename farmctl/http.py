from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def request_json(
    method: str,
    base_url: str,
    path: str,
    payload: dict[str, Any] | None = None,
    admin_token: str | None = None,
    timeout: int = 15,
) -> dict[str, Any]:
    base = base_url.rstrip("/")
    url = f"{base}{path}"
    headers = {"Accept": "application/json"}
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if admin_token:
        headers["Authorization"] = f"Bearer {admin_token}"
    req = Request(url, data=body, method=method, headers=headers)
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        text = exc.read().decode("utf-8")
        try:
            detail = json.loads(text)
        except json.JSONDecodeError:
            detail = {"error": text}
        raise RuntimeError(f"{method} {url} failed: {detail}") from exc

