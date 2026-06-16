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


if __name__ == "__main__":
    unittest.main()
