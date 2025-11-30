import subprocess
from typing import Tuple

from shellpilot.core.commands import ShellCommand


def run_shell_command(cmd: ShellCommand, dry_run: bool = False) -> Tuple[int, str, str]:
    """
    Run a shell command described by ShellCommand.

    - If dry_run=True: don't actually execute, just return the command string.
    - Always returns (return_code, stdout_str, stderr_str).
    - Robust against binary output (decodes with errors='replace').
    """
    if dry_run:
        # We don't execute; just pretend and show what would be run.
        return 0, cmd.command, ""

    proc = subprocess.Popen(
        cmd.command,
        shell=True,
        cwd=cmd.cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,  # raw bytes; we'll decode manually
    )

    stdout_bytes, stderr_bytes = proc.communicate()

    def _decode(data: bytes) -> str:
        if data is None:
            return ""
        if isinstance(data, (bytes, bytearray)):
            return data.decode("utf-8", errors="replace")
        return str(data)

    stdout = _decode(stdout_bytes)
    stderr = _decode(stderr_bytes)

    return proc.returncode, stdout, stderr
