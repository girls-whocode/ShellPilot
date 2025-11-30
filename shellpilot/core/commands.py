from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import shlex


@dataclass
class ShellCommand:
    """
    Represents a shell command plus some metadata we can show to the user.

    - description: Short “what this does” label.
    - command: The exact shell string to run.
    - explanation: Beginner-friendly explanation of the command.
    - cwd: Directory in which to run the command.
    - dangerous: Whether this might modify/delete data.
    """
    description: str
    command: str
    explanation: str
    cwd: Optional[Path] = None
    dangerous: bool = False

    def full_display(self) -> str:
        """Pretty-print how this command will be run."""
        if self.cwd:
            return f"# in {self.cwd}\n{self.command}"
        return self.command


def build_ls_command(path: Path) -> ShellCommand:
    """
    Build a safe 'ls -lha' command for the given path with an explanation
    targeted at beginners.
    """
    explanation = (
        "This command lists the contents of a directory using `ls -lha`:\n"
        "  • `-l`  = long format (permissions, owner, size, date)\n"
        "  • `-h`  = human-readable sizes (KB/MB/GB)\n"
        "  • `-a`  = show *all* files, including hidden ones that start with a dot.\n\n"
        "You can run this anytime without changing or deleting anything."
    )
    return ShellCommand(
        description=f"List contents of {path}",
        command="ls -lha -- .",
        explanation=explanation,
        cwd=path,
        dangerous=False,
    )


def build_view_file_command(path: Path, max_lines: int = 80) -> ShellCommand:
    """
    Build a safe 'view file' command.

    Conceptually: show the first N lines of the file.
    We'll present it as using `sed -n '1,NP'` so users learn a tool
    that's available on every Linux system.
    """
    quoted = shlex.quote(str(path))
    explanation = (
        f"This command shows the first {max_lines} lines of the file using `sed`:\n"
        "  • `sed -n '1,NP' file` = print only lines 1 through N\n"
        "  • This is useful for quickly previewing text files.\n\n"
        "It does *not* modify the file; it only reads and displays it."
    )
    command = f"sed -n '1,{max_lines}p' -- {quoted}"
    return ShellCommand(
        description=f"Preview of {path.name}",
        command=command,
        explanation=explanation,
        cwd=path.parent,
        dangerous=False,
    )


def build_mv_command(src: Path, dst: Path) -> ShellCommand:
    """
    Move/rename a file or directory.

    NOTE: This is marked as dangerous because it modifies the filesystem.
    We will later wrap this in a confirmation dialog before running.
    """
    explanation = (
        "This command moves or renames a file using `mv`:\n"
        "  • The first path is the source (what you are moving).\n"
        "  • The second path is the destination (where it goes or new name).\n\n"
        "Be careful: if the destination is an existing file, it may overwrite it."
    )
    return ShellCommand(
        description=f"Move {src.name} → {dst}",
        command=f"mv -- {src} {dst}",
        explanation=explanation,
        cwd=src.parent,
        dangerous=True,
    )
