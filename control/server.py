from __future__ import annotations

import argparse
import json
import mimetypes
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

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
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path in {"/health", "/api/health"}:
                self.send_json({"ok": True, "service": "loop-farm-control"})
            elif path == "/api/workers":
                self.require_admin()
                self.send_json({"workers": self.store.list_workers()})
            elif path == "/api/jobs":
                self.require_admin()
                self.send_json({"jobs": self.store.list_jobs()})
            elif path == "/api/job-events":
                self.require_admin()
                query = parse_qs(parsed.query)
                job_id = query.get("job_id", [None])[0]
                self.send_json({"events": self.store.list_job_events(job_id=job_id)})
            elif path == "/api/reports":
                self.require_admin()
                query = parse_qs(parsed.query)
                worker_id = query.get("worker_id", [None])[0]
                source = query.get("source", [None])[0]
                limit = int(query.get("limit", ["200"])[0])
                self.send_json(
                    {
                        "reports": self.store.list_worker_reports(
                            worker_id=worker_id, source=source, limit=limit
                        )
                    }
                )
            elif path == "/api/chat":
                self.require_admin()
                query = parse_qs(parsed.query)
                worker_id = query.get("worker_id", [None])[0]
                limit = int(query.get("limit", ["200"])[0])
                self.send_json(
                    {
                        "messages": self.store.list_chat_messages(
                            worker_id=worker_id, limit=limit
                        )
                    }
                )
            elif path == "/api/approvals":
                self.require_admin()
                self.send_json({"approvals": self.store.list_approvals()})
            elif path.startswith("/install/"):
                self.serve_install_file(path)
            elif self.server.ui_dir is not None:  # type: ignore[attr-defined]
                self.serve_ui_file(path)
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
            elif path == "/api/jobs/claim":
                self.send_json(self.store.claim_job(body))
            elif path == "/api/jobs/events":
                self.send_json(
                    self.store.record_job_event(body), status=HTTPStatus.CREATED
                )
            elif path == "/api/jobs/complete":
                self.send_json(self.store.complete_job(body))
            elif path == "/api/reports":
                self.send_json(
                    self.store.create_worker_report(body), status=HTTPStatus.CREATED
                )
            elif path == "/api/chat":
                self.require_admin()
                self.send_json(
                    self.store.create_chat_message(body), status=HTTPStatus.CREATED
                )
            elif path == "/api/approvals":
                self.send_json(
                    self.store.create_approval(body), status=HTTPStatus.CREATED
                )
            elif path == "/api/approvals/resolve":
                self.require_admin()
                self.send_json(self.store.resolve_approval(body))
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

    def serve_static_file(self, root: Path, request_path: str, index: bool = False) -> None:
        rel = unquote(request_path).lstrip("/")
        if index and (rel == "" or rel.endswith("/")):
            rel = f"{rel}index.html"
        target = (root / rel).resolve()
        root_resolved = root.resolve()
        if root_resolved not in target.parents and target != root_resolved:
            self.send_error_json(HTTPStatus.FORBIDDEN, "forbidden")
            return
        if not target.is_file():
            self.send_error_json(HTTPStatus.NOT_FOUND, "not found")
            return
        mime, _ = mimetypes.guess_type(str(target))
        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def serve_ui_file(self, path: str) -> None:
        ui_dir = self.server.ui_dir  # type: ignore[attr-defined]
        rel_path = path
        if rel_path == "/":
            rel_path = "/index.html"
        self.serve_static_file(ui_dir, rel_path.lstrip("/"), index=False)

    def serve_install_file(self, path: str) -> None:
        install_dir = self.server.install_dir  # type: ignore[attr-defined]
        rel_path = path.removeprefix("/install/")
        self.serve_static_file(install_dir, rel_path, index=False)

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
        ui_dir: Path | None,
        install_dir: Path,
    ):
        super().__init__(server_address, RequestHandlerClass)
        self.store = store
        self.admin_token = admin_token
        self.ui_dir = ui_dir
        self.install_dir = install_dir


def run(
    host: str,
    port: int,
    db_path: str,
    admin_token: str,
    ui_dir: str | None = None,
    install_dir: str = "install",
) -> None:
    store = Store(db_path)
    ui_path = Path(ui_dir).resolve() if ui_dir else None
    install_path = Path(install_dir).resolve()
    server = ControlServer(
        (host, port),
        ControlHandler,
        store,
        admin_token,
        ui_path,
        install_path,
    )
    print(f"loop-farm-control listening on http://{host}:{port}")
    print(f"database: {db_path}")
    if ui_path:
        print(f"ui: {ui_path}")
    print(f"install scripts: {install_path}")
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
    parser.add_argument("--ui", default=os.environ.get("LOOP_FARM_UI_DIR"))
    parser.add_argument(
        "--install-dir",
        default=os.environ.get("LOOP_FARM_INSTALL_DIR", "install"),
    )
    args = parser.parse_args()
    run(args.host, args.port, args.db, args.admin_token, args.ui, args.install_dir)


if __name__ == "__main__":
    main()
