from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def post_json(
    base_url: str, path: str, payload: dict[str, Any], timeout: int = 15
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        text = exc.read().decode("utf-8")
        try:
            detail = json.loads(text)
        except json.JSONDecodeError:
            detail = {"error": text}
        raise RuntimeError(f"POST {url} failed: {detail}") from exc

