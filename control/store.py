from __future__ import annotations

import json
import secrets
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any


def now_ts() -> int:
    return int(time.time())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def new_token(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(32)}"


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        self.init_schema()

    def init_schema(self) -> None:
        self.conn.executescript(
            """
            create table if not exists bootstrap_tokens (
                token text primary key,
                machine_name text not null,
                role text not null,
                expires_at integer not null,
                used_at integer,
                created_at integer not null
            );

            create table if not exists workers (
                id text primary key,
                machine_name text not null unique,
                hostname text not null,
                os_name text not null,
                tags_json text not null,
                metadata_json text not null,
                agent_token text not null,
                status text not null,
                last_seen integer,
                created_at integer not null
            );

            create table if not exists jobs (
                id text primary key,
                target_worker_id text,
                recipe text not null,
                payload_json text not null,
                status text not null,
                created_at integer not null,
                updated_at integer not null
            );

            create table if not exists job_events (
                id text primary key,
                job_id text,
                worker_id text,
                event_type text not null,
                message text not null,
                payload_json text not null,
                created_at integer not null
            );

            create table if not exists approval_requests (
                id text primary key,
                worker_id text,
                job_id text,
                title text not null,
                body_json text not null,
                status text not null,
                created_at integer not null,
                resolved_at integer
            );

            create table if not exists worker_reports (
                id text primary key,
                worker_id text not null,
                source text not null,
                level text not null,
                title text not null,
                message text not null,
                payload_json text not null,
                created_at integer not null
            );

            create table if not exists audit_logs (
                id text primary key,
                actor_type text not null,
                actor_id text not null,
                action text not null,
                payload_json text not null,
                created_at integer not null
            );
            """
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def create_bootstrap_token(
        self, machine_name: str, role: str = "worker", ttl_seconds: int = 3600
    ) -> dict[str, Any]:
        token = new_token("lfbt")
        ts = now_ts()
        row = {
            "token": token,
            "machine_name": machine_name,
            "role": role,
            "expires_at": ts + ttl_seconds,
            "created_at": ts,
        }
        with self.conn:
            self.conn.execute(
                """
                insert into bootstrap_tokens
                (token, machine_name, role, expires_at, created_at)
                values (?, ?, ?, ?, ?)
                """,
                (token, machine_name, role, row["expires_at"], ts),
            )
            self.audit("admin", "control", "bootstrap_token.create", row)
        return row

    def consume_bootstrap_token(self, token: str, machine_name: str) -> sqlite3.Row:
        row = self.conn.execute(
            "select * from bootstrap_tokens where token = ?", (token,)
        ).fetchone()
        if row is None:
            raise ValueError("bootstrap token not found")
        if row["used_at"] is not None:
            raise ValueError("bootstrap token already used")
        if row["expires_at"] < now_ts():
            raise ValueError("bootstrap token expired")
        if row["machine_name"] != machine_name:
            raise ValueError("bootstrap token machine_name mismatch")
        with self.conn:
            self.conn.execute(
                "update bootstrap_tokens set used_at = ? where token = ?",
                (now_ts(), token),
            )
        return row

    def register_worker(self, payload: dict[str, Any]) -> dict[str, Any]:
        machine_name = str(payload["machine_name"])
        token = str(payload["token"])
        self.consume_bootstrap_token(token, machine_name)

        worker_id = new_id("wkr")
        agent_token = new_token("lfat")
        tags = payload.get("tags") or []
        metadata = payload.get("metadata") or {}
        ts = now_ts()
        row = {
            "id": worker_id,
            "machine_name": machine_name,
            "hostname": str(payload.get("hostname") or machine_name),
            "os_name": str(payload.get("os") or "unknown"),
            "tags": tags,
            "metadata": metadata,
            "agent_token": agent_token,
            "status": "registered",
            "last_seen": ts,
            "created_at": ts,
        }
        with self.conn:
            self.conn.execute(
                """
                insert into workers
                (id, machine_name, hostname, os_name, tags_json, metadata_json,
                 agent_token, status, last_seen, created_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    worker_id,
                    machine_name,
                    row["hostname"],
                    row["os_name"],
                    json.dumps(tags),
                    json.dumps(metadata),
                    agent_token,
                    row["status"],
                    ts,
                    ts,
                ),
            )
            self.audit("worker", worker_id, "worker.register", row)
        return row

    def verify_worker(self, worker_id: str, agent_token: str) -> sqlite3.Row:
        row = self.conn.execute(
            "select * from workers where id = ?", (worker_id,)
        ).fetchone()
        if row is None:
            raise ValueError("worker not found")
        if row["agent_token"] != agent_token:
            raise ValueError("invalid agent token")
        return row

    def heartbeat(self, payload: dict[str, Any]) -> dict[str, Any]:
        worker_id = str(payload["worker_id"])
        agent_token = str(payload["agent_token"])
        self.verify_worker(worker_id, agent_token)
        status = str(payload.get("status") or "online")
        ts = now_ts()
        with self.conn:
            self.conn.execute(
                "update workers set status = ?, last_seen = ? where id = ?",
                (status, ts, worker_id),
            )
            self.conn.execute(
                """
                insert into job_events
                (id, worker_id, event_type, message, payload_json, created_at)
                values (?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id("evt"),
                    worker_id,
                    "heartbeat",
                    status,
                    json.dumps(payload.get("metrics") or {}),
                    ts,
                ),
            )
        return {"ok": True, "worker_id": worker_id, "last_seen": ts}

    def list_workers(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            select id, machine_name, hostname, os_name, tags_json, metadata_json,
                   status, last_seen, created_at
            from workers
            order by machine_name
            """
        ).fetchall()
        return [
            {
                "id": row["id"],
                "machine_name": row["machine_name"],
                "hostname": row["hostname"],
                "os": row["os_name"],
                "tags": json.loads(row["tags_json"]),
                "metadata": json.loads(row["metadata_json"]),
                "status": row["status"],
                "last_seen": row["last_seen"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def create_job(
        self, recipe: str, payload: dict[str, Any], target_worker_id: str | None = None
    ) -> dict[str, Any]:
        job_id = new_id("job")
        ts = now_ts()
        row = {
            "id": job_id,
            "target_worker_id": target_worker_id,
            "recipe": recipe,
            "payload": payload,
            "status": "queued",
            "created_at": ts,
            "updated_at": ts,
        }
        with self.conn:
            self.conn.execute(
                """
                insert into jobs
                (id, target_worker_id, recipe, payload_json, status, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    target_worker_id,
                    recipe,
                    json.dumps(payload),
                    row["status"],
                    ts,
                    ts,
                ),
            )
            self.audit("admin", "control", "job.create", row)
        return row

    def job_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "target_worker_id": row["target_worker_id"],
            "recipe": row["recipe"],
            "payload": json.loads(row["payload_json"]),
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def list_jobs(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            select id, target_worker_id, recipe, payload_json, status, created_at, updated_at
            from jobs
            order by created_at desc
            """
        ).fetchall()
        return [self.job_from_row(row) for row in rows]

    def claim_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        worker_id = str(payload["worker_id"])
        agent_token = str(payload["agent_token"])
        self.verify_worker(worker_id, agent_token)
        ts = now_ts()
        with self.lock:
            row = self.conn.execute(
                """
                select id, target_worker_id, recipe, payload_json, status, created_at, updated_at
                from jobs
                where status = 'queued'
                  and (target_worker_id is null or target_worker_id = ?)
                order by created_at asc
                limit 1
                """,
                (worker_id,),
            ).fetchone()
            if row is None:
                return {"job": None}
            with self.conn:
                cursor = self.conn.execute(
                    """
                    update jobs
                    set status = 'running', target_worker_id = ?, updated_at = ?
                    where id = ? and status = 'queued'
                    """,
                    (worker_id, ts, row["id"]),
                )
                if cursor.rowcount != 1:
                    return {"job": None}
                self.conn.execute(
                    """
                    insert into job_events
                    (id, job_id, worker_id, event_type, message, payload_json, created_at)
                    values (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        new_id("evt"),
                        row["id"],
                        worker_id,
                        "claimed",
                        "job claimed by worker",
                        json.dumps({}),
                        ts,
                    ),
                )
        claimed = self.conn.execute(
            """
            select id, target_worker_id, recipe, payload_json, status, created_at, updated_at
            from jobs
            where id = ?
            """,
            (row["id"],),
        ).fetchone()
        return {"job": self.job_from_row(claimed)}

    def record_job_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        worker_id = str(payload["worker_id"])
        agent_token = str(payload["agent_token"])
        job_id = str(payload["job_id"])
        self.verify_worker(worker_id, agent_token)
        job = self.conn.execute(
            "select target_worker_id from jobs where id = ?", (job_id,)
        ).fetchone()
        if job is None:
            raise ValueError("job not found")
        if job["target_worker_id"] != worker_id:
            raise ValueError("job is not assigned to this worker")
        event_id = new_id("evt")
        ts = now_ts()
        row = {
            "id": event_id,
            "job_id": job_id,
            "worker_id": worker_id,
            "event_type": str(payload["event_type"]),
            "message": str(payload.get("message") or ""),
            "payload": payload.get("payload") or {},
            "created_at": ts,
        }
        with self.conn:
            self.conn.execute(
                """
                insert into job_events
                (id, job_id, worker_id, event_type, message, payload_json, created_at)
                values (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    job_id,
                    worker_id,
                    row["event_type"],
                    row["message"],
                    json.dumps(row["payload"]),
                    ts,
                ),
            )
        return row

    def complete_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        worker_id = str(payload["worker_id"])
        agent_token = str(payload["agent_token"])
        job_id = str(payload["job_id"])
        status = str(payload["status"])
        if status not in {"succeeded", "failed", "blocked"}:
            raise ValueError("status must be succeeded, failed, or blocked")
        self.verify_worker(worker_id, agent_token)
        job = self.conn.execute(
            "select target_worker_id from jobs where id = ?", (job_id,)
        ).fetchone()
        if job is None:
            raise ValueError("job not found")
        if job["target_worker_id"] != worker_id:
            raise ValueError("job is not assigned to this worker")
        ts = now_ts()
        with self.conn:
            self.conn.execute(
                "update jobs set status = ?, updated_at = ? where id = ?",
                (status, ts, job_id),
            )
            self.conn.execute(
                """
                insert into job_events
                (id, job_id, worker_id, event_type, message, payload_json, created_at)
                values (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id("evt"),
                    job_id,
                    worker_id,
                    status,
                    str(payload.get("message") or status),
                    json.dumps(payload.get("payload") or {}),
                    ts,
                ),
            )
            self.audit(
                "worker",
                worker_id,
                f"job.{status}",
                {
                    "job_id": job_id,
                    "status": status,
                    "message": payload.get("message") or status,
                },
            )
        row = self.conn.execute(
            """
            select id, target_worker_id, recipe, payload_json, status, created_at, updated_at
            from jobs
            where id = ?
            """,
            (job_id,),
        ).fetchone()
        return self.job_from_row(row)

    def list_job_events(self, job_id: str | None = None) -> list[dict[str, Any]]:
        if job_id:
            rows = self.conn.execute(
                """
                select id, job_id, worker_id, event_type, message, payload_json, created_at
                from job_events
                where job_id = ?
                order by created_at asc
                """,
                (job_id,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """
                select id, job_id, worker_id, event_type, message, payload_json, created_at
                from job_events
                order by created_at desc
                limit 200
                """
            ).fetchall()
        return [
            {
                "id": row["id"],
                "job_id": row["job_id"],
                "worker_id": row["worker_id"],
                "event_type": row["event_type"],
                "message": row["message"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def create_approval(self, payload: dict[str, Any]) -> dict[str, Any]:
        worker_id = str(payload["worker_id"])
        agent_token = str(payload["agent_token"])
        self.verify_worker(worker_id, agent_token)
        approval_id = new_id("apr")
        ts = now_ts()
        row = {
            "id": approval_id,
            "worker_id": worker_id,
            "job_id": payload.get("job_id"),
            "title": str(payload["title"]),
            "body": payload.get("body") or {},
            "status": "pending",
            "created_at": ts,
        }
        with self.conn:
            self.conn.execute(
                """
                insert into approval_requests
                (id, worker_id, job_id, title, body_json, status, created_at)
                values (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    approval_id,
                    worker_id,
                    row["job_id"],
                    row["title"],
                    json.dumps(row["body"]),
                    row["status"],
                    ts,
                ),
            )
            self.audit("worker", worker_id, "approval.create", row)
        return row

    def list_approvals(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            select id, worker_id, job_id, title, body_json, status, created_at, resolved_at
            from approval_requests
            order by created_at desc
            """
        ).fetchall()
        return [
            {
                "id": row["id"],
                "worker_id": row["worker_id"],
                "job_id": row["job_id"],
                "title": row["title"],
                "body": json.loads(row["body_json"]),
                "status": row["status"],
                "created_at": row["created_at"],
                "resolved_at": row["resolved_at"],
            }
            for row in rows
        ]

    def resolve_approval(self, payload: dict[str, Any]) -> dict[str, Any]:
        approval_id = str(payload["approval_id"])
        decision = str(payload["decision"])
        if decision not in {"approved", "rejected"}:
            raise ValueError("decision must be approved or rejected")
        row = self.conn.execute(
            """
            select id, worker_id, job_id, title, body_json, status, created_at, resolved_at
            from approval_requests
            where id = ?
            """,
            (approval_id,),
        ).fetchone()
        if row is None:
            raise ValueError("approval not found")
        if row["status"] != "pending":
            raise ValueError("approval already resolved")
        ts = now_ts()
        audit_payload = {
            "approval_id": approval_id,
            "decision": decision,
            "comment": payload.get("comment") or "",
        }
        with self.conn:
            self.conn.execute(
                """
                update approval_requests
                set status = ?, resolved_at = ?
                where id = ?
                """,
                (decision, ts, approval_id),
            )
            self.audit("admin", "control", "approval.resolve", audit_payload)
        resolved = self.conn.execute(
            """
            select id, worker_id, job_id, title, body_json, status, created_at, resolved_at
            from approval_requests
            where id = ?
            """,
            (approval_id,),
        ).fetchone()
        return {
            "id": resolved["id"],
            "worker_id": resolved["worker_id"],
            "job_id": resolved["job_id"],
            "title": resolved["title"],
            "body": json.loads(resolved["body_json"]),
            "status": resolved["status"],
            "created_at": resolved["created_at"],
            "resolved_at": resolved["resolved_at"],
        }

    def create_worker_report(self, payload: dict[str, Any]) -> dict[str, Any]:
        worker_id = str(payload["worker_id"])
        agent_token = str(payload["agent_token"])
        self.verify_worker(worker_id, agent_token)
        source = str(payload.get("source") or "agent")
        level = str(payload.get("level") or "info")
        if source not in {"agent", "codex", "claude_code", "system", "human"}:
            raise ValueError("source must be agent, codex, claude_code, system, or human")
        if level not in {"debug", "info", "warning", "error", "blocked", "needs_human"}:
            raise ValueError("level must be debug, info, warning, error, blocked, or needs_human")
        report_id = new_id("rpt")
        ts = now_ts()
        row = {
            "id": report_id,
            "worker_id": worker_id,
            "source": source,
            "level": level,
            "title": str(payload.get("title") or ""),
            "message": str(payload.get("message") or ""),
            "payload": payload.get("payload") or {},
            "created_at": ts,
        }
        with self.conn:
            self.conn.execute(
                """
                insert into worker_reports
                (id, worker_id, source, level, title, message, payload_json, created_at)
                values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    worker_id,
                    source,
                    level,
                    row["title"],
                    row["message"],
                    json.dumps(row["payload"]),
                    ts,
                ),
            )
            self.audit("worker", worker_id, "worker_report.create", row)
        return row

    def list_worker_reports(
        self, worker_id: str | None = None, source: str | None = None, limit: int = 200
    ) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 1000))
        clauses = []
        params: list[Any] = []
        if worker_id:
            clauses.append("worker_id = ?")
            params.append(worker_id)
        if source:
            clauses.append("source = ?")
            params.append(source)
        where = f"where {' and '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(
            f"""
            select id, worker_id, source, level, title, message, payload_json, created_at
            from worker_reports
            {where}
            order by created_at desc
            limit ?
            """,
            (*params, limit),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "worker_id": row["worker_id"],
                "source": row["source"],
                "level": row["level"],
                "title": row["title"],
                "message": row["message"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def audit(
        self, actor_type: str, actor_id: str, action: str, payload: dict[str, Any]
    ) -> None:
        self.conn.execute(
            """
            insert into audit_logs
            (id, actor_type, actor_id, action, payload_json, created_at)
            values (?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("aud"),
                actor_type,
                actor_id,
                action,
                json.dumps(payload, default=str),
                now_ts(),
            ),
        )
