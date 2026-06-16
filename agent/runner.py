from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .config import AgentConfig
from .http import post_json


def post_event(
    cfg: AgentConfig,
    job_id: str,
    event_type: str,
    message: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return post_json(
        cfg.control_url,
        "/api/jobs/events",
        {
            "worker_id": cfg.worker_id,
            "agent_token": cfg.agent_token,
            "job_id": job_id,
            "event_type": event_type,
            "message": message,
            "payload": payload or {},
        },
    )


def complete_job(
    cfg: AgentConfig,
    job_id: str,
    status: str,
    message: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return post_json(
        cfg.control_url,
        "/api/jobs/complete",
        {
            "worker_id": cfg.worker_id,
            "agent_token": cfg.agent_token,
            "job_id": job_id,
            "status": status,
            "message": message,
            "payload": payload or {},
        },
    )


def create_approval(
    cfg: AgentConfig,
    job_id: str,
    title: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    return post_json(
        cfg.control_url,
        "/api/approvals",
        {
            "worker_id": cfg.worker_id,
            "agent_token": cfg.agent_token,
            "job_id": job_id,
            "title": title,
            "body": body,
        },
    )


def run_smoke_test(cfg: AgentConfig, job: dict[str, Any]) -> dict[str, Any]:
    job_id = job["id"]
    payload = job.get("payload") or {}
    job_dir = Path(cfg.work_dir).expanduser() / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    post_event(cfg, job_id, "started", "smoke_test started", {"payload": payload})

    delay_seconds = float(payload.get("delay_seconds") or 0)
    if delay_seconds > 0:
        time.sleep(min(delay_seconds, 5))

    if payload.get("request_approval"):
        approval = create_approval(
            cfg,
            job_id,
            title=str(payload.get("approval_title") or "Smoke test needs approval"),
            body={
                "risk": payload.get("risk") or "L4",
                "reason": payload.get("reason") or "smoke_test requested approval",
                "recommended": payload.get("recommended") or "review",
                "options": payload.get("options") or [],
            },
        )
        post_event(
            cfg,
            job_id,
            "blocked",
            "smoke_test blocked on approval",
            {"approval_id": approval["id"]},
        )
        return complete_job(
            cfg,
            job_id,
            "blocked",
            "smoke_test needs human approval",
            {"approval_id": approval["id"]},
        )

    if payload.get("fail"):
        post_event(
            cfg,
            job_id,
            "failed",
            "smoke_test simulated failure",
            {"reason": payload.get("reason") or "fail=true"},
        )
        return complete_job(
            cfg,
            job_id,
            "failed",
            "smoke_test simulated failure",
            {"reason": payload.get("reason") or "fail=true"},
        )

    result = {
        "message": payload.get("message") or "hello loop farm",
        "worker_id": cfg.worker_id,
        "machine_name": cfg.machine_name,
        "job_id": job_id,
    }
    result_path = job_dir / "result.json"
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    post_event(
        cfg,
        job_id,
        "artifact",
        "smoke_test wrote result artifact",
        {"path": str(result_path)},
    )
    return complete_job(
        cfg,
        job_id,
        "succeeded",
        "smoke_test completed",
        {"result": result, "artifact_path": str(result_path)},
    )


def run_job(cfg: AgentConfig, job: dict[str, Any]) -> dict[str, Any]:
    recipe = job["recipe"]
    try:
        if recipe == "smoke_test":
            return run_smoke_test(cfg, job)
        post_event(
            cfg,
            job["id"],
            "failed",
            "unknown recipe",
            {"recipe": recipe},
        )
        return complete_job(
            cfg,
            job["id"],
            "failed",
            f"unknown recipe: {recipe}",
            {"recipe": recipe},
        )
    except Exception as exc:
        try:
            post_event(
                cfg,
                job["id"],
                "failed",
                "runner exception",
                {"error": str(exc)},
            )
            return complete_job(
                cfg,
                job["id"],
                "failed",
                "runner exception",
                {"error": str(exc)},
            )
        except Exception:
            raise exc

