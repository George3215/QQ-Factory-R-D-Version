from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path
from typing import Any


def collect_inventory() -> dict[str, Any]:
    return {
        "hostname": platform.node(),
        "os": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "cwd": str(Path.cwd()),
    }


def collect_metrics(path: str = ".") -> dict[str, Any]:
    usage = shutil.disk_usage(path)
    loadavg = None
    if hasattr(os, "getloadavg"):
        try:
            loadavg = os.getloadavg()
        except OSError:
            loadavg = None
    return {
        "loadavg": loadavg,
        "disk_total": usage.total,
        "disk_used": usage.used,
        "disk_free": usage.free,
    }


def self_test() -> dict[str, Any]:
    checks = {
        "python_version": platform.python_version(),
        "git": shutil.which("git") is not None,
        "tailscale": shutil.which("tailscale") is not None,
        "rustdesk": shutil.which("rustdesk") is not None,
        "nvidia_smi": shutil.which("nvidia-smi") is not None,
    }
    return {
        "ok": True,
        "inventory": collect_inventory(),
        "checks": checks,
    }

