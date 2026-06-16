from __future__ import annotations

import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from control.store import Store


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = Store(Path(tmp) / "smoke.sqlite3")
        bootstrap = store.create_bootstrap_token("smoke-worker", ttl_seconds=60)
        worker = store.register_worker(
            {
                "token": bootstrap["token"],
                "machine_name": "smoke-worker",
                "hostname": "smoke-worker.local",
                "os": "linux",
                "tags": ["smoke"],
                "metadata": {"purpose": "local smoke test"},
            }
        )
        store.heartbeat(
            {
                "worker_id": worker["id"],
                "agent_token": worker["agent_token"],
                "status": "online",
                "metrics": {"loadavg": [0, 0, 0]},
            }
        )
        job = store.create_job(
            recipe="smoke_test",
            payload={"message": "hello loop farm"},
            target_worker_id=worker["id"],
        )
        approval = store.create_approval(
            {
                "worker_id": worker["id"],
                "agent_token": worker["agent_token"],
                "job_id": job["id"],
                "title": "Smoke approval",
                "body": {"risk": "L4", "recommended": "reject"},
            }
        )

        print("smoke ok")
        print(f"worker={worker['id']}")
        print(f"job={job['id']}")
        print(f"approval={approval['id']}")


if __name__ == "__main__":
    main()
