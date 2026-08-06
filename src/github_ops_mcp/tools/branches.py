from ..git_wrapper import run_git
from ..sandbox import resolve_file_in_repo, resolve_repo_path
from ..validators import validate_branch
from . import safe_call


@safe_call
def list_branches(repo_path: str):
    """List all local and remote branches, plus the current one."""
    repo = resolve_repo_path(repo_path)
    out, err, code = run_git(["branch", "-a"], cwd=repo)
    if code != 0:
        raise RuntimeError(err or "git branch failed")

    branches = []
    current = None
    for line in out.splitlines():
        line = line.rstrip()
        if not line:
            continue
        is_current = line.startswith("*")
        name = line[2:].strip() if is_current else line.strip()
        if is_current:
            current = name
        branches.append(name)
    return {"branches": branches, "current": current}


@safe_call
def checkout_branch(repo_path: str, branch: str, create_new: bool = False):
    """Switch to a branch, optionally creating it."""
    repo = resolve_repo_path(repo_path)
    validate_branch(branch)
    args = ["checkout", "-b", branch] if create_new else ["checkout", branch]
    out, err, code = run_git(args, cwd=repo)
    return {"success": code == 0, "message": (out + err).strip()}


@safe_call
def list_commits(repo_path: str, n: int = 10):
    """Show the last N commits."""
    repo = resolve_repo_path(repo_path)
    out, err, code = run_git(
        ["log", f"-n{n}", "--pretty=format:%H|%an|%ad|%s", "--date=short"],
        cwd=repo,
    )
    if code != 0:
        raise RuntimeError(err or "git log failed")
    return {"commits": _parse_log(out)}


@safe_call
def get_file_history(repo_path: str, filepath: str):
    """Commit history for a specific file (follows renames)."""
    repo = resolve_repo_path(repo_path)
    resolve_file_in_repo(repo_path, filepath)  # validates traversal
    out, err, code = run_git(
        ["log", "--follow", "--pretty=format:%H|%an|%ad|%s", "--date=short", "--", filepath],
        cwd=repo,
    )
    if code != 0:
        raise RuntimeError(err or "git log failed")
    return {"commits": _parse_log(out)}


def _parse_log(text: str) -> list[dict]:
    commits = []
    for line in text.splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            commits.append({
                "hash": parts[0],
                "author": parts[1],
                "date": parts[2],
                "message": parts[3],
            })
    return commits
