from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from control.store import Store


class StoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test.sqlite3"
        self.store = Store(self.db_path)

    def tearDown(self) -> None:
        self.store.close()
        self.tmpdir.cleanup()

    def test_worker_registration_and_heartbeat(self) -> None:
        bootstrap = self.store.create_bootstrap_token("lab-gpu-01", ttl_seconds=60)
        worker = self.store.register_worker(
            {
                "token": bootstrap["token"],
                "machine_name": "lab-gpu-01",
                "hostname": "lab-gpu-01.local",
                "os": "linux",
                "tags": ["linux", "gpu"],
                "metadata": {"gpu": "RTX 4090"},
            }
        )

        self.assertEqual(worker["machine_name"], "lab-gpu-01")
        self.assertTrue(worker["agent_token"].startswith("lfat_"))

        result = self.store.heartbeat(
            {
                "worker_id": worker["id"],
                "agent_token": worker["agent_token"],
                "status": "online",
                "metrics": {"loadavg": [0.1, 0.2, 0.3]},
            }
        )

        self.assertTrue(result["ok"])
        workers = self.store.list_workers()
        self.assertEqual(len(workers), 1)
        self.assertEqual(workers[0]["status"], "online")
        self.assertEqual(workers[0]["tags"], ["linux", "gpu"])

    def test_bootstrap_token_is_single_use(self) -> None:
        bootstrap = self.store.create_bootstrap_token("lab-gpu-01", ttl_seconds=60)
        payload = {
            "token": bootstrap["token"],
            "machine_name": "lab-gpu-01",
            "hostname": "lab-gpu-01.local",
            "os": "linux",
            "tags": [],
            "metadata": {},
        }
        self.store.register_worker(payload)
        with self.assertRaises(ValueError):
            self.store.register_worker(payload)

    def test_job_and_approval(self) -> None:
        bootstrap = self.store.create_bootstrap_token("lab-gpu-01", ttl_seconds=60)
        worker = self.store.register_worker(
            {
                "token": bootstrap["token"],
                "machine_name": "lab-gpu-01",
                "hostname": "lab-gpu-01.local",
                "os": "linux",
                "tags": [],
                "metadata": {},
            }
        )
        job = self.store.create_job(
            recipe="smoke_test",
            payload={"message": "hello"},
            target_worker_id=worker["id"],
        )
        approval = self.store.create_approval(
            {
                "worker_id": worker["id"],
                "agent_token": worker["agent_token"],
                "job_id": job["id"],
                "title": "Approve high-risk action",
                "body": {"risk": "L4"},
            }
        )

        self.assertEqual(job["status"], "queued")
        self.assertEqual(approval["status"], "pending")
        self.assertEqual(len(self.store.list_jobs()), 1)
        self.assertEqual(len(self.store.list_approvals()), 1)

        resolved = self.store.resolve_approval(
            {
                "approval_id": approval["id"],
                "decision": "approved",
                "comment": "test approval",
            }
        )
        self.assertEqual(resolved["status"], "approved")
        with self.assertRaises(ValueError):
            self.store.resolve_approval(
                {
                    "approval_id": approval["id"],
                    "decision": "rejected",
                    "comment": "should fail",
                }
            )

    def test_worker_can_claim_and_complete_job(self) -> None:
        bootstrap = self.store.create_bootstrap_token("lab-gpu-01", ttl_seconds=60)
        worker = self.store.register_worker(
            {
                "token": bootstrap["token"],
                "machine_name": "lab-gpu-01",
                "hostname": "lab-gpu-01.local",
                "os": "linux",
                "tags": [],
                "metadata": {},
            }
        )
        queued = self.store.create_job(
            recipe="smoke_test",
            payload={"message": "hello"},
            target_worker_id=None,
        )

        claimed = self.store.claim_job(
            {
                "worker_id": worker["id"],
                "agent_token": worker["agent_token"],
            }
        )["job"]

        self.assertEqual(claimed["id"], queued["id"])
        self.assertEqual(claimed["status"], "running")
        self.assertEqual(claimed["target_worker_id"], worker["id"])

        self.store.record_job_event(
            {
                "worker_id": worker["id"],
                "agent_token": worker["agent_token"],
                "job_id": queued["id"],
                "event_type": "artifact",
                "message": "wrote result",
                "payload": {"path": "result.json"},
            }
        )
        completed = self.store.complete_job(
            {
                "worker_id": worker["id"],
                "agent_token": worker["agent_token"],
                "job_id": queued["id"],
                "status": "succeeded",
                "message": "done",
                "payload": {"ok": True},
            }
        )

        self.assertEqual(completed["status"], "succeeded")
        events = self.store.list_job_events(job_id=queued["id"])
        event_types = [event["event_type"] for event in events]
        self.assertEqual(event_types, ["claimed", "artifact", "succeeded"])

    def test_worker_reports_capture_codex_and_claude_status(self) -> None:
        bootstrap = self.store.create_bootstrap_token("lab-gpu-01", ttl_seconds=60)
        worker = self.store.register_worker(
            {
                "token": bootstrap["token"],
                "machine_name": "lab-gpu-01",
                "hostname": "lab-gpu-01.local",
                "os": "linux",
                "tags": ["codex"],
                "metadata": {},
            }
        )

        codex_report = self.store.create_worker_report(
            {
                "worker_id": worker["id"],
                "agent_token": worker["agent_token"],
                "source": "codex",
                "level": "needs_human",
                "title": "License boundary",
                "message": "COMSOL license needs manual confirmation.",
                "payload": {"options": ["wait", "switch-worker"]},
            }
        )
        claude_report = self.store.create_worker_report(
            {
                "worker_id": worker["id"],
                "agent_token": worker["agent_token"],
                "source": "claude_code",
                "level": "info",
                "title": "Patch ready",
                "message": "Simulation runner patch compiled.",
                "payload": {"branch": "agent/sim-runner"},
            }
        )

        self.assertEqual(codex_report["source"], "codex")
        self.assertEqual(codex_report["level"], "needs_human")
        self.assertEqual(codex_report["payload"]["options"], ["wait", "switch-worker"])
        self.assertEqual(claude_report["source"], "claude_code")

        reports = self.store.list_worker_reports(worker_id=worker["id"])
        self.assertEqual({report["id"] for report in reports}, {codex_report["id"], claude_report["id"]})

        codex_reports = self.store.list_worker_reports(source="codex")
        self.assertEqual(len(codex_reports), 1)
        self.assertEqual(codex_reports[0]["title"], "License boundary")

        with self.assertRaises(ValueError):
            self.store.create_worker_report(
                {
                    "worker_id": worker["id"],
                    "agent_token": worker["agent_token"],
                    "source": "unknown",
                    "title": "Bad report",
                }
            )

    def test_worker_chat_threads_are_per_worker(self) -> None:
        first_bootstrap = self.store.create_bootstrap_token("lab-gpu-01", ttl_seconds=60)
        second_bootstrap = self.store.create_bootstrap_token("win-lab-01", ttl_seconds=60)
        first = self.store.register_worker(
            {
                "token": first_bootstrap["token"],
                "machine_name": "lab-gpu-01",
                "hostname": "lab-gpu-01.local",
                "os": "linux",
                "tags": [],
                "metadata": {},
            }
        )
        second = self.store.register_worker(
            {
                "token": second_bootstrap["token"],
                "machine_name": "win-lab-01",
                "hostname": "win-lab-01.local",
                "os": "windows",
                "tags": [],
                "metadata": {},
            }
        )

        self.store.create_worker_report(
            {
                "worker_id": first["id"],
                "agent_token": first["agent_token"],
                "source": "codex",
                "level": "needs_human",
                "title": "Boundary decision",
                "message": "Need Mac-side input.",
                "payload": {"risk": "L4"},
            }
        )
        human = self.store.create_chat_message(
            {
                "worker_id": first["id"],
                "role": "human",
                "author": "mac",
                "content": "Use the smaller range.",
                "payload": {"decision": "shrink_range"},
            }
        )
        self.store.create_chat_message(
            {
                "worker_id": second["id"],
                "role": "human",
                "author": "mac",
                "content": "Stand by.",
            }
        )

        first_messages = self.store.list_chat_messages(worker_id=first["id"])
        second_messages = self.store.list_chat_messages(worker_id=second["id"])

        self.assertEqual([message["role"] for message in first_messages], ["codex", "human"])
        self.assertIn("Boundary decision", first_messages[0]["content"])
        self.assertEqual(first_messages[1]["id"], human["id"])
        self.assertEqual(first_messages[1]["payload"]["decision"], "shrink_range")
        self.assertEqual(len(second_messages), 1)
        self.assertEqual(second_messages[0]["content"], "Stand by.")

    def test_worker_can_read_and_reply_to_own_chat_thread(self) -> None:
        first_bootstrap = self.store.create_bootstrap_token("lab-gpu-01", ttl_seconds=60)
        second_bootstrap = self.store.create_bootstrap_token("win-lab-01", ttl_seconds=60)
        first = self.store.register_worker(
            {
                "token": first_bootstrap["token"],
                "machine_name": "lab-gpu-01",
                "hostname": "lab-gpu-01.local",
                "os": "linux",
                "tags": [],
                "metadata": {},
            }
        )
        second = self.store.register_worker(
            {
                "token": second_bootstrap["token"],
                "machine_name": "win-lab-01",
                "hostname": "win-lab-01.local",
                "os": "windows",
                "tags": [],
                "metadata": {},
            }
        )

        self.store.create_chat_message(
            {
                "worker_id": first["id"],
                "role": "human",
                "author": "mac",
                "content": "Run the smoke test.",
            }
        )
        self.store.create_chat_message(
            {
                "worker_id": second["id"],
                "role": "human",
                "author": "mac",
                "content": "Do not expose this to first worker.",
            }
        )

        visible = self.store.list_worker_chat_messages(
            {
                "worker_id": first["id"],
                "agent_token": first["agent_token"],
                "limit": 10,
            }
        )
        self.assertEqual(len(visible), 1)
        self.assertEqual(visible[0]["content"], "Run the smoke test.")

        reply = self.store.create_worker_chat_message(
            {
                "worker_id": first["id"],
                "agent_token": first["agent_token"],
                "role": "claude_code",
                "content": "Smoke test passed.",
                "payload": {"command": "make smoke"},
            }
        )

        self.assertEqual(reply["role"], "claude_code")
        self.assertEqual(reply["payload"]["command"], "make smoke")
        first_messages = self.store.list_chat_messages(worker_id=first["id"])
        self.assertEqual(
            [message["role"] for message in first_messages],
            ["human", "claude_code"],
        )

        with self.assertRaises(ValueError):
            self.store.list_worker_chat_messages(
                {
                    "worker_id": first["id"],
                    "agent_token": second["agent_token"],
                }
            )
        with self.assertRaises(ValueError):
            self.store.create_worker_chat_message(
                {
                    "worker_id": first["id"],
                    "agent_token": first["agent_token"],
                    "role": "human",
                    "content": "I should not be accepted.",
                }
            )


if __name__ == "__main__":
    unittest.main()
