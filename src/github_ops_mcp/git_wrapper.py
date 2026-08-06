import subprocess
from pathlib import Path

from .config import CMD_TIMEOUT

ALLOWED_GIT_SUBCOMMANDS = {
    "clone", "pull", "branch", "checkout",
    "status", "diff", "log", "rev-list", "shortlog",
}

BLOCKED_FLAGS = {
    "push", "reset", "rebase", "clean",
    "--force", "-f", "--hard", "-D", "-d",
}


def run_git(args: list[str], cwd: Path | None = None) -> tuple[str, str, int]:
    if not args:
        raise ValueError("git args cannot be empty")

    sub = args[0]
    if sub not in ALLOWED_GIT_SUBCOMMANDS:
        raise PermissionError(f"git subcommand '{sub}' is not allowed")

    if sub == "branch" and any(a in ("-D", "-d", "--delete") for a in args[1:]):
        raise PermissionError("branch deletion is not allowed")

    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=CMD_TIMEOUT,
        shell=False,
    )
    return proc.stdout, proc.stderr, proc.returncode
