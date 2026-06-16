from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_CONFIG_PATH = "~/.loop-farm-agent/config.json"


@dataclass
class AgentConfig:
    control_url: str
    machine_name: str
    worker_id: str
    agent_token: str
    heartbeat_interval: int = 10
    work_dir: str = "~/.loop-farm-agent/workspaces"
    artifact_dir: str = "~/.loop-farm-agent/artifacts"

    @classmethod
    def load(cls, path: str | Path) -> "AgentConfig":
        raw = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
        return cls(**raw)

    def save(self, path: str | Path) -> None:
        target = Path(path).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

