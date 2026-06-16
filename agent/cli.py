from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any

from . import __version__
from .config import DEFAULT_CONFIG_PATH, AgentConfig
from .http import post_json
from .inventory import collect_inventory, collect_metrics, self_test
from .runner import run_job


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def cmd_self_test(args: argparse.Namespace) -> None:
    print_json(self_test())


def cmd_register(args: argparse.Namespace) -> None:
    machine_name = args.machine_name or platform.node()
    inventory = collect_inventory()
    payload = {
        "token": args.bootstrap_token,
        "machine_name": machine_name,
        "hostname": inventory["hostname"],
        "os": inventory["os"],
        "tags": args.tag or [],
        "metadata": {
            "inventory": inventory,
            "agent_version": __version__,
        },
    }
    result = post_json(args.control_url, "/api/workers/register", payload)
    cfg = AgentConfig(
        control_url=args.control_url,
        machine_name=machine_name,
        worker_id=result["worker_id"],
        agent_token=result["agent_token"],
        heartbeat_interval=int(result.get("heartbeat_interval") or 10),
        work_dir=args.work_dir,
        artifact_dir=args.artifact_dir,
    )
    cfg.save(args.config)
    Path(cfg.work_dir).expanduser().mkdir(parents=True, exist_ok=True)
    Path(cfg.artifact_dir).expanduser().mkdir(parents=True, exist_ok=True)
    print_json(
        {
            "ok": True,
            "worker_id": cfg.worker_id,
            "machine_name": cfg.machine_name,
            "config": str(Path(args.config).expanduser()),
        }
    )


def send_heartbeat(cfg: AgentConfig, status: str = "online") -> dict[str, Any]:
    metrics = collect_metrics(Path(cfg.work_dir).expanduser())
    payload = {
        "worker_id": cfg.worker_id,
        "agent_token": cfg.agent_token,
        "machine_name": cfg.machine_name,
        "status": status,
        "metrics": metrics,
        "agent_version": __version__,
    }
    return post_json(cfg.control_url, "/api/workers/heartbeat", payload)


def claim_next_job(cfg: AgentConfig) -> dict[str, Any] | None:
    result = post_json(
        cfg.control_url,
        "/api/jobs/claim",
        {
            "worker_id": cfg.worker_id,
            "agent_token": cfg.agent_token,
        },
    )
    return result.get("job")


def run_cycle(cfg: AgentConfig) -> dict[str, Any]:
    heartbeat = send_heartbeat(cfg)
    job = claim_next_job(cfg)
    if job is None:
        return {"heartbeat": heartbeat, "job": None}
    result = run_job(cfg, job)
    return {"heartbeat": heartbeat, "job": job, "result": result}


def cmd_heartbeat(args: argparse.Namespace) -> None:
    cfg = AgentConfig.load(args.config)
    print_json(send_heartbeat(cfg, status=args.status))


def cmd_run_once(args: argparse.Namespace) -> None:
    cfg = AgentConfig.load(args.config)
    print_json(run_cycle(cfg))


def cmd_daemon(args: argparse.Namespace) -> None:
    cfg = AgentConfig.load(args.config)
    interval = args.interval or cfg.heartbeat_interval
    print(
        f"loop-farm-agent running for {cfg.machine_name} ({cfg.worker_id}); "
        f"heartbeat every {interval}s"
    )
    while True:
        try:
            result = run_cycle(cfg)
            print(json.dumps(result, ensure_ascii=False))
        except Exception as exc:
            print(f"agent cycle failed: {exc}", file=sys.stderr)
        if args.once:
            break
        time.sleep(interval)


def cmd_approval_request(args: argparse.Namespace) -> None:
    cfg = AgentConfig.load(args.config)
    body: dict[str, Any] = {}
    if args.body_json:
        body = json.loads(args.body_json)
    payload = {
        "worker_id": cfg.worker_id,
        "agent_token": cfg.agent_token,
        "job_id": args.job_id,
        "title": args.title,
        "body": body,
    }
    print_json(post_json(cfg.control_url, "/api/approvals", payload))


def cmd_report(args: argparse.Namespace) -> None:
    cfg = AgentConfig.load(args.config)
    payload_body: dict[str, Any] = {}
    if args.payload_json:
        payload_body = json.loads(args.payload_json)
    payload = {
        "worker_id": cfg.worker_id,
        "agent_token": cfg.agent_token,
        "source": args.source,
        "level": args.level,
        "title": args.title,
        "message": args.message,
        "payload": payload_body,
    }
    print_json(post_json(cfg.control_url, "/api/reports", payload))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="loop-farm-agent",
        description="Worker wrapper around EvoScientist for Loop Farm.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    self_test_cmd = sub.add_parser("self-test", help="Check local worker prerequisites.")
    self_test_cmd.set_defaults(func=cmd_self_test)

    register = sub.add_parser("register", help="Register this machine as a worker.")
    register.add_argument("--control-url", required=True)
    register.add_argument("--bootstrap-token", required=True)
    register.add_argument("--machine-name", default=None)
    register.add_argument("--tag", action="append", default=[])
    register.add_argument("--config", default=os.environ.get("LOOP_FARM_AGENT_CONFIG", DEFAULT_CONFIG_PATH))
    register.add_argument("--work-dir", default="~/.loop-farm-agent/workspaces")
    register.add_argument("--artifact-dir", default="~/.loop-farm-agent/artifacts")
    register.set_defaults(func=cmd_register)

    heartbeat = sub.add_parser("heartbeat", help="Send one heartbeat.")
    heartbeat.add_argument("--config", default=os.environ.get("LOOP_FARM_AGENT_CONFIG", DEFAULT_CONFIG_PATH))
    heartbeat.add_argument("--status", default="online")
    heartbeat.set_defaults(func=cmd_heartbeat)

    run_once = sub.add_parser("run-once", help="Send heartbeat, claim one job, run it.")
    run_once.add_argument("--config", default=os.environ.get("LOOP_FARM_AGENT_CONFIG", DEFAULT_CONFIG_PATH))
    run_once.set_defaults(func=cmd_run_once)

    daemon = sub.add_parser("daemon", help="Run the heartbeat daemon.")
    daemon.add_argument("--config", default=os.environ.get("LOOP_FARM_AGENT_CONFIG", DEFAULT_CONFIG_PATH))
    daemon.add_argument("--interval", type=int, default=None)
    daemon.add_argument("--once", action="store_true")
    daemon.set_defaults(func=cmd_daemon)

    approval = sub.add_parser("approval-request", help="Create an approval request.")
    approval.add_argument("--config", default=os.environ.get("LOOP_FARM_AGENT_CONFIG", DEFAULT_CONFIG_PATH))
    approval.add_argument("--job-id", default=None)
    approval.add_argument("--title", required=True)
    approval.add_argument("--body-json", default="{}")
    approval.set_defaults(func=cmd_approval_request)

    report = sub.add_parser("report", help="Send a Codex/Claude/Agent report to the Mac control host.")
    report.add_argument("--config", default=os.environ.get("LOOP_FARM_AGENT_CONFIG", DEFAULT_CONFIG_PATH))
    report.add_argument("--source", choices=["agent", "codex", "claude_code", "system", "human"], default="agent")
    report.add_argument("--level", choices=["debug", "info", "warning", "error", "blocked", "needs_human"], default="info")
    report.add_argument("--title", required=True)
    report.add_argument("--message", default="")
    report.add_argument("--payload-json", default="{}")
    report.set_defaults(func=cmd_report)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except Exception as exc:
        print(f"loop-farm-agent: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
