from pathlib import Path
import subprocess

def run_git(args, cwd=None):
    """Run a git command and return output or None on failure."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=1
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
    except Exception:
        return None


def is_git_repo(path: Path) -> bool:
    """Return True if path is inside a Git repository."""
    return run_git(["rev-parse", "--is-inside-work-tree"], cwd=path) == "true"


def get_git_root(path: Path) -> Path | None:
    out = run_git(["rev-parse", "--show-toplevel"], cwd=path)
    return Path(out) if out else None


def get_git_branch(path: Path) -> str | None:
    out = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=path)
    return out


def get_git_status(path: Path) -> dict:
    """
    Return a dictionary summarizing the repo’s status.
    Good for the status bar or quick-view overlays.
    """
    porcelain = run_git(["status", "--porcelain"], cwd=path)
    branch = get_git_branch(path)

    added = modified = deleted = untracked = 0
    if porcelain:
        for line in porcelain.splitlines():
            code = line[:2]
            if code == "??":
                untracked += 1
            elif "A" in code:
                added += 1
            elif "M" in code:
                modified += 1
            elif "D" in code:
                deleted += 1

    return {
        "branch": branch,
        "added": added,
        "modified": modified,
        "deleted": deleted,
        "untracked": untracked,
    }
