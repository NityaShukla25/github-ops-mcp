import json
import re
import subprocess
from pathlib import Path

from .config import CMD_TIMEOUT

ALLOWED_GH_SUBCOMMANDS = {"search", "repo", "issue", "pr", "release", "api"}

BLOCKED_REPO_ACTIONS = {"delete", "edit", "create", "fork", "archive", "rename"}

ALLOWED_API_PREFIXES = (
    "repos/",  # covers contributors, languages, forks, stats, branches/protection, readme
)

OWNER_REPO_PATTERN = re.compile(r"^[\w.-]+/[\w.-]+$")


def run_gh(args: list[str], cwd: Path | None = None) -> tuple[str, str, int]:
    if not args:
        raise ValueError("gh args cannot be empty")

    sub = args[0]
    if sub not in ALLOWED_GH_SUBCOMMANDS:
        raise PermissionError(f"gh subcommand '{sub}' is not allowed")

    if sub == "repo" and len(args) > 1 and args[1] in BLOCKED_REPO_ACTIONS:
        raise PermissionError(f"gh repo {args[1]} is not allowed")

    if sub == "api" and len(args) > 1:
        endpoint = args[1]
        if not any(endpoint.startswith(p) for p in ALLOWED_API_PREFIXES):
            raise PermissionError(f"gh api endpoint '{endpoint}' is not allowed")

    proc = subprocess.run(
        ["gh", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=CMD_TIMEOUT,
        shell=False,
    )
    return proc.stdout, proc.stderr, proc.returncode


def run_gh_json(args: list[str]) -> tuple[dict | list | None, str, int]:
    out, err, code = run_gh(args)
    if code != 0 or not out.strip():
        return None, err, code
    try:
        return json.loads(out), err, code
    except json.JSONDecodeError:
        return None, f"invalid JSON from gh: {out[:200]}", code
