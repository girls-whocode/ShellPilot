# shellpilot/ai/hardware.py
from __future__ import annotations

import subprocess
from typing import NamedTuple, Optional


class GPUInfo(NamedTuple):
    name: str
    memory_mb: int


def detect_nvidia_gpu(timeout: float = 2.0) -> Optional[GPUInfo]:
    """
    Detect an NVIDIA GPU using `nvidia-smi`.

    Returns:
        GPUInfo if at least one NVIDIA GPU is detected, otherwise None.
    """
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        print("[ShellPilot][GPU] nvidia-smi not found on PATH.")
        return None
    except Exception as e:
        print(f"[ShellPilot][GPU] Error running nvidia-smi: {e}")
        return None

    if result.returncode != 0:
        print("[ShellPilot][GPU] nvidia-smi returned non-zero exit code:")
        print("  stdout:", result.stdout.strip() or "<empty>")
        print("  stderr:", result.stderr.strip() or "<empty>")
        return None

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        print("[ShellPilot][GPU] nvidia-smi produced no lines.")
        return None

    first = lines[0]
    print(f"[ShellPilot][GPU] Raw line from nvidia-smi: {first!r}")
    parts = [p.strip() for p in first.split(",")]
    if len(parts) < 2:
        print("[ShellPilot][GPU] Could not parse CSV fields:", parts)
        return None

    name, mem_str = parts[0], parts[1]
    try:
        mem_mb = int(mem_str)
    except ValueError:
        print(f"[ShellPilot][GPU] Failed to parse memory amount: {mem_str!r}")
        mem_mb = 0

    info = GPUInfo(name=name, memory_mb=mem_mb)
    print(f"[ShellPilot][GPU] Detected GPU: {info}")
    return info
