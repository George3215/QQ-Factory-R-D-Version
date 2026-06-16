from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
from typing import Any
from urllib.parse import urlencode

from .http import request_json


DEFAULT_CONTROL_URL = "http://127.0.0.1:8787"
DEFAULT_ADMIN_TOKEN = "dev-admin-token"


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def control_url_from(args: argparse.Namespace) -> str:
    return args.control_url or os.environ.get("LOOP_FARM_CONTROL_URL", DEFAULT_CONTROL_URL)


def admin_token_from(args: argparse.Namespace) -> str:
    return args.admin_token or os.environ.get("LOOP_FARM_ADMIN_TOKEN", DEFAULT_ADMIN_TOKEN)


def cmd_tokens_create(args: argparse.Namespace) -> None:
    payload = {
        "machine_name": args.machine_name,
        "role": "worker",
        "ttl_seconds": args.ttl,
    }
    result = request_json(
        "POST",
        control_url_from(args),
        "/api/bootstrap-tokens",
        payload=payload,
        admin_token=admin_token_from(args),
    )
    print_json(result)


def bootstrap_shell_command(args: argparse.Namespace) -> str:
    parts = [
        "curl",
        "-fsSL",
        args.install_url,
        "|",
        "sudo",
        "bash",
        "-s",
        "--",
        "--control-url",
        shlex.quote(args.control_url),
        "--bootstrap-token",
        shlex.quote(args.token),
        "--machine-name",
        shlex.quote(args.machine_name),
    ]
    if args.repo_url:
        parts.extend(["--repo-url", shlex.quote(args.repo_url)])
    return " ".join(parts)


def worker_install_command(
    platform: str,
    control_url: str,
    machine_name: str,
    token: str,
    install_base_url: str,
    repo_url: str,
    tailscale_auth_key: str,
) -> str:
    base = install_base_url.rstrip("/")
    common = {
        "control_url": shlex.quote(control_url),
        "machine_name": shlex.quote(machine_name),
        "token": shlex.quote(token),
        "repo_url": shlex.quote(repo_url),
        "tailscale_auth_key": shlex.quote(tailscale_auth_key),
    }
    if platform == "linux":
        parts = [
            "curl",
            "-fsSL",
            f"{base}/worker-linux.sh",
            "|",
            "sudo",
            "bash",
            "-s",
            "--",
            "--control-url",
            common["control_url"],
            "--bootstrap-token",
            common["token"],
            "--machine-name",
            common["machine_name"],
        ]
        if repo_url:
            parts.extend(["--repo-url", common["repo_url"]])
        if tailscale_auth_key:
            parts.extend(["--tailscale-auth-key", common["tailscale_auth_key"]])
        return " ".join(parts)
    if platform == "macos":
        parts = [
            "curl",
            "-fsSL",
            f"{base}/worker-macos.sh",
            "|",
            "bash",
            "-s",
            "--",
            "--control-url",
            common["control_url"],
            "--bootstrap-token",
            common["token"],
            "--machine-name",
            common["machine_name"],
        ]
        if repo_url:
            parts.extend(["--repo-url", common["repo_url"]])
        if tailscale_auth_key:
            parts.extend(["--tailscale-auth-key", common["tailscale_auth_key"]])
        return " ".join(parts)
    if platform == "windows":
        script_url = f"{base}/worker-windows.ps1"
        ps_parts = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            shlex.quote(
                "& { "
                f"$script = Join-Path $env:TEMP 'worker-windows.ps1'; "
                f"Invoke-WebRequest -UseBasicParsing -Uri '{script_url}' -OutFile $script; "
                f"& $script -ControlUrl '{control_url}' -BootstrapToken '{token}' -MachineName '{machine_name}'"
                + (f" -RepoUrl '{repo_url}'" if repo_url else "")
                + (f" -TailscaleAuthKey '{tailscale_auth_key}'" if tailscale_auth_key else "")
                + " }"
            ),
        ]
        return " ".join(ps_parts)
    raise ValueError(f"unsupported platform: {platform}")


def cmd_worker_bootstrap_command(args: argparse.Namespace) -> None:
    print(bootstrap_shell_command(args))


def cmd_install_worker_command(args: argparse.Namespace) -> None:
    print(
        worker_install_command(
            platform=args.platform,
            control_url=args.control_url,
            machine_name=args.machine_name,
            token=args.token,
            install_base_url=args.install_base_url,
            repo_url=args.repo_url,
            tailscale_auth_key=args.tailscale_auth_key,
        )
    )


def cmd_workers_list(args: argparse.Namespace) -> None:
    result = request_json(
        "GET",
        control_url_from(args),
        "/api/workers",
        admin_token=admin_token_from(args),
    )
    print_json(result)


def cmd_jobs_create(args: argparse.Namespace) -> None:
    payload = {}
    if args.payload_json:
        payload = json.loads(args.payload_json)
    result = request_json(
        "POST",
        control_url_from(args),
        "/api/jobs",
        payload={
            "recipe": args.recipe,
            "payload": payload,
            "target_worker_id": args.target_worker_id,
        },
        admin_token=admin_token_from(args),
    )
    print_json(result)


def cmd_jobs_events(args: argparse.Namespace) -> None:
    path = "/api/job-events"
    if args.job_id:
        path = f"{path}?{urlencode({'job_id': args.job_id})}"
    result = request_json(
        "GET",
        control_url_from(args),
        path,
        admin_token=admin_token_from(args),
    )
    print_json(result)


def cmd_approvals_list(args: argparse.Namespace) -> None:
    result = request_json(
        "GET",
        control_url_from(args),
        "/api/approvals",
        admin_token=admin_token_from(args),
    )
    print_json(result)


def cmd_approvals_resolve(args: argparse.Namespace) -> None:
    decision = "approved" if args.decision == "approve" else "rejected"
    result = request_json(
        "POST",
        control_url_from(args),
        "/api/approvals/resolve",
        payload={
            "approval_id": args.approval_id,
            "decision": decision,
            "comment": args.comment,
        },
        admin_token=admin_token_from(args),
    )
    print_json(result)


def cmd_reports_list(args: argparse.Namespace) -> None:
    query = {}
    if args.worker_id:
        query["worker_id"] = args.worker_id
    if args.source:
        query["source"] = args.source
    if args.limit:
        query["limit"] = args.limit
    path = "/api/reports"
    if query:
        path = f"{path}?{urlencode(query)}"
    result = request_json(
        "GET",
        control_url_from(args),
        path,
        admin_token=admin_token_from(args),
    )
    print_json(result)


def add_common_control_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--control-url", default=None, help="Control API base URL.")
    parser.add_argument("--admin-token", default=None, help="Control API admin token.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="farmctl",
        description="Mac-side CLI for QQ Farm research automation.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    tokens = sub.add_parser("tokens", help="Manage bootstrap tokens.")
    tokens_sub = tokens.add_subparsers(dest="tokens_command", required=True)
    token_create = tokens_sub.add_parser("create", help="Create a worker bootstrap token.")
    add_common_control_args(token_create)
    token_create.add_argument("--machine-name", required=True)
    token_create.add_argument("--ttl", type=int, default=3600)
    token_create.set_defaults(func=cmd_tokens_create)

    worker = sub.add_parser("worker", help="Manage workers.")
    worker_sub = worker.add_subparsers(dest="worker_command", required=True)

    worker_list = worker_sub.add_parser("list", help="List registered workers.")
    add_common_control_args(worker_list)
    worker_list.set_defaults(func=cmd_workers_list)

    bootstrap = worker_sub.add_parser(
        "bootstrap-command", help="Print a one-line Linux bootstrap command."
    )
    bootstrap.add_argument("--control-url", required=True)
    bootstrap.add_argument("--machine-name", required=True)
    bootstrap.add_argument("--token", required=True)
    bootstrap.add_argument(
        "--install-url",
        default="https://control.example.com/install/worker-linux.sh",
        help="URL serving install/worker-linux.sh.",
    )
    bootstrap.add_argument(
        "--repo-url",
        default="",
        help="Git repo URL to clone on the worker. Leave empty when script is pre-bundled.",
    )
    bootstrap.set_defaults(func=cmd_worker_bootstrap_command)

    install = sub.add_parser("install", help="Generate integrated install commands.")
    install_sub = install.add_subparsers(dest="install_command", required=True)
    install_worker = install_sub.add_parser(
        "worker-command", help="Print a one-line worker installer command."
    )
    install_worker.add_argument("--platform", choices=["linux", "macos", "windows"], required=True)
    install_worker.add_argument("--control-url", required=True)
    install_worker.add_argument("--machine-name", required=True)
    install_worker.add_argument("--token", required=True)
    install_worker.add_argument(
        "--install-base-url",
        default="https://control.example.com/install",
        help="Base URL serving worker-linux.sh, worker-macos.sh, and worker-windows.ps1.",
    )
    install_worker.add_argument("--repo-url", default="")
    install_worker.add_argument("--tailscale-auth-key", default="")
    install_worker.set_defaults(func=cmd_install_worker_command)

    jobs = sub.add_parser("jobs", help="Manage jobs.")
    jobs_sub = jobs.add_subparsers(dest="jobs_command", required=True)
    job_create = jobs_sub.add_parser("create", help="Create a queued job.")
    add_common_control_args(job_create)
    job_create.add_argument("--recipe", required=True)
    job_create.add_argument("--target-worker-id", default=None)
    job_create.add_argument("--payload-json", default="{}")
    job_create.set_defaults(func=cmd_jobs_create)

    job_events = jobs_sub.add_parser("events", help="List job events.")
    add_common_control_args(job_events)
    job_events.add_argument("--job-id", default=None)
    job_events.set_defaults(func=cmd_jobs_events)

    approvals = sub.add_parser("approvals", help="Manage approval requests.")
    approvals_sub = approvals.add_subparsers(dest="approvals_command", required=True)
    approvals_list = approvals_sub.add_parser("list", help="List approval requests.")
    add_common_control_args(approvals_list)
    approvals_list.set_defaults(func=cmd_approvals_list)

    approvals_resolve = approvals_sub.add_parser(
        "resolve", help="Approve or reject an approval request."
    )
    add_common_control_args(approvals_resolve)
    approvals_resolve.add_argument("--approval-id", required=True)
    approvals_resolve.add_argument("--decision", choices=["approve", "reject"], required=True)
    approvals_resolve.add_argument("--comment", default="")
    approvals_resolve.set_defaults(func=cmd_approvals_resolve)

    reports = sub.add_parser("reports", help="View Codex/Claude/Agent reports from workers.")
    reports_sub = reports.add_subparsers(dest="reports_command", required=True)
    reports_list = reports_sub.add_parser("list", help="List worker reports.")
    add_common_control_args(reports_list)
    reports_list.add_argument("--worker-id", default=None)
    reports_list.add_argument("--source", choices=["agent", "codex", "claude_code", "system", "human"], default=None)
    reports_list.add_argument("--limit", type=int, default=200)
    reports_list.set_defaults(func=cmd_reports_list)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except Exception as exc:
        print(f"farmctl: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
