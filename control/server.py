from __future__ import annotations

import argparse
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from .store import Store


DEFAULT_ADMIN_TOKEN = "dev-admin-token"


class ControlHandler(BaseHTTPRequestHandler):
    server_version = "LoopFarmControl/0.1"

    @property
    def store(self) -> Store:
        return self.server.store  # type: ignore[attr-defined]

    @property
    def admin_token(self) -> str:
        return self.server.admin_token  # type: ignore[attr-defined]

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/health":
                self.send_json({"ok": True, "service": "loop-farm-control"})
            elif path == "/api/workers":
                self.require_admin()
                self.send_json({"workers": self.store.list_workers()})
            elif path == "/api/jobs":
                self.require_admin()
                self.send_json({"jobs": self.store.list_jobs()})
            elif path == "/api/approvals":
                self.require_admin()
                self.send_json({"approvals": self.store.list_approvals()})
            else:
                self.send_error_json(HTTPStatus.NOT_FOUND, "not found")
        except Exception as exc:
            self.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            body = self.read_json()
            if path == "/api/bootstrap-tokens":
                self.require_admin()
                token = self.store.create_bootstrap_token(
                    machine_name=str(body["machine_name"]),
                    role=str(body.get("role") or "worker"),
                    ttl_seconds=int(body.get("ttl_seconds") or 3600),
                )
                self.send_json(token, status=HTTPStatus.CREATED)
            elif path == "/api/workers/register":
                worker = self.store.register_worker(body)
                self.send_json(
                    {
                        "worker_id": worker["id"],
                        "machine_name": worker["machine_name"],
                        "agent_token": worker["agent_token"],
                        "heartbeat_interval": 10,
                    },
                    status=HTTPStatus.CREATED,
                )
            elif path == "/api/workers/heartbeat":
                self.send_json(self.store.heartbeat(body))
            elif path == "/api/jobs":
                self.require_admin()
                job = self.store.create_job(
                    recipe=str(body["recipe"]),
                    payload=body.get("payload") or {},
                    target_worker_id=body.get("target_worker_id"),
                )
                self.send_json(job, status=HTTPStatus.CREATED)
            elif path == "/api/approvals":
                self.send_json(
                    self.store.create_approval(body), status=HTTPStatus.CREATED
                )
            else:
                self.send_error_json(HTTPStatus.NOT_FOUND, "not found")
        except Exception as exc:
            self.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def require_admin(self) -> None:
        expected = f"Bearer {self.admin_token}"
        if self.headers.get("Authorization") != expected:
            raise PermissionError("missing or invalid admin token")

    def send_json(
        self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK
    ) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_error_json(self, status: HTTPStatus, message: str) -> None:
        self.send_json({"ok": False, "error": message}, status=status)

    def log_message(self, fmt: str, *args: Any) -> None:
        if os.environ.get("LOOP_FARM_QUIET_HTTP") == "1":
            return
        super().log_message(fmt, *args)


class ControlServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        RequestHandlerClass: type[BaseHTTPRequestHandler],
        store: Store,
        admin_token: str,
    ):
        super().__init__(server_address, RequestHandlerClass)
        self.store = store
        self.admin_token = admin_token


def run(host: str, port: int, db_path: str, admin_token: str) -> None:
    store = Store(db_path)
    server = ControlServer((host, port), ControlHandler, store, admin_token)
    print(f"loop-farm-control listening on http://{host}:{port}")
    print(f"database: {db_path}")
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Loop Farm control API.")
    parser.add_argument("--host", default=os.environ.get("LOOP_FARM_HOST", "127.0.0.1"))
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("LOOP_FARM_PORT", "8787"))
    )
    parser.add_argument(
        "--db",
        default=os.environ.get("LOOP_FARM_DB", "data/loop-farm-control.sqlite3"),
    )
    parser.add_argument(
        "--admin-token",
        default=os.environ.get("LOOP_FARM_ADMIN_TOKEN", DEFAULT_ADMIN_TOKEN),
    )
    args = parser.parse_args()
    run(args.host, args.port, args.db, args.admin_token)


if __name__ == "__main__":
    main()

