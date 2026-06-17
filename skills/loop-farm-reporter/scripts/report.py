#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_CONFIG_PATH = "~/.loop-farm-agent/config.json"
SOURCES = ("agent", "codex", "claude_code", "system", "human")
LEVELS = ("debug", "info", "warning", "error", "blocked", "needs_human")


def default_config_candidates(path: str | None) -> list[Path]:
    if path:
        return [Path(path).expanduser()]
    env_path = os.environ.get("LOOP_FARM_AGENT_CONFIG")
    if env_path:
        return [Path(env_path).expanduser()]

    candidates = [Path(DEFAULT_CONFIG_PATH).expanduser()]
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(Path(local_app_data) / "LoopFarmAgent" / "config.json")
    return candidates


def load_config(path: str | None) -> dict[str, Any]:
    for target in default_config_candidates(path):
        if target.exists():
            return json.loads(target.read_text(encoding="utf-8"))
    return {}


def first_value(*values: str | None) -> str:
    for value in values:
        if value:
            return value
    return ""


def require_value(name: str, value: str) -> str:
    if value:
        return value
    raise SystemExit(
        f"missing {name}; pass --{name.replace('_', '-')} or configure the worker agent first"
    )


def parse_payload(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise SystemExit("--payload-json must decode to a JSON object")
    return payload


def post_json(base_url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/api/reports"
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        text = exc.read().decode("utf-8")
        raise SystemExit(f"report failed: HTTP {exc.code}: {text}") from exc
    except URLError as exc:
        raise SystemExit(f"report failed: {exc.reason}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Report Codex, Claude Code, or agent status to the Loop Farm Mac control host."
    )
    parser.add_argument("--config", default=None, help="Worker config JSON path.")
    parser.add_argument("--control-url", default=None)
    parser.add_argument("--worker-id", default=None)
    parser.add_argument("--agent-token", default=None)
    parser.add_argument("--source", choices=SOURCES, default="codex")
    parser.add_argument("--level", choices=LEVELS, default="info")
    parser.add_argument("--title", required=True)
    parser.add_argument(
        "--message",
        default="",
        help="Report body. Use '-' to read from stdin.",
    )
    parser.add_argument("--payload-json", default="{}")
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the report payload without sending it.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    message = sys.stdin.read() if args.message == "-" else args.message

    control_url = require_value(
        "control_url",
        first_value(
            args.control_url,
            os.environ.get("LOOP_FARM_CONTROL_URL"),
            config.get("control_url"),
        ),
    )
    worker_id = require_value(
        "worker_id",
        first_value(
            args.worker_id,
            os.environ.get("LOOP_FARM_WORKER_ID"),
            config.get("worker_id"),
        ),
    )
    agent_token = require_value(
        "agent_token",
        first_value(
            args.agent_token,
            os.environ.get("LOOP_FARM_AGENT_TOKEN"),
            config.get("agent_token"),
        ),
    )

    payload = {
        "worker_id": worker_id,
        "agent_token": agent_token,
        "source": args.source,
        "level": args.level,
        "title": args.title,
        "message": message,
        "payload": parse_payload(args.payload_json),
    }

    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    result = post_json(control_url, payload, timeout=args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
